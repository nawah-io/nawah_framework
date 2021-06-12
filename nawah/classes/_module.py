from nawah.enums import Event, NAWAH_VALUES

from typing import (
	Tuple,
	Dict,
	Any,
	Optional,
	Union,
	List,
	TYPE_CHECKING,
	AsyncGenerator,
	Callable,
	Literal,
	Protocol,
	TypedDict,
	cast,
)

import datetime, logging

from ._exceptions import MethodException

if TYPE_CHECKING:
	from nawah.base_module import BaseModule
	from nawah.base_method import BaseMethod
	from ._attr import ATTR
	from ._dictobj import DictObj
	from ._types import NAWAH_EVENTS, NAWAH_ENV, NAWAH_DOC, NAWAH_QUERY
	from ._query import Query


logger = logging.getLogger('nawah')

PRE_HANDLER_RETURN = Tuple[
	'NAWAH_EVENTS', 'NAWAH_ENV', 'Query', 'NAWAH_DOC', Dict[str, Any]
]
ON_HANDLER_RETURN = Tuple[
	Dict[str, Any], 'NAWAH_EVENTS', 'NAWAH_ENV', 'Query', 'NAWAH_DOC', Dict[str, Any]
]

PERM_QUERY_MOD_UNIT = Dict[str, Union['ATTR', Literal['$__date', '$__user'], Any]]
PERM_QUERY_MOD = Union[PERM_QUERY_MOD_UNIT, 'NAWAH_QUERY', List['PERM_QUERY_MOD']]  # type: ignore

PERM_DOC_MOD_UNIT = Dict[str, Union['ATTR', Literal['$__date', '$__user'], Any]]
PERM_DOC_MOD = Union[PERM_DOC_MOD_UNIT, 'NAWAH_DOC']


class PERM:
	privilege: str
	query_mod: PERM_QUERY_MOD
	doc_mod: PERM_DOC_MOD

	_method: 'METHOD'
	_set_index: int

	def __repr__(self):
		return f'<PERM:{self.privilege},{self.query_mod},{self.doc_mod}>'

	def __init__(
		self,
		*,
		privilege: str,
		query_mod: Optional[PERM_QUERY_MOD] = None,
		doc_mod: Optional[PERM_DOC_MOD] = None,
	):
		if not query_mod:
			query_mod = {}
		if not doc_mod:
			doc_mod = {}
		self.privilege = privilege
		self.query_mod = query_mod
		self.doc_mod = doc_mod

	def _validate(self):
		# [DOC] Validate privilege is listed in BaseModule.privileges to detect typos, missing privileges, but skip *, __sys
		if self.privilege not in ['*', '__sys']:
			# [DOC] Check for cross-module privilege
			if '.' in self.privilege:
				from nawah.config import Config

				# [DOC] Validate correct format of cross-platform privilege: module_name.privilege
				try:
					module_name, privilege = self.privilege.split('.')
				except ValueError:
					raise Exception(
						f'Permission Set \'{self._set_index}\' of method \'{self._method._method_name}\' of module \'{self._method._module.module_name}\' requires invalid privilege \'{self.privilege}\'.'
					)

				module = Config.modules[module_name]
			else:
				module_name = self._method._module.module_name
				module = self._method._module
				privilege = self.privilege

			if privilege not in module.privileges:
				raise Exception(
					f'Permission Set \'{self._set_index}\' of method \'{self._method._method_name}\' of module \'{self._method._module.module_name}\' requires unknown privilege \'{module_name}.{privilege}\'.'
				)

		# [DOC] Add default Doc Modifiers to prevent sys attrs from being modified
		if self._method._method_name == 'update':
			for attr in ['user', 'create_time']:
				if attr not in self.doc_mod.keys():
					self.doc_mod[attr] = None
				# [TODO] Assert this is behaving correctly
				elif self.doc_mod[attr] == NAWAH_VALUES.ALLOW_MOD:
					del self.doc_mod[attr]

		# [DOC] Validate query_mod, doc_mod
		self._validate_query_mod()
		self._validate_doc_mod()

	def _validate_query_mod(self):
		if self.query_mod:
			logger.debug(
				f'Attemting to validate \'{self._method._module.module_name}.{self._method._method_name}[{self._set_index}].query_mod\'.'
			)
			self.__validate_obj(self.query_mod)

	def _validate_doc_mod(self):
		if self.doc_mod:
			logger.debug(
				f'Attemting to validate \'{self._method._module.module_name}.{self._method._method_name}[{self._set_index}].doc_mod\'.'
			)
			self.__validate_obj(self.doc_mod)

	def __validate_obj(self, obj):
		from ._attr import ATTR

		obj_iter: Iterable
		if type(obj) == list:
			obj_iter = range(len(obj))
		elif type(obj) == dict:
			obj_iter = list(obj.keys())
		else:
			raise Exception(f'Can\'t validate permission obj {obj} of type {type(obj)}.')

		logger.debug(f'Found \'{obj}\' to validate. Iterating.')

		for j in obj_iter:
			logger.debug(f'Attempting to validate \'{j}\'')
			if type(obj[j]) in [list, dict]:
				logger.debug(f'Item is an iterable object. Iterating.')
				self.__validate_obj(obj[j])
			elif type(obj[j]) == ATTR:
				if obj[j]._type != 'TYPE':
					raise Exception(f'Attr Type \'{j}\' of TYPE \'{obj[j]._type}\' is not allowed.')

				ATTR.validate_type(attr_type=obj[j])


class EXTN:
	module: str
	skip_events: Optional[List[Event]]
	query: Optional['NAWAH_QUERY']
	attrs: Union[List[str], str]
	force: Union[bool, str] = False

	def __repr__(self):
		return f'<EXTN:{self.module},{self.attrs},{self.force}>'

	def __init__(
		self,
		*,
		module: str,
		skip_events: List[Event] = None,
		query: 'NAWAH_QUERY' = None,
		attrs: Union[List[str], str],
		force: Union[bool, str] = False,
	):
		self.module = module
		self.skip_events = skip_events
		self.query = query
		self.attrs = attrs
		self.force = force

		# [DOC] Wrap query in list if it is a dict
		if type(query) == dict:
			self.query = [self.query]


class METHOD:
	permissions: List[PERM]
	query_args: Union[
		None,
		List[Dict[str, 'ATTR']],
		Dict[str, 'ATTR'],
	]
	doc_args: Union[
		None,
		List[Dict[str, 'ATTR']],
		Dict[str, 'ATTR'],
	] = None
	get_method: bool
	post_method: bool
	watch_method: bool

	_callable: 'BaseMethod'
	_module: 'BaseModule'
	_method_name: str

	def __init__(
		self,
		*,
		permissions: List[PERM],
		query_args: Union[
			None,
			List[Dict[str, 'ATTR']],
			Dict[str, 'ATTR'],
		] = None,
		doc_args: Union[
			None,
			List[Dict[str, 'ATTR']],
			Dict[str, 'ATTR'],
		] = None,
		get_method: bool = False,
		post_method: bool = False,
		watch_method: bool = False,
	):
		self.permissions = permissions
		self.query_args = query_args
		self.doc_args = doc_args
		self.get_method = get_method
		self.post_method = post_method
		self.watch_method = watch_method

	def __call__(self, **kwargs):
		return self._callable(**kwargs)

	def _validate(self):
		from nawah.base_method import BaseMethod
		from ._attr import ATTR

		# [DOC] Check for existence of at least single permissions set per method
		if not len(self.permissions):
			raise Exception(
				f'No permissions sets for method \'{self._method_name}\' of module \'{self._module.module_name}\'.'
			)
		# [DOC] Check method query_args attr, set it or update it if required.
		if not self.query_args:
			if self._method_name == 'create_file':
				self.query_args = [{'_id': ATTR.ID(), 'attr': ATTR.STR()}]
			elif self._method_name == 'delete_file':
				self.query_args = [
					{
						'_id': ATTR.ID(),
						'attr': ATTR.STR(),
						'index': ATTR.INT(),
						'name': ATTR.STR(),
					}
				]
		elif type(self.query_args) == dict:
			method_query_args = self.query_args
			method_query_args = cast(Dict[str, ATTR], method_query_args)
			self.query_args = [method_query_args]
		# [DOC] Check method doc_args attr, set it or update it if required.
		if not self.doc_args:
			if self._method_name == 'create_file':
				self.doc_args = [{'file': ATTR.FILE()}]
		elif type(self.doc_args) == dict:
			method_doc_args = self.doc_args
			method_doc_args = cast(Dict[str, ATTR], method_doc_args)
			self.doc_args = [method_doc_args]
		# [DOC] Check method get_method attr, update it if required.
		if self.get_method == True:
			if not self.query_args:
				if self._method_name == 'retrieve_file':
					self.query_args = [
						{
							'_id': ATTR.ID(),
							'attr': ATTR.STR(),
							'filename': ATTR.STR(),
						},
						{
							'_id': ATTR.ID(),
							'attr': ATTR.STR(),
							'thumb': ATTR.STR(pattern=r'[0-9]+x[0-9]+'),
							'filename': ATTR.STR(),
						},
					]
				else:
					self.query_args = [{}]
		# [DOC] Check method post_method attr, update it if required.
		if self.post_method == True:
			if not self.query_args:
				self.query_args = [{}]
		# [DOC] Check permissions sets for any invalid set
		for i in range(len(self.permissions)):
			permissions_set = self.permissions[i]
			if type(permissions_set) != PERM:
				raise Exception(
					f'Invalid permissions set \'{permissions_set}\' of method \'{self._method_name}\' of module \'{self._module.module_name}\'.'
				)
			# [DOC] Set PERM._method value to create back-link from child to parent
			permissions_set._method = self
			permissions_set._set_index = i
			permissions_set = cast(PERM, permissions_set)
			# [DOC] Check valida Permission Set
			permissions_set._validate()

		# [DOC] Check invalid query_args, doc_args types
		for arg_set in ['query_args', 'doc_args']:
			arg_set = cast(Literal['query_args', 'doc_args'], arg_set)
			if getattr(self, arg_set):
				method_arg_set: List[Dict[str, ATTR]] = getattr(self, arg_set)
				for args_set in method_arg_set:
					for attr in args_set.keys():
						try:
							ATTR.validate_type(attr_type=args_set[attr])
						except:
							raise Exception(
								f'Invalid \'{arg_set}\' attr type for \'{attr}\' of set \'{args_set}\' of method \'{self._method_name}\' of module \'{self._module.module_name}\'.'
							)
		# [DOC] Initialise method as BaseMethod
		method_query_args = self.query_args  # type: ignore
		method_query_args = cast(List[Dict[str, ATTR]], method_query_args)
		method_doc_args = self.doc_args  # type: ignore
		method_doc_args = cast(List[Dict[str, ATTR]], method_doc_args)

		# [DOC] Validate method implementation exist in the class
		try:
			getattr(self._module, f'_method_{self._method_name}')
		except AttributeError:
			raise Exception(
				f'Method \'{self._method_name}\' of module \'{self._module.module_name}\' is defined but not implemented.'
			)

		self._callable = BaseMethod(
			module=self._module,
			method=self._method_name,
			permissions=self.permissions,
			query_args=method_query_args,
			doc_args=method_doc_args,
			watch_method=self.watch_method,
			get_method=self.get_method,
			post_method=self.post_method,
		)


class CACHE_CONDITION(Protocol):
	def __call__(
		self,
		skip_events: 'NAWAH_EVENTS',
		env: 'NAWAH_ENV',
		query: Union['Query', 'NAWAH_QUERY'],
	) -> bool:
		...


class CACHE:
	condition: CACHE_CONDITION
	period: Optional[int]
	queries: Dict[str, 'CACHED_QUERY']

	def __repr__(self):
		return f'<CACHE:{self.condition},{self.period}>'

	def __init__(
		self,
		*,
		condition: CACHE_CONDITION,
		period: int = None,
	):
		setattr(self, 'condition', condition)
		self.period = period
		self.queries = {}

	def cache_query(self, *, query_key: str, results: Dict[str, Any]):
		self.queries[query_key] = CACHED_QUERY(results=results)


class CACHED_QUERY:
	results: Dict[str, Any]
	query_time: datetime.datetime

	def __init__(self, *, results: Dict[str, Any], query_time: datetime.datetime = None):
		self.results = results
		if not query_time:
			query_time = datetime.datetime.utcnow()
		self.query_time = query_time


class ANALYTIC_CONDITION(Protocol):
	def __call__(
		self,
		skip_events: 'NAWAH_EVENTS',
		env: 'NAWAH_ENV',
		query: Union['Query', 'NAWAH_QUERY'],
		doc: 'NAWAH_DOC',
		method: str,
	) -> bool:
		...


class ANALYTIC_DOC(Protocol):
	def __call__(
		self,
		skip_events: 'NAWAH_EVENTS',
		env: 'NAWAH_ENV',
		query: Union['Query', 'NAWAH_QUERY'],
		doc: 'NAWAH_DOC',
		method: str,
	) -> 'NAWAH_DOC':
		...


class ANALYTIC:
	condition: ANALYTIC_CONDITION
	doc: ANALYTIC_DOC

	def __init__(
		self,
		*,
		condition: ANALYTIC_CONDITION,
		doc: ANALYTIC_DOC,
	):
		setattr(self, 'condition', condition)
		setattr(self, 'doc', doc)
