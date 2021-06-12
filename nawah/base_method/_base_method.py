from nawah.classes import (
	DictObj,
	BaseModel,
	Query,
	JSONEncoder,
	ATTR,
	NAWAH_EVENTS,
	NAWAH_ENV,
	NAWAH_DOC,
	NAWAH_QUERY,
	PERM,
	WATCH_TASK,
	METHOD,
	MethodException,
	InvalidAttrException,
	InvalidCallArgsException,
)
from nawah.enums import Event, NAWAH_VALUES
from nawah.config import Config

from ._check_permissions import check_permissions, InvalidPermissionsExcpetion
from ._validate_args import validate_args

from asyncio import coroutine
from aiohttp.web import WebSocketResponse
from typing import (
	List,
	Dict,
	Union,
	Any,
	Tuple,
	Set,
	AsyncGenerator,
	TYPE_CHECKING,
	Literal,
	Iterable,
	Optional,
	cast,
	Awaitable,
)

import logging, copy, traceback, sys, asyncio

if TYPE_CHECKING:
	from nawah.base_module import BaseModule

logger = logging.getLogger('nawah')


class BaseMethod:
	def __init__(
		self,
		module: 'BaseModule',
		method: str,
		permissions: List[PERM],
		query_args: List[Dict[str, ATTR]],
		doc_args: List[Dict[str, ATTR]],
		watch_method: bool,
		get_method: bool,
		post_method: bool,
	):
		self.module = module
		self.method = method
		self.permissions = permissions
		self.query_args = query_args
		self.doc_args = doc_args
		self.watch_method = watch_method
		self.get_method = get_method
		self.post_method = post_method

	async def __call__(
		self,
		*,
		skip_events: NAWAH_EVENTS = None,
		env: NAWAH_ENV = None,
		query: Union[NAWAH_QUERY, Query] = None,
		doc: NAWAH_DOC = None,
		call_id: str = None,
	) -> Optional[DictObj]:
		if skip_events == None:
			skip_events = []
		if env == None:
			env = {}
		if query == None:
			query = []
		if doc == None:
			doc = {}
		skip_events = cast(NAWAH_EVENTS, skip_events)
		env = cast(NAWAH_ENV, env)
		query = cast(Union[NAWAH_QUERY, Query], query)
		doc = cast(NAWAH_DOC, doc)
		call_id = cast(str, call_id)
		# [DOC] Convert list query to Query object
		query = Query(copy.deepcopy(query))
		# [DOC] deepcopy() doc object ro prevent mutating original doc
		doc = copy.deepcopy(doc)

		logger.debug(
			f'Calling: {self.module.module_name}.{self.method}, with skip_events:{skip_events}, query:{str(query)[:250]}, doc.keys:{doc.keys()}'
		)

		if call_id:
			for analytics_set in self.module.analytics:
				if analytics_set.condition(
					skip_events=skip_events,
					env=env,
					query=query,
					doc=doc,
					method=self.method,
				):
					try:
						analytic_doc = analytics_set.doc(
							skip_events=skip_events,
							env=env,
							query=query,
							doc=doc,
							method=self.method,
						)
						analytic_results = await Config.modules['analytic'].create(
							skip_events=[Event.PERM], env=env, doc=analytic_doc
						)
					except Exception as e:
						logger.error(
							f'Failed to create \'Analytic\' doc: {analytic_doc}. Results: {analytic_results}'
						)
					if analytic_results.status != 200:
						logger.error(
							f'Failed to create \'Analytic\' doc: {analytic_doc}. Results: {analytic_results}'
						)

		if Event.PERM not in skip_events and env['session']:
			try:
				permissions_check = await check_permissions(
					skip_events=skip_events,
					env=env,
					query=query,
					doc=doc,
					module=self.module,
					permissions=self.permissions,
				)
				logger.debug(f'permissions_check: Pass.')
			except Exception as e:
				logger.debug(f'permissions_check: Fail.')
				# [DOC] InvalidAttrException, usually raised by Attr Type TYPE
				if type(e) == InvalidAttrException:
					return await self.return_results(
						ws=env['ws'] if 'ws' in env.keys() else None,
						results=DictObj(
							{
								'status': 400,
								'msg': str(e),
								'args': DictObj({'code': 'INVALID_ARGS'}),
							}
						),
						call_id=call_id,
					)
				# [DOC] Any other exception, treat as server error
				elif type(e) != InvalidPermissionsExcpetion:
					logger.error(f'An error occurred. Details: {traceback.format_exc()}.')
					tb = sys.exc_info()[2]
					if tb is not None:
						prev = tb
						current = tb.tb_next
						while current is not None:
							prev = current
							current = current.tb_next
						logger.error(f'Scope variables: {JSONEncoder().encode(prev.tb_frame.f_locals)}')
					return await self.return_results(
						ws=env['ws'] if 'ws' in env.keys() else None,
						results=DictObj(
							{
								'status': 500,
								'msg': 'Unexpected error has occurred.',
								'args': DictObj({'code': 'CORE_SERVER_ERROR'}),
							}
						),
						call_id=call_id,
					)
				# [DOC] Regular InvalidPermissionsExcpetion failure
				return await self.return_results(
					ws=env['ws'] if 'ws' in env.keys() else None,
					results=DictObj(
						{
							'status': 403,
							'msg': 'You don\'t have permissions to access this endpoint.',
							'args': DictObj({'code': 'CORE_SESSION_FORBIDDEN'}),
						}
					),
					call_id=call_id,
				)
			else:
				if type(permissions_check['query_mod']) == dict:
					permissions_check['query_mod'] = [permissions_check['query_mod']]
				for i in range(len(permissions_check['query_mod'])):
					# [DOC] attempt to process query_set as nested-list (OR) even if it's dict
					if type(permissions_check['query_mod'][i]) == dict:
						query_set_list = [permissions_check['query_mod'][i]]
					elif type(permissions_check['query_mod'][i]) == list:
						query_set_list = permissions_check['query_mod'][i]
					# [DOC] loop over query_set_list, query_set
					for query_set in query_set_list:
						del_args = []
						for attr in query_set.keys():
							# [DOC] Flag attr for deletion if value is None
							# [TODO] Check why the condition included (or type(query_set[attr]) == ATTR_MOD:)
							if query_set[attr] == None:
								del_args.append(attr)
						for attr in del_args:
							del query_set[attr]
				# [DOC] Append query permissions args to query
				query.append(permissions_check['query_mod'])

				del_args = []
				for attr in permissions_check['doc_mod'].keys():
					# [DOC] Replace None value with NONE_VALUE to bypass later validate step
					if permissions_check['doc_mod'][attr] == None:
						permissions_check['doc_mod'][attr] = NAWAH_VALUES.NONE_VALUE
				for attr in del_args:
					del permissions_check['doc_mod'][attr]
				# [DOC] Update doc with doc permissions args
				doc.update(permissions_check['doc_mod'])
				doc = {
					attr: doc[attr] for attr in doc.keys() if doc[attr] != NAWAH_VALUES.NONE_VALUE
				}

		if Event.ARGS not in skip_events:
			try:
				await validate_args(args=query, args_list_label='query', args_list=self.query_args)
			except InvalidCallArgsException as e:
				test_query = e.args[0]
				for i in range(len(test_query)):
					test_query[i] = (
						'['
						+ ', '.join(
							[
								f'\'{arg}\': {val.capitalize()}'
								for arg, val in test_query[i].items()
								if val != True
							]
						)
						+ ']'
					)
				return await self.return_results(
					ws=env['ws'] if 'ws' in env.keys() else None,
					results=DictObj(
						{
							'status': 400,
							'msg': 'Could not match query with any of the required query_args. Failed sets:'
							+ ', '.join(test_query),
							'args': DictObj(
								{
									'code': f'{self.module.package_name.upper()}_{self.module.module_name.upper()}_INVALID_QUERY'
								}
							),
						}
					),
					call_id=call_id,
				)

			try:
				await validate_args(args=doc, args_list_label='doc', args_list=self.doc_args)
			except InvalidCallArgsException as e:
				test_doc = e.args[0]
				for i in range(len(test_doc)):
					test_doc[i] = (
						'['
						+ ', '.join(
							[
								f'\'{arg}\': {val.capitalize()}'
								for arg, val in test_doc[i].items()
								if val != True
							]
						)
						+ ']'
					)
				return await self.return_results(
					ws=env['ws'] if 'ws' in env.keys() else None,
					results=DictObj(
						{
							'status': 400,
							'msg': 'Could not match doc with any of the required doc_args. Failed sets:'
							+ ', '.join(test_doc),
							'args': DictObj(
								{
									'code': f'{self.module.package_name.upper()}_{self.module.module_name.upper()}_INVALID_DOC'
								}
							),
						}
					),
					call_id=call_id,
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

		try:
			# [DOC] Use getattr to get the method implementation as module._method_METHOD_NAME, which is a fake name that allows BaseModule.__getattribute__ to correctly return the implementation rather than BaseMethod
			method = getattr(self.module, f'_method_{self.method}')
			# [DOC] Call method function
			if self.watch_method:
				await env['ws'].send_str(
					JSONEncoder().encode(
						{
							'status': 200,
							'msg': 'Created watch task.',
							'args': {
								'code': 'CORE_WATCH_OK',
								'watch': call_id,
								'call_id': call_id,
							},
						}
					)
				)
				watch_loop = self.watch_loop(
					ws=env['ws'],
					stream=method(skip_events=skip_events, env=env, query=query, doc=doc),
					call_id=call_id,
					watch_task=env['watch_tasks'][call_id],
				)
				env['watch_tasks'][call_id] = {'watch': watch_loop}
				env['watch_tasks'][call_id]['task'] = asyncio.create_task(watch_loop)
				return None
			else:
				try:
					results = await method(skip_events=skip_events, env=env, query=query, doc=doc)
				except MethodException as e:
					results = e.args[0]

				if type(results) == coroutine:
					raise TypeError('Method returned coroutine rather than acceptable results format.')

				results = DictObj(results)
				try:
					results['args'] = DictObj(results.args)
				except Exception:
					results['args'] = DictObj({})

				logger.debug(f'Call results: {JSONEncoder().encode(results)}')
				# [DOC] Check for session in results
				if 'session' in results.args:
					if results.args.session._id == 'f00000000000000000000012':
						# [DOC] Updating session to __ANON
						anon_user = Config.compile_anon_user()
						anon_session = Config.compile_anon_session()
						anon_session['user'] = DictObj(anon_user)
						env['session'] = BaseModel(anon_session)
					else:
						# [DOC] Updating session to user
						env['session'] = results.args.session

				return await self.return_results(
					ws=env['ws'] if 'ws' in env.keys() else None, results=results, call_id=call_id
				)
			# query = Query([])
		except Exception as e:
			logger.error(f'An error occurred. Details: {traceback.format_exc()}.')
			tb = sys.exc_info()[2]
			if tb is not None:
				prev = tb
				current = tb.tb_next
				while current is not None:
					prev = current
					current = current.tb_next
				logger.error(f'Scope variables: {JSONEncoder().encode(prev.tb_frame.f_locals)}')
			query = Query([])
			if Config.debug:
				return await self.return_results(
					ws=env['ws'] if 'ws' in env.keys() else None,
					results=DictObj(
						{
							'status': 500,
							'msg': f'Unexpected error has occurred [method:{self.module.module_name}.{self.method}] [{str(e)}].',
							'args': DictObj(
								{
									'code': 'CORE_SERVER_ERROR',
									'method': f'{self.module.module_name}.{self.method}',
									'err': str(e),
								}
							),
						}
					),
					call_id=call_id,
				)
			else:
				return await self.return_results(
					ws=env['ws'] if 'ws' in env.keys() else None,
					results=DictObj(
						{
							'status': 500,
							'msg': 'Unexpected error has occurred.',
							'args': DictObj({'code': 'CORE_SERVER_ERROR'}),
						}
					),
					call_id=call_id,
				)

	async def return_results(
		self, ws: Optional[WebSocketResponse], results: DictObj, call_id: Optional[str]
	) -> Optional[DictObj]:
		if call_id and call_id != '__TEST__':
			results.args['call_id'] = call_id
			ws = cast(WebSocketResponse, ws)
			await ws.send_str(JSONEncoder().encode(results))
			return None
		else:
			return results

	async def watch_loop(
		self,
		ws: WebSocketResponse,
		stream: AsyncGenerator[DictObj, DictObj],
		call_id: str,
		watch_task: WATCH_TASK,
	) -> None:
		logger.debug('Preparing async loop at BaseMethod')
		async for results in stream:
			logger.debug(f'Received watch results at BaseMethod: {results}')
			# [DOC] Update watch_task stream value with stream object
			if 'stream' in results.keys():
				watch_task['stream'] = results['stream']
				continue

			results = DictObj(results)
			try:
				results['args'] = DictObj(results.args)
			except Exception:
				results['args'] = DictObj({})

			results.args['call_id'] = call_id
			results.args['watch'] = call_id

			await ws.send_str(JSONEncoder().encode(results))

		logger.debug('Generator ended at BaseMethod.')
