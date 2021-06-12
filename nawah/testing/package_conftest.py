from nawah.classes import (
	Query,
	DictObj,
	ATTR,
	BaseModel,
	MethodException,
	InvalidPermissionsExcpetion,
	InvalidCallArgsException,
)
from nawah.base_method._check_permissions import check_permissions
from nawah.base_method._validate_args import validate_args
from nawah.enums import Event, NAWAH_VALUES
from nawah.config import Config
from nawah import base_module, registry

from typing import Dict, Any
from bson import ObjectId

import pytest, mock, re, datetime


class MockBaseModule:
	collection = None
	attrs = None
	diff = None
	create_draft = None
	update_draft = None
	defaults = None
	unique_attrs = None
	extns = None
	privileges = None
	methods = None
	cache = None
	analytics = None

	package_name = None
	module_name = None

	def _pre_initialise(self):
		raise NotImplementedError()

	def _initialise(self):
		raise NotImplementedError()

	def status(self, *, status, msg, args=None):
		status_dict = {'status': status, 'msg': msg, 'args': {}}
		if args and type(args) == DictObj:
			if 'code' in args:
				args[
					'code'
				] = f'{self.package_name.upper()}_{self.module_name.upper()}_{args["code"]}'
			status_dict['args'] = args
		elif args and type(args) == dict:
			if 'code' in args.keys():
				args[
					'code'
				] = f'{self.package_name.upper()}_{self.module_name.upper()}_{args["code"]}'
			status_dict['args'] = args
		return DictObj(status_dict)

	def exception(self, *, status, msg, args=None):
		status_dict = {'status': status, 'msg': msg, 'args': {}}
		if args and type(args) == DictObj:
			if 'code' in args:
				args[
					'code'
				] = f'{self.package_name.upper()}_{self.module_name.upper()}_{args["code"]}'
			status_dict['args'] = args
		elif args and type(args) == dict:
			if 'code' in args.keys():
				args[
					'code'
				] = f'{self.package_name.upper()}_{self.module_name.upper()}_{args["code"]}'
			status_dict['args'] = args
		return MethodException(DictObj(status_dict))

	async def pre_read(self, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler pre_read is not implemented')

	async def on_read(self, results, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler on_read is not implemented')

	async def read(self, skip_events=[], env={}, query=[], doc={}):
		raise NotImplementedError('Method read is not implemented')

	async def pre_watch(self, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler pre_watch is not implemented')

	async def on_watch(self, results, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler on_watch is not implemented')

	async def watch(self, skip_events=[], env={}, query=[], doc={}):
		raise NotImplementedError('Method watch is not implemented')

	async def pre_create(self, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler pre_create is not implemented')

	async def on_create(self, results, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler on_create is not implemented')

	async def create(self, skip_events=[], env={}, query=[], doc={}):
		raise NotImplementedError('Method create is not implemented')

	async def pre_update(self, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler pre_update is not implemented')

	async def on_update(self, results, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler on_update is not implemented')

	async def update(self, skip_events=[], env={}, query=[], doc={}):
		raise NotImplementedError('Method update is not implemented')

	async def pre_delete(self, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler pre_delete is not implemented')

	async def on_delete(self, results, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler on_delete is not implemented')

	async def delete(self, skip_events=[], env={}, query=[], doc={}):
		raise NotImplementedError('Method delete is not implemented')

	async def pre_create_file(self, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler pre_create_file is not implemented')

	async def on_create_file(self, results, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler on_create_file is not implemented')

	async def create_file(self, skip_events=[], env={}, query=[], doc={}):
		raise NotImplementedError('Method create_file is not implemented')

	async def pre_delete_file(self, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler pre_delete_file is not implemented')

	async def on_delete_file(self, results, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler on_delete_file is not implemented')

	async def delete_file(self, skip_events=[], env={}, query=[], doc={}):
		raise NotImplementedError('Method delete_file is not implemented')

	async def pre_retrieve_file(self, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler pre_retrieve_file is not implemented')

	async def on_retrieve_file(self, results, skip_events, env, query, doc, payload):
		raise NotImplementedError('Handler on_retrieve_file is not implemented')

	async def retrieve_file(self, skip_events=[], env={}, query=[], doc={}):
		raise NotImplementedError('Method retrieve_file is not implemented')

	async def update_cache(self, skip_events=[], env={}, query=[], doc={}):
		raise NotImplementedError('Method update_cache is not implemented')


class MockRegistry(registry.Registry):
	modules: Dict[str, MockBaseModule] = {}

	@staticmethod
	def module(module):
		try:
			return MockRegistry.modules[module]
		except KeyError:
			raise registry.InvalidModuleException(module=module)


base_module.BaseModule = MockBaseModule  # type: ignore
registry.Registry = MockRegistry  # type: ignore


def pytest_configure(config):
	config.addinivalue_line(
		'markers',
		'setup_test(modules, l10n, vars, types): Config mocked environment for testing.',
	)


def pytest_runtest_setup(item):
	for marker in item.iter_markers(name='setup_test'):
		setup_test(**marker.kwargs)


def setup_test(*, modules=None, l10n_dicts=None, vars=None, types=None):
	MockRegistry.modules = {}
	Config.l10n = {}
	Config.vars = {}
	Config.types = {}

	if modules:
		for module_class in modules.keys():
			module = module_class()
			module.package_name = (
				module.__module__.replace('modules.', '').upper().split('.')[-2]
			)
			module.module_name = re.sub(
				r'([A-Z])',
				r'_\1',
				module.__class__.__name__[0].lower() + module.__class__.__name__[1:],
			).lower()
			for method_name in modules[module_class].keys():
				mock_method = mock.AsyncMock()
				mock_method.return_value = modules[module_class][method_name]
				setattr(module, method_name, mock_method)

			MockRegistry.modules[module.module_name] = module

	if l10n_dicts:
		Config.l10n = l10n_dicts

	if vars:
		Config.vars = vars

	if types:
		Config.types = types


@pytest.fixture
def mock_env():
	def _(*, session=None, user=None, privileges=None):
		if not session:
			session = {
				'_id': ObjectId('f00000000000000000000012'),
				'user': None,
				'host_add': '127.0.0.1',
				'user_agent': '__ANON_TOKEN_000000000000000000000000',
				'timestamp': '1970-01-01T00:00:00',
				'expiry': '1970-01-01T00:00:00',
				'token': '__ANON_TOKEN_000000000000000000000000',
				'token_hash': '__ANON_TOKEN_000000000000000000000000',
			}

		if not user:
			user = {
				'_id': ObjectId('f00000000000000000000011'),
				'name': {'na_NA': '__ANON'},
				'groups': [],
				'privileges': None,
				'locale': 'na_NA',
			}

		if not privileges:
			privileges = {}

		session = DictObj(session)
		user = DictObj(user)
		session['user'] = user
		user['privileges'] = privileges

		return {
			'id': 0,
			'conn': None,
			'REMOTE_ADDR': '127.0.0.1',
			'ws': None,
			'watch_tasks': {},
			'init': False,
			'last_call': datetime.datetime.utcnow(),
			'quota': {
				'counter': 0,
				'last_check': datetime.datetime.utcnow(),
			},
			'HTTP_USER_AGENT': '',
			'HTTP_ORIGIN': '',
			'session': session,
		}

	return _


@pytest.fixture
def call_handler_pre(mock_env):
	async def _(
		*, module, handler, skip_events=[], env=None, query=[], doc={}, payload={}
	):
		if not env:
			env = mock_env()
		query = Query(query)
		return await getattr(MockRegistry.modules[module], handler)(
			skip_events=skip_events, env=env, query=query, doc=doc, payload=payload
		)

	return _


@pytest.fixture
def call_handler_on(mock_env):
	async def _(
		*, module, handler, results, skip_events=[], env=None, query=[], doc={}, payload={}
	):
		if not env:
			env = mock_env()
		query = Query(query)
		return await getattr(MockRegistry.modules[module], handler)(
			results=results,
			skip_events=skip_events,
			env=env,
			query=query,
			doc=doc,
			payload=payload,
		)

	return _


@pytest.fixture
def call_method_check_permissions(mock_env):
	async def _(*, module, method, skip_events=[], env=None, query=[], doc={}):
		if not env:
			env = mock_env()
		query = Query(query)

		permissions = await check_permissions(
			skip_events=skip_events,
			env=env,
			query=query,
			doc=doc,
			module=MockRegistry.modules[module],
			permissions=MockRegistry.modules[module].methods[method].permissions,
		)

		return permissions

	return _


@pytest.fixture
def call_method_validate_args():
	async def _(*, args, args_list_label, args_list):
		await validate_args(
			args=args,
			args_list_label=args_list_label,
			args_list=args_list,
		)

	return _


@pytest.fixture
def call_method(mock_env, call_method_check_permissions, call_method_validate_args):
	async def _(*, module, method, skip_events=[], env=None, query=[], doc={}):
		if not env:
			env = mock_env()
		query = Query(query)

		# [DOC] Following code is actual copy of BaseModule.__call__ method as to replicate the complete process of calling an initialised Nawah module method

		if Event.PERM not in skip_events:
			permissions_check = await call_method_check_permissions(
				module=module, method=method, skip_events=skip_events, env=env, query=query, doc=doc
			)

			if type(permissions_check['query_mod']) == dict:
				permissions_check['query_mod'] = [permissions_check['query_mod']]
			for i in range(len(permissions_check['query_mod'])):
				if type(permissions_check['query_mod'][i]) == dict:
					query_set_list = [permissions_check['query_mod'][i]]
				elif type(permissions_check['query_mod'][i]) == list:
					query_set_list = permissions_check['query_mod'][i]
				for query_set in query_set_list:
					del_args = []
					for attr in query_set.keys():
						if query_set[attr] == None:
							del_args.append(attr)
					for attr in del_args:
						del query_set[attr]
			query.append(permissions_check['query_mod'])

			del_args = []
			for attr in permissions_check['doc_mod'].keys():
				if permissions_check['doc_mod'][attr] == None:
					permissions_check['doc_mod'][attr] = NAWAH_VALUES.NONE_VALUE
			for attr in del_args:
				del permissions_check['doc_mod'][attr]
			doc.update(permissions_check['doc_mod'])
			doc = {
				attr: doc[attr] for attr in doc.keys() if doc[attr] != NAWAH_VALUES.NONE_VALUE
			}

		if Event.ARGS not in skip_events:
			if args_list := MockRegistry.modules[module].methods[method].query_args:
				if type(args_list) != list:
					args_list = [args_list]

				# [DOC] Call ATTR.validate_type on query_args to initialise Attr Type TYPE
				for args_set in args_list:
					for attr in args_set.keys():
						ATTR.validate_type(attr_type=args_set[attr])

				await validate_args(
					args=query,
					args_list_label='query',
					args_list=args_list,
				)

			if args_list := MockRegistry.modules[module].methods[method].doc_args:
				if type(args_list) != list:
					args_list = [args_list]

				# [DOC] Call ATTR.validate_type on query_args to initialise Attr Type TYPE
				for args_set in args_list:
					for attr in args_set.keys():
						ATTR.validate_type(attr_type=args_set[attr])

				await validate_args(
					args=doc,
					args_list_label='doc',
					args_list=args_list,
				)

		for arg in doc.keys():
			if type(doc[arg]) == BaseModel:
				doc[arg] = doc[arg]._id  # type: ignore

		# [DOC] check if $soft oper is set to add it to events
		if '$soft' in query and query['$soft'] == True:
			skip_events.append(Event.SOFT)
			del query['$soft']

		# [DOC] check if $extn oper is set to add it to events
		if '$extn' in query and query['$extn'] == False:
			skip_events.append(Event.EXTN)
			del query['$extn']

		return await getattr(MockRegistry.modules[module], method)(
			skip_events=skip_events, env=env, query=query, doc=doc
		)

	return _
