from nawah.config import Config
from nawah.enums import Event, DELETE_STRATEGY, NAWAH_VALUES
from nawah import data as Data
from nawah.utils import (
	validate_doc,
	expand_attr,
	update_attr_values,
)
from nawah.classes import (
	DictObj,
	BaseModel,
	Query,
	NAWAH_EVENTS,
	NAWAH_ENV,
	Query,
	NAWAH_QUERY,
	NAWAH_DOC,
	ATTR,
	PERM,
	EXTN,
	METHOD,
	CACHE,
	CACHED_QUERY,
	ANALYTIC,
	PRE_HANDLER_RETURN,
	ON_HANDLER_RETURN,
	MethodException,
	InvalidAttrTypeException,
	InvalidAttrTypeArgException,
	InvalidAttrException,
	MissingAttrException,
	ConvertAttrException,
)
from nawah.base_method import BaseMethod

from typing import (
	List,
	Dict,
	Union,
	Tuple,
	Callable,
	Any,
	TypedDict,
	cast,
	Literal,
	Optional,
	AsyncGenerator,
)

from PIL import Image
from bson import ObjectId
import traceback, logging, datetime, re, sys, io, copy, asyncio

logger = logging.getLogger('nawah')


class BaseModule:
	_nawah_module: bool = True

	collection: Optional[str]
	attrs: Dict[str, ATTR]
	diff: Union[bool, ATTR]
	create_draft: Union[bool, ATTR]
	update_draft: Union[bool, ATTR]
	defaults: Dict[str, Any]
	unique_attrs: List[Union[str, Tuple[str, ...]]]
	extns: Dict[str, Union[EXTN, ATTR]]
	privileges: List[str]
	methods: Dict[str, METHOD]
	cache: List[CACHE]
	analytics: List[ANALYTIC]

	package_name: str
	module_name: str

	def __init__(self):
		if not getattr(self, 'collection', None):
			self.collection = None
		if not getattr(self, 'attrs', None):
			self.attrs = {}
		if not getattr(self, 'diff', None):
			self.diff = False
		if not getattr(self, 'create_draft', None):
			self.create_draft = False
		if not getattr(self, 'update_draft', None):
			self.update_draft = False
		if not getattr(self, 'defaults', None):
			self.defaults = {}
		if not getattr(self, 'unique_attrs', None):
			self.unique_attrs = []
		if not getattr(self, 'extns', None):
			self.extns = {}
		if not getattr(self, 'privileges', None):
			self.privileges = ['read', 'create', 'update', 'delete', 'admin']
		if not getattr(self, 'methods', None):
			self.methods = {}
		if not getattr(self, 'cache', None):
			self.cache = []
		if not getattr(self, 'analytics', None):
			self.analytics = []

		# [DOC] Populate package and module names for in-context use.
		self.package_name = self.__module__.replace('modules.', '').upper().split('.')[-2]
		self.module_name = re.sub(
			r'([A-Z])',
			r'_\1',
			self.__class__.__name__[0].lower() + self.__class__.__name__[1:],
		).lower()

	def _pre_initialise(self) -> None:
		pass

	def _initialise(self) -> None:
		# [DOC] Call _pre_initialise for advanced module initialisation
		self._pre_initialise()
		# [DOC] Check attrs for any invalid type
		for attr in self.attrs.keys():
			try:
				logger.debug(
					f'Attempting to validate Attr Type for \'{attr}\' of module \'{self.module_name}\'.'
				)
				ATTR.validate_type(attr_type=self.attrs[attr])
			except InvalidAttrTypeException as e:
				logger.error(
					f'Invalid Attr Type for \'{attr}\' of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
				)
				exit(1)
			except InvalidAttrTypeArgException as e:
				logger.error(
					f'Invalid Attr Type Arg for \'{attr}\' of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
				)
				exit(1)
			# [DOC] Check default for invalid types, update default value
			for default in self.defaults.keys():
				if (
					default == attr or default.startswith(f'{attr}.') or default.startswith(f'{attr}:')
				):
					if type(self.defaults[default]) == ATTR:
						if self.defaults[default]._type != 'TYPE':
							logger.error(
								f'Invalid Attr Type for default \'{default}\' of module \'{self.module_name}\'. Only Attr Type TYPE is allowed. Exiting.'
							)
							exit(1)
						logger.debug(
							f'Attempting to validate Attr Type of default \'{default}\' of module \'{self.module_name}\'.'
						)
						try:
							ATTR.validate_type(attr_type=self.defaults[default])
						except InvalidAttrTypeException as e:
							logger.error(
								f'Invalid Attr Type for default \'{default}\' of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
							)
							exit(1)
						except InvalidAttrTypeArgException as e:
							logger.error(
								f'Invalid Attr Type Arg for default \'{default}\' of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
							)
							exit(1)
					logger.debug(
						f'Updating default value for attr \'{attr}\' to: \'{self.defaults[default]}\''
					)
					update_attr_values(
						attr=ATTR.TYPED_DICT(dict=self.attrs),
						value='default',
						value_path=default,
						value_val=self.defaults[default],
					)
			# [DOC] Update extn value
			for extn in self.extns.keys():
				if extn == attr or extn.startswith(f'{attr}.') or extn.startswith(f'{attr}:'):
					logger.debug(f'Updating extn value for attr \'{extn}\' to: \'{self.extns[extn]}\'')
					update_attr_values(
						attr=ATTR.TYPED_DICT(dict=self.attrs),
						value='extn',
						value_path=extn,
						value_val=self.extns[extn],
					)
		# [DOC] Abstract methods as BaseMethod objects
		for method_name in self.methods.keys():
			method = self.methods[method_name]
			# [DOC] Check value type
			if type(method) != METHOD:
				logger.error(
					f'Invalid method \'{method}\' of module \'{self.module_name}\'. Exiting.'
				)
				exit(1)
			# [DOC] Set Method._module value to create back-link from child to parent
			method._module = self
			method._method_name = method_name
			# [DOC] Check valid method (and initialise it)
			try:
				method._validate()
			except Exception as e:
				logger.error(e)
				logger.error('Exiting.')
				exit(1)
		# [DOC] Check extns for invalid extended attrs
		for attr in self.extns.keys():
			if type(self.extns[attr]) not in [EXTN, ATTR]:
				logger.error(
					f'Invalid extns attr \'{attr}\' of module \'{self.module_name}\'. Exiting.'
				)
				exit(1)
			if type(self.extns[attr]) == ATTR:
				self.extns[attr] = cast(ATTR, self.extns[attr])
				if self.extns[attr]._type != 'TYPE':
					logger.error(
						f'Invalid Attr Type for extn \'{attr}\' of module \'{self.module_name}\'. Only Attr Type TYPE is allowed. Exiting.'
					)
					exit(1)
				logger.debug(
					f'Attempting to validate Attr Type of extn \'{attr}\' of module \'{self.module_name}\'.'
				)
				try:
					ATTR.validate_type(attr_type=self.extns[attr])
				except InvalidAttrTypeException as e:
					logger.error(
						f'Invalid Attr Type for extn \'{attr}\' of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
					)
					exit(1)
				except InvalidAttrTypeArgException as e:
					logger.error(
						f'Invalid Attr Type Arg for extn \'{attr}\' of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
					)
					exit(1)

		# [DOC] Check valid type, value for diff
		if type(self.diff) not in [bool, ATTR]:
			logger.error(f'Invalid diff for module \'{self.module_name}\'. Exiting.')
			exit(1)
		if type(self.diff) == ATTR:
			self.diff = cast(ATTR, self.diff)
			if self.diff._type != 'TYPE':
				logger.error(
					f'Invalid Attr Type for diff of module \'{self.module_name}\'. Only Attr Type TYPE is allowed. Exiting.'
				)
				exit(1)
			logger.debug(
				f'Attempting to validate Attr Type diff of module \'{self.module_name}\'.'
			)
			try:
				ATTR.validate_type(attr_type=self.diff)
			except InvalidAttrTypeException as e:
				logger.error(
					f'Invalid Attr Type for diff of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
				)
				exit(1)
			except InvalidAttrTypeArgException as e:
				logger.error(
					f'Invalid Attr Type Arg for diff of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
				)
				exit(1)

		# [DOC] Check valid types, values for create_draft, update_draft
		for attr in ['create_draft', 'update_draft']:
			if type(getattr(self, attr)) not in [bool, ATTR]:
				logger.error(f'Invalid {attr} for module \'{self.module_name}\'. Exiting.')
				exit(1)
			if type(getattr(self, attr)) == ATTR:
				if getattr(self, attr)._type != 'TYPE':
					logger.error(
						f'Invalid Attr Type for {attr} of module \'{self.module_name}\'. Only Attr Type TYPE is allowed. Exiting.'
					)
					exit(1)
				logger.debug(
					f'Attempting to validate Attr Type {attr} of module \'{self.module_name}\'.'
				)
				try:
					ATTR.validate_type(attr_type=getattr(self, attr))
				except InvalidAttrTypeException as e:
					logger.error(
						f'Invalid Attr Type for {attr} of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
					)
					exit(1)
				except InvalidAttrTypeArgException as e:
					logger.error(
						f'Invalid Attr Type Arg for {attr} of module \'{self.module_name}\'. Original validation error: {str(e)}. Exiting.'
					)
					exit(1)

		logger.debug(f'Initialised module {self.module_name}')

	def status(
		self, *, status: int, msg: str, args: Optional[Union[Dict[str, Any], DictObj]] = None
	) -> DictObj:
		if status != 200:
			logger.warning(
				f'BaseModule.status with msg \'{msg}\' is not called with \'200\' status code. Use BaseModule.exception instead.'
			)

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

	def exception(
		self, *, status: int, msg: str, args: Optional[Union[Dict[str, Any], DictObj]] = None
	) -> MethodException:
		if status == 200:
			logger.warning(
				f'BaseModule.exception with msg \'{msg}\' is called with \'200\' status code. Use BaseModule.status instead.'
			)

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

	def __getattribute__(self, attr):
		# [DOC] Module is not yet initialised, skip to return exact attr
		try:
			object.__getattribute__(self, 'methods')
		except AttributeError:
			return object.__getattribute__(self, attr)
		# [DOC] Module is initialised attempt to check for methods
		if attr in object.__getattribute__(self, 'methods').keys():
			return object.__getattribute__(self, 'methods')[attr]
		elif attr.startswith('_method_'):
			return object.__getattribute__(self, attr.replace('_method_', ''))
		else:
			return object.__getattribute__(self, attr)

	async def pre_read(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> PRE_HANDLER_RETURN:
		return (skip_events, env, query, doc, payload)

	async def on_read(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> ON_HANDLER_RETURN:
		return (results, skip_events, env, query, doc, payload)

	async def read(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		if not self.collection:
			raise self.exception(
				status=400,
				msg='Utility module can\'t call \'read\' method.',
				args={'code': 'INVALID_CALL'},
			)

		payload: Dict[str, Any] = {}

		query = cast(Query, query)

		if Event.PRE not in skip_events:
			pre_read = await self.pre_read(
				skip_events=skip_events, env=env, query=query, doc=doc, payload=payload
			)
			skip_events, env, query, doc, payload = pre_read

			# [DOC] Check if __results are passed in payload
			if '__results' in payload.keys():
				return payload['__results']

		# [DOC] Check for cache workflow instructins
		if self.cache:
			results: Optional[Dict[str, Any]] = None
			for cache_set in self.cache:
				if cache_set.condition(skip_events=skip_events, env=env, query=query) == True:
					cache_key = f'{str(query._query)}____{str(query._special)}'
					if cache_key in cache_set.queries.keys():
						if cache_set.period:
							if (
								cache_set.queries[cache_key].query_time
								+ datetime.timedelta(seconds=cache_set.period)
							) < datetime.datetime.utcnow():
								if not results:
									results = await Data.read(
										env=env,
										collection_name=self.collection,
										attrs=self.attrs,
										query=query,
									)
								cache_set.queries[cache_key] = CACHED_QUERY(results=results)
							else:
								results = cache_set.queries[cache_key].results
								results['cache'] = cache_set.queries[cache_key].query_time.isoformat()
						else:
							results = cache_set.queries[cache_key].results
							results['cache'] = cache_set.queries[cache_key].query_time.isoformat()
					else:
						if not results:
							results = await Data.read(
								env=env,
								collection_name=self.collection,
								attrs=self.attrs,
								query=query,
							)
						cache_set.queries[cache_key] = CACHED_QUERY(results=results)
			if not results:
				results = await Data.read(
					env=env,
					collection_name=self.collection,
					attrs=self.attrs,
					query=query,
					skip_extn='$extn' in query or Event.EXTN in skip_events,
				)
		else:
			results = await Data.read(
				env=env,
				collection_name=self.collection,
				attrs=self.attrs,
				query=query,
				skip_extn='$extn' in query or Event.EXTN in skip_events,
			)
		if Event.ON not in skip_events:
			on_read = await self.on_read(
				results=results,
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				payload=payload,
			)
			results, skip_events, env, query, doc, payload = on_read
			# [DOC] if $attrs query arg is present return only required keys.
			if '$attrs' in query:
				query['$attrs'].insert(0, '_id')
				for i in range(len(results['docs'])):
					results['docs'][i] = BaseModel(
						{
							attr: results['docs'][i][attr]
							for attr in query['$attrs']
							if attr in results['docs'][i]._attrs()
						}
					)

		return self.status(status=200, msg=f'Found {results["count"]} docs.', args=results)

	async def pre_watch(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> PRE_HANDLER_RETURN:
		return (skip_events, env, query, doc, payload)

	async def on_watch(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> ON_HANDLER_RETURN:
		return (results, skip_events, env, query, doc, payload)

	async def watch(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> AsyncGenerator[DictObj, DictObj]:
		if not self.collection:
			raise self.exception(
				status=400,
				msg='Utility module can\'t call \'watch\' method.',
				args={'code': 'INVALID_CALL'},
			)

		payload: Dict[str, Any] = {}

		query = cast(Query, query)

		if Event.PRE not in skip_events:
			pre_watch = await self.pre_watch(
				skip_events=skip_events, env=env, query=query, doc=doc, payload=payload
			)
			skip_events, env, query, doc, payload = pre_watch

		logger.debug('Preparing async loop at BaseModule')
		self.collection = cast(str, self.collection)
		async for results in Data.watch(
			env=env,
			collection_name=self.collection,
			attrs=self.attrs,
			query=query,
			skip_extn='$extn' in query or Event.EXTN in skip_events,
		):
			logger.debug(f'Received watch results at BaseModule: {results}')

			if 'stream' in results.keys():
				yield self.status(
					status=200, msg=f'Detected {results["count"]} docs.', args=results
				)
				continue

			if Event.ON not in skip_events:
				on_watch = await self.on_watch(
					results=results,
					skip_events=skip_events,
					env=env,
					query=query,
					doc=doc,
					payload=payload,
				)
				results, skip_events, env, query, doc, payload = on_watch

				# [DOC] if $attrs query arg is present return only required keys.
				if '$attrs' in query:
					query['$attrs'].insert(0, '_id')
					for i in range(len(results['docs'])):
						results['docs'][i] = BaseModel(
							{
								attr: results['docs'][i][attr]
								for attr in query['$attrs']
								if attr in results['docs'][i]._attrs()
							}
						)
			yield self.status(status=200, msg=f'Detected {results["count"]} docs.', args=results)

		logger.debug('Generator ended at BaseModule.')

	async def pre_create(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> PRE_HANDLER_RETURN:
		return (skip_events, env, query, doc, payload)

	async def on_create(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> ON_HANDLER_RETURN:
		return (results, skip_events, env, query, doc, payload)

	async def create(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		if not self.collection:
			raise self.exception(
				status=400,
				msg='Utility module can\'t call \'create\' method.',
				args={'code': 'INVALID_CALL'},
			)

		payload: Dict[str, Any] = {}

		query = cast(Query, query)

		# [DOC] Check for __create_draft
		if '__create_draft' in query:
			# [DOC] Check for conflicts
			if len(doc.keys()):
				raise self.exception(
					status=400,
					msg='Can\'t use \'__create_draft\' with attrs provided in \'doc\'',
					args={'code': 'INVALID_CREATE_DRAFT_DOC'},
				)

			# [DOC] Load __create_draft and use it as doc
			draft_results = await Data.read(
				env=env,
				collection_name=self.collection,
				attrs=self.attrs,
				query=Query([{'_id': query['__create_draft'][0], '__create_draft': True}]),
				skip_process=True,
			)

			if not draft_results['count']:
				raise self.exception(
					status=400,
					msg='Invalid \'__create_draft\' doc.',
					args={'code': 'INVALID_CREATE_DRAFT'},
				)

			# [DOC] Data.read returns doc as BaseModel, extract values using BaseModel._attrs()
			doc = draft_results['docs'][0]._attrs()
			# [DOC] Delete special attrs
			del doc['_id']

		if Event.PRE not in skip_events:
			pre_create = await self.pre_create(
				skip_events=skip_events, env=env, query=query, doc=doc, payload=payload
			)
			skip_events, env, query, doc, payload = pre_create

			# [DOC] Check if __results are passed in payload
			if '__results' in payload.keys():
				return payload['__results']

		# [DOC] Expant dot-notated keys onto dicts
		doc = expand_attr(doc=doc)
		# [DOC] Deleted all extra doc args
		doc = {
			attr: doc[attr]
			for attr in ['_id', '__create_draft', '__update_draft', *self.attrs.keys()]
			if attr in doc.keys() and doc[attr] != None
		}
		# [DOC] Append host_add, user_agent, create_time, diff if it's present in attrs.
		if (
			'user' in self.attrs.keys()
			and 'host_add' not in doc.keys()
			and env['session']
			and Event.ARGS not in skip_events
		):
			doc['user'] = env['session'].user._id
		if 'create_time' in self.attrs.keys():
			doc['create_time'] = datetime.datetime.utcnow().isoformat()
		if 'host_add' in self.attrs.keys() and 'host_add' not in doc.keys():
			doc['host_add'] = env['REMOTE_ADDR']
		if 'user_agent' in self.attrs.keys() and 'user_agent' not in doc.keys():
			doc['user_agent'] = env['HTTP_USER_AGENT']
		if Event.ARGS not in skip_events:
			mode: Literal['create', 'create_draft'] = 'create'
			if '__create_draft' in doc.keys() and doc['__create_draft'] == True:
				if not self.create_draft:
					raise self.exception(
						status=400,
						msg=f'Module \'{self.package_name.upper()}_{self.module_name.upper()}\' doesn\'t support \'create_draft\'',
						args={'code': 'NO_CREATE_DRAFT'},
					)
				if type(self.create_draft) == ATTR:
					self.create_draft = cast(ATTR, self.create_draft)
					# [DOC] Attr Type TYPE create_draft, call the funcion and catch InvalidAttrException
					try:
						await self.create_draft._args['func'](
							mode='create',
							attr_name='create_draft',
							attr_type=self.create_draft,
							attr_val=None,
							skip_events=skip_events,
							env=env,
							query=query,
							doc=doc,
							scope=doc,
						)
					except:
						raise self.exception(
							status=400,
							msg=f'Module \'{self.package_name.upper()}_{self.module_name.upper()}\' \'create_draft\' failed.',
							args={'code': 'NO_CREATE_DRAFT_CONDITION'},
						)

				mode = 'create_draft'

			elif '__update_draft' in doc.keys() and (
				type(doc['__update_draft']) == ObjectId
				or (
					type(doc['__update_draft']) == str
					and re.match(r'^[0-9a-fA-F]{24}$', doc['__update_draft'])
				)
			):
				doc['__update_draft'] = ObjectId(doc['__update_draft'])
				if not self.update_draft:
					raise self.exception(
						status=400,
						msg=f'Module \'{self.package_name.upper()}_{self.module_name.upper()}\' doesn\'t support \'update_draft\'',
						args={'code': 'NO_UPDATE_DRAFT'},
					)
				if type(self.update_draft) == ATTR:
					self.update_draft = cast(ATTR, self.update_draft)
					# [DOC] Attr Type TYPE update_draft, call the funcion and catch InvalidAttrException
					try:
						await self.update_draft._args['func'](
							mode='create',
							attr_name='update_draft',
							attr_type=self.update_draft,
							attr_val=None,
							skip_events=skip_events,
							env=env,
							query=query,
							doc=doc,
							scope=doc,
						)
					except:
						raise self.exception(
							status=400,
							msg=f'Module \'{self.package_name.upper()}_{self.module_name.upper()}\' \'update_draft\' failed.',
							args={'code': 'NO_UPDATE_DRAFT_CONDITION'},
						)

				mode = 'create_draft'
			# [DOC] Check presence and validate all attrs in doc args
			try:
				await validate_doc(
					mode=mode,
					doc=doc,
					attrs=self.attrs,
					skip_events=skip_events,
					env=env,
					query=query,
				)
			except MissingAttrException as e:
				raise self.exception(
					status=400,
					msg=f'{str(e)} for \'create\' request on module \'{self.package_name.upper()}_{self.module_name.upper()}\'.',
					args={'code': 'MISSING_ATTR'},
				)
			except InvalidAttrException as e:
				raise self.exception(
					status=400,
					msg=f'{str(e)} for \'create\' request on module \'{self.package_name.upper()}_{self.module_name.upper()}\'.',
					args={'code': 'INVALID_ATTR'},
				)
			except ConvertAttrException as e:
				raise self.exception(
					status=400,
					msg=f'{str(e)} for \'create\' request on module \'{self.package_name.upper()}_{self.module_name.upper()}\'.',
					args={'code': 'CONVERT_INVALID_ATTR'},
				)
			# [DOC] Check unique_attrs
			if self.unique_attrs:
				unique_attrs_query: List[Any] = [[]]
				for attr in self.unique_attrs:
					if type(attr) == str:
						attr = cast(str, attr)
						unique_attrs_query[0].append({attr: doc[attr]})
					elif type(attr) == tuple:
						unique_attrs_query[0].append({child_attr: doc[child_attr] for child_attr in attr})
					# [TODO] Implement use of single-item dict with LITERAL Attr Type for dynamic unique check based on doc value
				unique_attrs_query.append({'$limit': 1})
				unique_attrs_query = cast(NAWAH_QUERY, unique_attrs_query)
				unique_results = await self.read(
					skip_events=[Event.PERM], env=env, query=unique_attrs_query
				)
				if unique_results.args.count:
					unique_attrs_str = ', '.join(
						map(
							lambda _: ('(' + ', '.join(_) + ')') if type(_) == tuple else _,  # type: ignore
							self.unique_attrs,
						)
					)
					raise self.exception(
						status=400,
						msg=f'A doc with the same \'{unique_attrs_str}\' already exists.',
						args={'code': 'DUPLICATE_DOC'},
					)
		# [DOC] Execute Data driver create
		results = await Data.create(
			env=env, collection_name=self.collection, attrs=self.attrs, doc=doc
		)

		# [DOC] Check for __create_draft and delete it
		if '__create_draft' in query:
			delete_draft_results = await Data.delete(
				env=env,
				collection_name=self.collection,
				attrs=self.attrs,
				docs=[ObjectId(query['__create_draft'][0])],
				strategy=DELETE_STRATEGY.FORCE_SYS,
			)
			if delete_draft_results['count'] != 1:
				logger.error(
					f'Failed to delete \'__create_draft\'. Results: {delete_draft_results}'
				)

		if Event.ON not in skip_events:
			on_create = await self.on_create(
				results=results,
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				payload=payload,
			)
			results, skip_events, env, query, doc, payload = on_create

		# [DOC] create soft action is to only return the new created doc _id.
		if Event.SOFT in skip_events:
			read_results = await self.read(
				skip_events=[Event.PERM], env=env, query=[[{'_id': results['docs'][0]}]]
			)
			results = read_results.args

		# [DOC] Module collection is updated, update_cache
		asyncio.create_task(self.update_cache(env=env))

		return self.status(status=200, msg=f'Created {results["count"]} docs.', args=results)

	async def pre_update(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> PRE_HANDLER_RETURN:
		return (skip_events, env, query, doc, payload)

	async def on_update(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> ON_HANDLER_RETURN:
		return (results, skip_events, env, query, doc, payload)

	async def update(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		if not self.collection:
			raise self.exception(
				status=400,
				msg='Utility module can\'t call \'update\' method.',
				args={'code': 'INVALID_CALL'},
			)

		payload: Dict[str, Any] = {}

		query = cast(Query, query)

		update_draft = None
		# [DOC] Check for __update_draft
		if '__update_draft' in query:
			update_draft = query['__update_draft'][0]
			# [DOC] Check for conflicts
			if len(doc.keys()):
				raise self.exception(
					status=400,
					msg='Can\'t use \'__update_draft\' with attrs provided in \'doc\'',
					args={'code': 'INVALID_UPDATE_DRAFT_DOC'},
				)

			# [DOC] Load __create_draft and use it as doc
			draft_results = await Data.read(
				env=env,
				collection_name=self.collection,
				attrs=self.attrs,
				query=Query(
					[{'_id': query['__update_draft'][0], '__update_draft': {'$ne': False}}]
				),
				skip_process=True,
			)

			if not draft_results['count']:
				raise self.exception(
					status=400,
					msg='Invalid \'__update_draft\' doc.',
					args={'code': 'INVALID_UPDATE_DRAFT'},
				)

			# [DOC] Update query per the value of doc.__update_draft
			del query['__update_draft'][0]
			query.append({'_id': draft_results['docs'][0]['__update_draft']})
			# [DOC] Data.read returns doc as BaseModel, extract values using BaseModel._attrs()
			doc = draft_results['docs'][0]._attrs()
			# [DOC] Delete special attrs
			del doc['_id']

		if Event.PRE not in skip_events:
			pre_update = await self.pre_update(
				skip_events=skip_events, env=env, query=query, doc=doc, payload=payload
			)
			skip_events, env, query, doc, payload = pre_update

			# [DOC] Check if __results are passed in payload
			if '__results' in payload.keys():
				return payload['__results']

		# [DOC] Check presence and validate all attrs in doc args
		try:
			await validate_doc(
				mode='update',
				doc=doc,
				attrs=self.attrs,
				skip_events=skip_events,
				env=env,
				query=query,
			)
		except MissingAttrException as e:
			raise self.exception(
				status=400,
				msg=f'{str(e)} for \'update\' request on module \'{self.package_name.upper()}_{self.module_name.upper()}\'.',
				args={'code': 'MISSING_ATTR'},
			)
		except InvalidAttrException as e:
			raise self.exception(
				status=400,
				msg=f'{str(e)} for \'update\' request on module \'{self.package_name.upper()}_{self.module_name.upper()}\'.',
				args={'code': 'INVALID_ATTR'},
			)
		except ConvertAttrException as e:
			raise self.exception(
				status=400,
				msg=f'{str(e)} for \'update\' request on module \'{self.package_name.upper()}_{self.module_name.upper()}\'.',
				args={'code': 'CONVERT_INVALID_ATTR'},
			)
		# [DOC] Delete all attrs not belonging to the doc, checking against top level attrs only
		doc = {
			attr: doc[attr]
			for attr in ['_id', *doc.keys()]
			if attr.split('.')[0].split(':')[0] in self.attrs.keys()
			and (
				(type(doc[attr]) != dict and doc[attr] != None)
				or (
					type(doc[attr]) == dict
					and doc[attr].keys()
					and list(doc[attr].keys())[0][0] != '$'
				)
				or (
					type(doc[attr]) == dict
					and doc[attr].keys()
					and list(doc[attr].keys())[0][0] == '$'
					and doc[attr][list(doc[attr].keys())[0]] != None
				)
			)
		}
		# [DOC] Check if there is anything yet to update
		if not len(doc.keys()):
			return self.status(status=200, msg='Nothing to update.', args={})
		# [DOC] Find which docs are to be updated
		docs_results = await Data.read(
			env=env,
			collection_name=self.collection,
			attrs=self.attrs,
			query=query,
			skip_process=True,
		)
		# [DOC] Check unique_attrs
		if self.unique_attrs:
			# [DOC] If any of the unique_attrs is present in doc, and docs_results is > 1, we have duplication
			if len(docs_results['docs']) > 1:
				unique_attrs_check = True
				for attr in self.unique_attrs:
					if type(attr) == str and attr in doc.keys():
						unique_attrs_check = False
						break
					elif type(attr) == tuple:
						for child_attr in attr:
							if not unique_attrs_check:
								break
							if child_attr in doc.keys():
								unique_attrs_check = False
								break

				if not unique_attrs_check:
					raise self.exception(
						status=400,
						msg='Update call query has more than one doc as results. This would result in duplication.',
						args={'code': 'MULTI_DUPLICATE'},
					)

			# [DOC] Check if any of the unique_attrs are present in doc
			if sum(1 for attr in doc.keys() if attr in self.unique_attrs) > 0:
				# [DOC] Check if the doc would result in duplication after update
				unique_attrs_query: List[Any] = [[]]
				for attr in self.unique_attrs:
					if type(attr) == str:
						attr = cast(str, attr)
						if attr in doc.keys():
							unique_attrs_query[0].append({attr: doc[attr]})
					elif type(attr) == tuple:
						unique_attrs_query[0].append(
							{child_attr: doc[child_attr] for child_attr in attr if attr in doc.keys()}
						)
				unique_attrs_query.append(
					{'_id': {'$nin': [doc._id for doc in docs_results['docs']]}}
				)
				unique_attrs_query.append({'$limit': 1})
				unique_attrs_query = cast(NAWAH_QUERY, unique_attrs_query)
				unique_results = await self.read(
					skip_events=[Event.PERM], env=env, query=unique_attrs_query
				)
				if unique_results.args.count:
					unique_attrs_str = ', '.join(
						map(
							lambda _: ('(' + ', '.join(_) + ')') if type(_) == tuple else _,  # type: ignore
							self.unique_attrs,
						)
					)
					raise self.exception(
						status=400,
						msg=f'A doc with the same \'{unique_attrs_str}\' already exists.',
						args={'code': 'DUPLICATE_DOC'},
					)
		results = await Data.update(
			env=env,
			collection_name=self.collection,
			attrs=self.attrs,
			docs=[doc._id for doc in docs_results['docs']],
			doc=doc,
		)

		# [DOC] Check for update_draft and delete it
		if update_draft:
			delete_draft_results = await Data.delete(
				env=env,
				collection_name=self.collection,
				attrs=self.attrs,
				docs=[ObjectId(update_draft)],
				strategy=DELETE_STRATEGY.FORCE_SYS,
			)
			if delete_draft_results['count'] != 1:
				logger.error(
					f'Failed to delete \'__update_draft\'. Results: {delete_draft_results}'
				)

		if Event.ON not in skip_events:
			on_update = await self.on_update(
				results=results,
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				payload=payload,
			)
			results, skip_events, env, query, doc, payload = on_update

		# [DOC] If at least one doc updated, and module has diff enabled, and __DIFF__ not skipped:
		if results['count'] and self.diff and Event.DIFF not in skip_events:
			if type(self.diff) == ATTR:
				# [DOC] # [DOC] Attr Type TYPE diff, call the funcion and catch InvalidAttrException
				self.diff = cast(ATTR, self.diff)
				try:
					await self.diff._args['func'](
						mode='create',
						attr_name='diff',
						attr_type=self.diff,
						attr_val=None,
						skip_events=skip_events,
						env=env,
						query=query,
						doc=doc,
						scope=doc,
					)

					# [DOC] if function passes, create Diff doc with default callable
					diff_vars = doc
					diff_results = await Config.modules['diff'].create(
						skip_events=[Event.PERM],
						env=env,
						query=query,
						doc={'module': self.module_name, 'vars': diff_vars},
					)
					if diff_results.status != 200:
						logger.error(f'Failed to create Diff doc, results: {diff_results}')
				except:
					logger.debug(f'Skipped Diff Workflow due to failed condition.')
			else:
				diff_results = await Config.modules['diff'].create(
					skip_events=[Event.PERM],
					env=env,
					query=query,
					doc={'module': self.module_name, 'vars': doc},
				)
				if diff_results.status != 200:
					logger.error(f'Failed to create Diff doc, results: {diff_results}')
		else:
			logger.debug(
				f'Skipped Diff Workflow due to: {results["count"]}, {self.diff}, {Event.DIFF not in skip_events}'
			)

		# [DOC] Module collection is updated, update_cache
		asyncio.create_task(self.update_cache(env=env))

		return self.status(status=200, msg=f'Updated {results["count"]} docs.', args=results)

	async def pre_delete(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> PRE_HANDLER_RETURN:
		return (skip_events, env, query, doc, payload)

	async def on_delete(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> ON_HANDLER_RETURN:
		return (results, skip_events, env, query, doc, payload)

	async def delete(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		if not self.collection:
			raise self.exception(
				status=400,
				msg='Utility module can\'t call \'delete\' method.',
				args={'code': 'INVALID_CALL'},
			)

		payload: Dict[str, Any] = {}

		query = cast(Query, query)

		if Event.PRE not in skip_events:
			pre_delete = await self.pre_delete(
				skip_events=skip_events, env=env, query=query, doc=doc, payload=payload
			)
			skip_events, env, query, doc, payload = pre_delete

			# [DOC] Check if __results are passed in payload
			if '__results' in payload.keys():
				return payload['__results']

		# [TODO]: confirm all extns are not linked.
		# [DOC] Pick delete strategy based on skip_events
		strategy = DELETE_STRATEGY.SOFT_SKIP_SYS
		if Event.SOFT not in skip_events and Event.SYS_DOCS in skip_events:
			strategy = DELETE_STRATEGY.SOFT_SYS
		elif Event.SOFT in skip_events and Event.SYS_DOCS not in skip_events:
			strategy = DELETE_STRATEGY.FORCE_SKIP_SYS
		elif Event.SOFT in skip_events and Event.SYS_DOCS in skip_events:
			strategy = DELETE_STRATEGY.FORCE_SYS

		docs_results = results = await Data.read(
			env=env,
			collection_name=self.collection,
			attrs=self.attrs,
			query=query,
			skip_process=True,
		)
		results = await Data.delete(
			env=env,
			collection_name=self.collection,
			attrs=self.attrs,
			docs=[doc._id for doc in docs_results['docs']],
			strategy=strategy,
		)
		if Event.ON not in skip_events:
			on_delete = await self.on_delete(
				results=results,
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				payload=payload,
			)
			results, skip_events, env, query, doc, payload = on_delete

		# [DOC] Module collection is updated, update_cache
		asyncio.create_task(self.update_cache(env=env))

		return self.status(status=200, msg=f'Deleted {results["count"]} docs.', args=results)

	async def pre_create_file(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> PRE_HANDLER_RETURN:
		return (skip_events, env, query, doc, payload)

	async def on_create_file(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> ON_HANDLER_RETURN:
		return (results, skip_events, env, query, doc, payload)

	async def create_file(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		if not self.collection:
			raise self.exception(
				status=400,
				msg='Utility module can\'t call \'create_file\' method.',
				args={'code': 'INVALID_CALL'},
			)

		payload: Dict[str, Any] = {}

		query = cast(Query, query)

		if Event.PRE not in skip_events:
			pre_create_file = await self.pre_create_file(
				skip_events=skip_events, env=env, query=query, doc=doc, payload=payload
			)
			skip_events, env, query, doc, payload = pre_create_file

			# [DOC] Check if __results are passed in payload
			if '__results' in payload.keys():
				return payload['__results']

		# [TODO] Allow use dot-notated attr path in attr query attr
		if (
			query['attr'][0] not in self.attrs.keys()
			or type(self.attrs[query['attr'][0]]._type) != 'LIST'
			or not self.attrs[query['attr'][0]]._args['list'][0]._type != 'FILE'
		):
			raise self.exception(
				status=400, msg='Attr is invalid.', args={'code': 'INVALID_ATTR'}
			)

		update_results = await self.update(
			skip_events=[Event.PERM],
			env=env,
			query=[{'_id': query['_id'][0]}],
			doc={query['attr'][0]: {'$append': doc['file']}},
		)
		results = update_results['args']

		if Event.ON not in skip_events:
			on_create_file = await self.on_create_file(
				results=results,
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				payload=payload,
			)
			results, skip_events, env, query, doc, payload = on_create_file

		return self.status(status=200, msg=f'Updated {results["count"]} docs.', args=results)

	async def pre_delete_file(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> PRE_HANDLER_RETURN:
		return (skip_events, env, query, doc, payload)

	async def on_delete_file(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> ON_HANDLER_RETURN:
		return (results, skip_events, env, query, doc, payload)

	async def delete_file(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		if not self.collection:
			raise self.exception(
				status=400,
				msg='Utility module can\'t call \'delete_file\' method.',
				args={'code': 'INVALID_CALL'},
			)

		payload: Dict[str, Any] = {}

		query = cast(Query, query)

		if Event.PRE not in skip_events:
			pre_delete_file = await self.pre_delete_file(
				skip_events=skip_events, env=env, query=query, doc=doc, payload=payload
			)
			skip_events, env, query, doc, payload = pre_delete_file

			# [DOC] Check if __results are passed in payload
			if '__results' in payload.keys():
				return payload['__results']

		# [TODO] Allow use dot-notated attr path in attr query attr
		if (
			query['attr'][0] not in self.attrs.keys()
			or type(self.attrs[query['attr'][0]]._type) != 'LIST'
			or not self.attrs[query['attr'][0]]._args['list'][0]._type != 'FILE'
		):
			raise self.exception(
				status=400, msg='Attr is invalid.', args={'code': 'INVALID_ATTR'}
			)

		read_results = await self.read(
			skip_events=[Event.PERM], env=env, query=[{'_id': query['_id'][0]}]
		)
		if not read_results.args.count:
			raise self.exception(status=400, msg='Doc is invalid.', args={'code': 'INVALID_DOC'})
		doc = read_results.args.docs[0]

		if query['attr'][0] not in doc or not doc[query['attr'][0]]:
			raise self.exception(
				status=400,
				msg='Doc attr is invalid.',
				args={'code': 'INVALID_DOC_ATTR'},
			)

		if query['index'][0] not in range(len(doc[query['attr'][0]])):
			raise self.exception(
				status=400, msg='Index is invalid.', args={'code': 'INVALID_INDEX'}
			)

		if (
			type(doc[query['attr'][0]][query['index'][0]]) != dict
			or 'name' not in doc[query['attr'][0]][query['index'][0]].keys()
		):
			raise self.exception(
				status=400,
				msg='Index value is invalid.',
				args={'code': 'INVALID_INDEX_VALUE'},
			)

		if doc[query['attr'][0]][query['index'][0]]['name'] != query['name'][0]:  # type: ignore
			raise self.exception(
				status=400,
				msg='File name in query doesn\'t match value.',
				args={'code': 'FILE_NAME_MISMATCH'},
			)

		update_results = await self.update(
			skip_events=[Event.PERM],
			env=env,
			query=[{'_id': query['_id'][0]}],
			doc={query['attr'][0]: {'$del_val': [doc[query['attr'][0]][query['index'][0]]]}},
		)
		results = update_results['args']

		if Event.ON not in skip_events:
			on_delete_file = await self.on_delete_file(
				results=results,
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				payload=payload,
			)
			results, skip_events, env, query, doc, payload = on_delete_file

		return results

	async def pre_retrieve_file(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> PRE_HANDLER_RETURN:
		return (skip_events, env, query, doc, payload)

	async def on_retrieve_file(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Query,
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> ON_HANDLER_RETURN:
		return (results, skip_events, env, query, doc, payload)

	async def retrieve_file(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		if not self.collection:
			raise self.exception(
				status=400,
				msg='Utility module can\'t call \'retrieve_file\' method.',
				args={'code': 'INVALID_CALL'},
			)

		payload: Dict[str, Any] = {}

		query = cast(Query, query)

		if Event.PRE not in skip_events:
			pre_retrieve_file = await self.pre_retrieve_file(
				skip_events=skip_events, env=env, query=query, doc=doc, payload=payload
			)
			skip_events, env, query, doc, payload = pre_retrieve_file

			# [DOC] Check if __results are passed in payload
			if '__results' in payload.keys():
				return payload['__results']

		attr_name = query['attr'][0]
		filename = query['filename'][0]
		if 'thumb' in query:
			thumb_dims: Optional[List[int]] = [int(dim) for dim in query['thumb'][0].split('x')]
		else:
			thumb_dims = None

		read_results = await self.read(
			skip_events=[Event.PERM] + skip_events,
			env=env,
			query=[{'_id': query['_id'][0]}],
		)
		if not read_results.args.count:
			raise self.exception(
				status=400,
				msg='File not found.',
				args={'code': 'NOT_FOUND', 'return': 'json'},
			)
		attr: Union[List[Dict[str, Any]], Dict[str, Any]]
		doc = read_results.args.docs[0]
		try:
			attr_path = attr_name.split('.')
			attr = doc
			for path in attr_path:
				attr = doc[path]
		except:
			raise self.exception(
				status=404,
				msg='File not found.',
				args={'code': 'NOT_FOUND', 'return': 'json'},
			)

		retrieved_file = None

		if type(attr) == list:
			attr = cast(List[Dict[str, Any]], attr)
			for item in attr:
				if item['name'] == filename:
					retrieved_file = item
					break
		elif type(attr) == dict:
			attr = cast(Dict[str, Any], attr)
			if attr['name'] == filename:
				retrieved_file = attr

		if not retrieved_file:
			# [DOC] No filename match
			raise self.exception(
				status=404,
				msg='File not found.',
				args={'code': 'NOT_FOUND', 'return': 'json'},
			)

		# [DOC] filematch!
		results: Dict[str, Any]
		results = {
			'docs': [
				DictObj(
					{
						'_id': query['_id'][0],
						'name': retrieved_file['name'],
						'type': retrieved_file['type'],
						'lastModified': retrieved_file['lastModified'],
						'size': retrieved_file['size'],
						'content': retrieved_file['content'],
					}
				)
			]
		}

		if thumb_dims:
			if retrieved_file['type'].split('/')[0] != 'image':
				raise self.exception(
					status=400,
					msg='File is not of type image to create thumbnail for.',
					args={'code': 'NOT_IMAGE', 'return': 'json'},
				)
			try:
				image = Image.open(io.BytesIO(retrieved_file['content']))
				image.thumbnail(thumb_dims)
				stream = io.BytesIO()
				image.save(stream, format=image.format)
				stream.seek(0)
				results['docs'][0]['content'] = stream.read()
			except:
				pass

		if Event.ON not in skip_events:
			on_retrieve_file = await self.on_retrieve_file(
				results=results,
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				payload=payload,
			)
			results, skip_events, env, query, doc, payload = on_retrieve_file

		results['return'] = 'file'
		return self.status(status=200, msg='File attached to response.', args=results)

	async def update_cache(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		if self.collection and self.cache:
			for cache_set in self.cache:
				for cache_key in cache_set.queries.keys():
					del cache_set.queries[cache_key]
					cache_query: NAWAH_QUERY = eval(cache_key.split('____')[0])
					cache_special: NAWAH_QUERY = eval(cache_key.split('____')[1])
					cache_query.append(cache_special)
					results = await Data.read(
						env=env,
						collection_name=self.collection,
						attrs=self.attrs,
						query=Query(cache_query),
					)
					cache_set.queries[cache_key] = CACHED_QUERY(results=results)
		return self.status(status=200, msg='Cache deleted.', args={})
