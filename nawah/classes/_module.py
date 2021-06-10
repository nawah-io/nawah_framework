from nawah.enums import Event

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
			Exception(f'Can\'t validate permission obj {obj} of type {type(obj)}.')

		logger.debug(f'Found \'{obj}\' to validate. Iterating.')

		for j in obj_iter:
			logger.debug(f'Attempting to validate \'{j}\'')
			if type(obj[j]) in [list, dict]:
				logger.debug(f'Item is an iterable object. Iterating.')
				self.__validate_obj(obj[j])
			elif type(obj[j]) == ATTR:
				if obj[j]._type != 'TYPE':
					Exception(f'Attr Type \'{j}\' of TYPE \'{obj[j]._type}\' is not allowed.')

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
