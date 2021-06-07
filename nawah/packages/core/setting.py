from nawah.base_module import BaseModule
from nawah.enums import Event
from nawah.classes import ATTR, PERM, EXTN, METHOD, InvalidAttrException
from nawah.utils import validate_doc, generate_dynamic_attr
from nawah.config import Config


async def attr_extn_val(
	*,
	mode,
	attr_name,
	attr_type,
	attr_val,
	skip_events,
	env,
	query,
	doc,
	scope,
):
	if type(doc['val']) == dict and '__extn' in doc['val'].keys():
		return {
			'__extn': EXTN(
				module=doc['val']['__extn']['__module'],
				attrs=doc['val']['__extn']['__attrs'],
				force=doc['val']['__extn']['__force'],
			),
			'__val': doc['val']['__extn']['__val'],
		}

	raise InvalidAttrException(
		attr_name=attr_name, attr_type=attr_type, val_type=type(doc['val'])
	)


async def attr_query_mod_type(
	*,
	mode,
	attr_name,
	attr_type,
	attr_val,
	skip_events,
	env,
	query,
	doc,
	scope,
):
	if 'type' not in query or query['type'][0] == 'user_sys':
		raise InvalidAttrException(
			attr_name='type',
			attr_type=ATTR.LITERAL(literal=['global', 'user']),
			val_type=str,
		)


class Setting(BaseModule):
	'''`Setting` module module provides data type and controller for settings in Nawah eco-system. This is used by `User` module tp provide additional user-wise settings. It also allows for global-typed settings.'''

	collection = 'settings'
	attrs = {
		'user': ATTR.ID(desc='`_id` of `User` doc the doc belongs to.'),
		'var': ATTR.STR(
			desc='Name of the setting. This is unique for every `user` in the module.'
		),
		'val': ATTR.ANY(desc='Value of the setting.'),
		'val_type': ATTR.DYNAMIC_ATTR(),
		'type': ATTR.LITERAL(
			desc='Type of the setting. This sets whether setting is global, or belong to user, and whether use can update it or not.',
			literal=['global', 'user', 'user_sys'],
		),
	}
	diff = True
	unique_attrs = [('user', 'var', 'type')]
	extns = {
		'val': ATTR.TYPE(type=attr_extn_val),
	}
	methods = {
		'read': METHOD(
			permissions=[
				PERM(privilege='admin', query_mod={'$limit': 1}),
				PERM(
					privilege='read',
					query_mod={
						'user': '$__user',
						'type': ATTR.TYPE(type=attr_query_mod_type),
						'$limit': 1,
					},
				),
			],
			query_args=[
				{
					'_id': ATTR.ID(),
					'type': ATTR.LITERAL(literal=['global', 'user', 'user_sys']),
				},
				{
					'var': ATTR.STR(),
					'type': ATTR.LITERAL(literal=['global']),
				},
				{
					'var': ATTR.STR(),
					'user': ATTR.ID(),
					'type': ATTR.LITERAL(literal=['user', 'user_sys']),
				},
			],
		),
		'create': METHOD(
			permissions=[
				PERM(privilege='admin'),
				PERM(privilege='create', doc_mod={'type': 'user'}),
			]
		),
		'update': METHOD(
			permissions=[
				PERM(privilege='admin', query_mod={'$limit': 1}),
				PERM(
					privilege='update',
					query_mod={'type': 'user', 'user': '$__user', '$limit': 1},
					doc_mod={'var': None, 'val_type': None, 'type': None},
				),
			],
			query_args=[
				{
					'_id': ATTR.ID(),
					'type': ATTR.LITERAL(literal=['global', 'user', 'user_sys']),
				},
				{
					'var': ATTR.STR(),
					'type': ATTR.LITERAL(literal=['global']),
				},
				{
					'var': ATTR.STR(),
					'user': ATTR.ID(),
					'type': ATTR.LITERAL(literal=['user', 'user_sys']),
				},
			],
		),
		'delete': METHOD(
			permissions=[PERM(privilege='admin', query_mod={'$limit': 1})],
			query_args=[{'_id': ATTR.ID()}, {'var': ATTR.STR()}],
		),
		'retrieve_file': METHOD(
			permissions=[PERM(privilege='*', query_mod={'type': 'global'})],
			get_method=True,
		),
	}

	async def on_create(self, results, skip_events, env, query, doc, payload):
		if doc['type'] in ['user', 'user_sys']:
			if doc['user'] == env['session'].user._id and doc['var'] in Config.user_doc_settings:
				env['session'].user[doc['var']] = doc['val']
		return (results, skip_events, env, query, doc, payload)

	async def pre_update(self, skip_events, env, query, doc, payload):
		for attr in doc.keys():
			if attr == 'val' or attr.startswith('val.'):
				val_attr = attr
				break
		else:
			raise self.exception(
				status=400,
				msg='Could not match doc with any of the required doc_args. Failed sets:[\'val\': Missing]',
				args={'code': 'INVALID_DOC'},
			)

		setting_results = await self.read(skip_events=[Event.PERM], env=env, query=query)
		if not setting_results.args.count:
			raise self.exception(
				status=400, msg='Invalid Setting doc', args={'code': 'INVALID_SETTING'}
			)

		setting = setting_results.args.docs[0]
		# [DOC] Attempt to validate val against Setting val_type
		try:
			exception_raised: Exception = None
			setting_val_type, _ = generate_dynamic_attr(dynamic_attr=setting.val_type)
			await validate_doc(
				mode='update',
				doc=doc,
				attrs={'val': setting_val_type},
				skip_events=skip_events,
				env=env,
				query=query,
			)
		except Exception as e:
			exception_raised = e

		if exception_raised or doc[val_attr] == None:
			raise self.exception(
				status=400,
				msg=f'Invalid value for for Setting doc of type \'{type(doc[val_attr])}\' with required type \'{setting.val_type}\'',
				args={'code': 'INVALID_ATTR'},
			)

		return (skip_events, env, query, doc, payload)

	async def on_update(self, results, skip_events, env, query, doc, payload):
		# [TODO] Update according to the changes of Doc Opers
		try:
			if (
				query['type'][0] in ['user', 'user_sys']
				and query['user'][0] == env['session'].user._id
				and query['var'][0] in Config.user_doc_settings
			):
				if type(doc['val']) == dict and '$add' in doc['val'].keys():
					env['session'].user[query['var'][0]] += doc['val']['$add']
				elif type(doc['val']) == dict and '$multiply' in doc['val'].keys():
					env['session'].user[query['var'][0]] *= doc['val']['$multiply']
				elif type(doc['val']) == dict and '$append' in doc['val'].keys():
					env['session'].user[query['var'][0]].append(doc['val']['$append'])
				elif type(doc['val']) == dict and '$set_index' in doc['val'].keys():
					env['session'].user[query['var'][0]][doc['val']['$index']] = doc['val'][
						'$set_index'
					]
				elif type(doc['val']) == dict and '$del_val' in doc['val'].keys():
					for val in doc['val']['$del_val']:
						env['session'].user[query['var'][0]].remove(val)
				elif type(doc['val']) == dict and '$del_index' in doc['val'].keys():
					del env['session'].user[query['var'][0]][doc['val']['$index']]
				else:
					env['session'].user[query['var'][0]] = doc['val']
		except:
			pass
		return (results, skip_events, env, query, doc, payload)
