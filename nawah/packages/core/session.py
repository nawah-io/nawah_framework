from nawah.base_module import BaseModule
from nawah.config import Config
from nawah.registry import Registry
from nawah.enums import Event
from nawah.classes import (
	ATTR,
	PERM,
	EXTN,
	METHOD,
	Query,
	NAWAH_DOC,
	NAWAH_QUERY,
	ANALYTIC,
	DictObj,
	BaseModel,
)
from nawah.utils import extract_attr

from bson import ObjectId
from passlib.hash import pbkdf2_sha512
from typing import List, Dict, Any, Union, Iterable

import logging, secrets, copy, datetime

logger = logging.getLogger('nawah')


class Session(BaseModule):
	'''`Session` module provides data type and controller for sessions in Nawah eco-system. CRUD methods of the module are supposed to used for internal calls only, while methods `auth`, `reauth`, and `signout` are available for use by API as well as internal calls when needed.'''

	collection = 'sessions'
	attrs = {
		'user': ATTR.ID(desc='`_id` of `User` doc the doc belongs to.'),
		'groups': ATTR.LIST(
			desc='List of `_id` for every group the session is authenticated against. This attr is set by `auth` method when called with `groups` Doc Arg for Controller Auth Sequence.',
			list=[ATTR.ID(desc='`_id` of Group doc the session is authenticated against.')],
		),
		'host_add': ATTR.IP(desc='IP of the host the user used to authenticate.'),
		'user_agent': ATTR.STR(desc='User-agent of the app the user used to authenticate.'),
		'expiry': ATTR.DATETIME(desc='Python `datetime` ISO format of session expiry.'),
		'token_hash': ATTR.STR(desc='Hashed system-generated session token.'),
		'create_time': ATTR.DATETIME(
			desc='Python `datetime` ISO format of the doc creation.'
		),
	}
	defaults = {'groups': []}
	extns = {'user': EXTN(module='user', attrs=['*'], force=True)}
	methods = {
		'read': METHOD(permissions=[PERM(privilege='read', query_mod={'user': '$__user'})]),
		'create': METHOD(permissions=[PERM(privilege='create')]),
		'update': METHOD(
			permissions=[
				PERM(
					privilege='update',
					query_mod={'user': '$__user'},
					doc_mod={'user': None},
				)
			],
			query_args={'_id': ATTR.ID()},
		),
		'delete': METHOD(
			permissions=[PERM(privilege='delete', query_mod={'user': '$__user'})],
			query_args={'_id': ATTR.ID()},
		),
		'auth': METHOD(permissions=[PERM(privilege='*')], doc_args=[]),
		'reauth': METHOD(
			permissions=[PERM(privilege='*')],
			query_args=[
				{
					'_id': ATTR.ID(),
					'token': ATTR.STR(),
					'groups': ATTR.LIST(list=[ATTR.ID()]),
				},
				{'_id': ATTR.ID(), 'token': ATTR.STR()},
			],
		),
		'signout': METHOD(
			permissions=[PERM(privilege='*')],
			query_args={'_id': ATTR.ID()},
		),
	}

	async def auth(self, skip_events=[], env={}, query=[], doc={}):
		for attr in Registry.module('user').unique_attrs:
			if attr in doc.keys():
				key = attr
				break
		user_query = [{key: doc[key], '$limit': 1}]
		if 'groups' in doc.keys():
			user_query.append([{'groups': {'$in': doc['groups']}}, {'privileges': {'*': ['*']}}])
		user_results = await Registry.module('user').read(
			skip_events=[Event.PERM, Event.ON], env=env, query=user_query
		)
		if not user_results.args.count or not pbkdf2_sha512.verify(
			doc['hash'],
			user_results.args.docs[0][f'{key}_hash'],
		):
			raise self.exception(
				status=403,
				msg='Wrong auth credentials.',
				args={'code': 'INVALID_CREDS'},
			)

		user = user_results.args.docs[0]

		if Event.ON not in skip_events:
			if user.status in ['banned', 'deleted']:
				raise self.exception(
					status=403,
					msg=f'User is {user.status}.',
					args={'code': 'INVALID_USER'},
				)

			elif user.status == 'disabled_password':
				raise self.exception(
					status=403,
					msg='User password is disabled.',
					args={'code': 'INVALID_USER'},
				)

		token = secrets.token_urlsafe(32)
		session = {
			'user': user._id,
			'groups': doc['groups'] if 'groups' in doc.keys() else [],
			'host_add': env['REMOTE_ADDR'],
			'user_agent': env['HTTP_USER_AGENT'],
			'expiry': (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat(),
			'token_hash': pbkdf2_sha512.using(rounds=100000).hash(token),
		}

		results = await self.create(skip_events=[Event.PERM], env=env, doc=session)
		if results.status != 200:
			return results

		session['_id'] = results.args.docs[0]._id
		session['user'] = user
		del session['token_hash']
		session['token'] = token
		results.args.docs[0] = BaseModel(session)

		# [DOC] read user privileges and return them
		user_results = await Registry.module('user').read_privileges(
			skip_events=[Event.PERM], env=env, query=[{'_id': user._id}]
		)
		if user_results.status != 200:
			return user_results
		results.args.docs[0]['user'] = user_results.args.docs[0]

		# [DOC] Create CONN_AUTH Analytic doc
		if Config.analytics_events['session_conn_auth']:
			analytic_doc = {
				'event': 'CONN_AUTH',
				'subevent': env['client_app'],
				'args': {
					'user': user_results.args.docs[0]._id,
					'session': results.args.docs[0]._id,
					'REMOTE_ADDR': env['REMOTE_ADDR'],
					'HTTP_USER_AGENT': env['HTTP_USER_AGENT'],
				},
			}
			analytic_results = await Registry.module('analytic').create(
				skip_events=[Event.PERM], env=env, doc=analytic_doc
			)
			if analytic_results.status != 200:
				logger.error(
					f'Failed to create \'Analytic\' doc: {analytic_doc}. Results: {analytic_results}'
				)
		# [DOC] Create USER_AUTH Analytic doc
		if Config.analytics_events['session_user_auth']:
			analytic_doc = {
				'event': 'USER_AUTH',
				'subevent': user_results.args.docs[0]._id,
				'args': {
					'session': results.args.docs[0]._id,
					'REMOTE_ADDR': env['REMOTE_ADDR'],
					'HTTP_USER_AGENT': env['HTTP_USER_AGENT'],
					'client_app': env['client_app'],
				},
			}
			analytic_results = await Registry.module('analytic').create(
				skip_events=[Event.PERM], env=env, doc=analytic_doc
			)
			if analytic_results.status != 200:
				logger.error(
					f'Failed to create \'Analytic\' doc: {analytic_doc}. Results: {analytic_results}'
				)

		return self.status(
			status=200,
			msg='You were successfully authed.',
			args={'session': results.args.docs[0]},
		)

	async def reauth(self, skip_events=[], env={}, query=[], doc={}):
		if str(query['_id'][0]) == 'f00000000000000000000012':
			raise self.exception(
				status=400,
				msg='Reauth is not required for \'__ANON\' user.',
				args={'code': 'ANON_REAUTH'},
			)

		session_query = [{'_id': query['_id'][0]}]
		if 'groups' in query:
			session_query.append({'groups': {'$in': query['groups'][0]}})
		results = await self.read(skip_events=[Event.PERM], env=env, query=session_query)
		if not results.args.count:
			raise self.exception(
				status=403, msg='Session is invalid.', args={'code': 'INVALID_SESSION'}
			)

		if not pbkdf2_sha512.verify(query['token'][0], results.args.docs[0].token_hash):
			raise self.exception(
				status=403,
				msg='Reauth token hash invalid.',
				args={'code': 'INVALID_REAUTH_HASH'},
			)

		del results.args.docs[0]['token_hash']
		results.args.docs[0]['token'] = query['token'][0]

		if results.args.docs[0].expiry < datetime.datetime.utcnow().isoformat():
			results = await self.delete(
				skip_events=[Event.PERM, Event.SOFT],
				env=env,
				query=[{'_id': env['session']._id}],
			)
			raise self.exception(
				status=403, msg='Session had expired.', args={'code': 'SESSION_EXPIRED'}
			)

		# [DOC] update user's last_login timestamp
		await Registry.module('user').update(
			skip_events=[Event.PERM],
			env=env,
			query=[{'_id': results.args.docs[0].user}],
			doc={'login_time': datetime.datetime.utcnow().isoformat()},
		)
		await self.update(
			skip_events=[Event.PERM],
			env=env,
			query=[{'_id': results.args.docs[0]._id}],
			doc={
				'expiry': (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat()
			},
		)
		# [DOC] read user privileges and return them
		user_results = await Registry.module('user').read_privileges(
			skip_events=[Event.PERM],
			env=env,
			query=[{'_id': results.args.docs[0].user._id}],
		)
		results.args.docs[0]['user'] = user_results.args.docs[0]

		# [DOC] Create CONN_AUTH Analytic doc
		if Config.analytics_events['session_conn_reauth']:
			analytic_doc = {
				'event': 'CONN_REAUTH',
				'subevent': env['client_app'],
				'args': {
					'user': user_results.args.docs[0]._id,
					'session': results.args.docs[0]._id,
					'REMOTE_ADDR': env['REMOTE_ADDR'],
					'HTTP_USER_AGENT': env['HTTP_USER_AGENT'],
				},
			}
			analytic_results = await Registry.module('analytic').create(
				skip_events=[Event.PERM], env=env, doc=analytic_doc
			)
			if analytic_results.status != 200:
				logger.error(
					f'Failed to create \'Analytic\' doc: {analytic_doc}. Results: {analytic_results}'
				)
		# [DOC] Create USER_AUTH Analytic doc
		if Config.analytics_events['session_user_reauth']:
			analytic_doc = {
				'event': 'USER_REAUTH',
				'subevent': user_results.args.docs[0]._id,
				'args': {
					'session': results.args.docs[0]._id,
					'REMOTE_ADDR': env['REMOTE_ADDR'],
					'HTTP_USER_AGENT': env['HTTP_USER_AGENT'],
					'client_app': env['client_app'],
				},
			}
			analytic_results = await Registry.module('analytic').create(
				skip_events=[Event.PERM], env=env, doc=analytic_doc
			)
			if analytic_results.status != 200:
				logger.error(
					f'Failed to create \'Analytic\' doc: {analytic_doc}. Results: {analytic_results}'
				)

		return self.status(
			status=200,
			msg='You were successfully reauthed.',
			args={'session': results.args.docs[0]},
		)

	async def signout(self, skip_events=[], env={}, query=[], doc={}):
		if str(query['_id'][0]) == 'f00000000000000000000012':
			raise self.exception(
				status=400,
				msg='Singout is not allowed for \'__ANON\' user.',
				args={'code': 'ANON_SIGNOUT'},
			)

		results = await self.read(
			skip_events=[Event.PERM], env=env, query=[{'_id': query['_id'][0]}]
		)

		if not results.args.count:
			raise self.exception(
				status=403, msg='Session is invalid.', args={'code': 'INVALID_SESSION'}
			)

		results = await self.delete(
			skip_events=[Event.PERM], env=env, query=[{'_id': env['session']._id}]
		)

		# [DOC] Create CONN_AUTH Analytic doc
		if Config.analytics_events['session_conn_deauth']:
			analytic_doc = {
				'event': 'CONN_DEAUTH',
				'subevent': env['client_app'],
				'args': {
					'user': env['session'].user._id,
					'session': env['session']._id,
					'REMOTE_ADDR': env['REMOTE_ADDR'],
					'HTTP_USER_AGENT': env['HTTP_USER_AGENT'],
				},
			}
			analytic_results = await Registry.module('analytic').create(
				skip_events=[Event.PERM], env=env, doc=analytic_doc
			)
			if analytic_results.status != 200:
				logger.error(
					f'Failed to create \'Analytic\' doc: {analytic_doc}. Results: {analytic_results}'
				)
		# [DOC] Create USER_AUTH Analytic doc
		if Config.analytics_events['session_user_deauth']:
			analytic_doc = {
				'event': 'USER_DEAUTH',
				'subevent': env['session'].user._id,
				'args': {
					'session': env['session']._id,
					'REMOTE_ADDR': env['REMOTE_ADDR'],
					'HTTP_USER_AGENT': env['HTTP_USER_AGENT'],
					'client_app': env['client_app'],
				},
			}
			analytic_results = await Registry.module('analytic').create(
				skip_events=[Event.PERM], env=env, doc=analytic_doc
			)
			if analytic_results.status != 200:
				logger.error(
					f'Failed to create \'Analytic\' doc: {analytic_doc}. Results: {analytic_results}'
				)

		return self.status(
			status=200,
			msg='You are successfully signed-out.',
			args={'session': DictObj({'_id': 'f00000000000000000000012'})},
		)
