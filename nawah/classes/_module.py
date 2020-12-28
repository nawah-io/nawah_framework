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

import datetime

if TYPE_CHECKING:
	from __future__ import annotations
	from nawah.base_method import BaseMethod
	from ._attr import ATTR
	from ._dictobj import DictObj
	from ._types import NAWAH_EVENTS, NAWAH_ENV, NAWAH_DOC, NAWAH_QUERY
	from ._query import Query


PRE_HANDLER_RETURN = Tuple[NAWAH_EVENTS, NAWAH_ENV, Query, NAWAH_DOC, Dict[str, Any]]
ON_HANDLER_RETURN = Tuple[
	Dict[str, Any], NAWAH_EVENTS, NAWAH_ENV, Query, NAWAH_DOC, Dict[str, Any]
]


class NAWAH_MODULE:
	collection: Optional[str]
	proxy: str
	attrs: Dict[str, ATTR]
	diff: Union[bool, 'ATTR_MOD']
	defaults: Dict[str, Any]
	unique_attrs: List[str]
	extns: Dict[str, 'EXTN']
	privileges: List[str]
	methods: Dict[str, 'METHOD']
	cache: List['CACHE']
	analytics: List['ANALYTIC']
	package_name: str
	module_name: str

	async def pre_read(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[PRE_HANDLER_RETURN, DictObj]:
		pass

	async def on_read(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[ON_HANDLER_RETURN, DictObj]:
		pass

	async def read(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		pass

	async def pre_watch(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[PRE_HANDLER_RETURN, DictObj]:
		pass

	async def on_watch(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[ON_HANDLER_RETURN, DictObj]:
		pass

	async def watch(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
		payload: Optional[Dict[str, Any]] = None,
	) -> AsyncGenerator[DictObj, DictObj]:
		pass

	async def pre_create(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[PRE_HANDLER_RETURN, DictObj]:
		pass

	async def on_create(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[ON_HANDLER_RETURN, DictObj]:
		pass

	async def create(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		pass

	async def pre_update(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[PRE_HANDLER_RETURN, DictObj]:
		pass

	async def on_update(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[ON_HANDLER_RETURN, DictObj]:
		pass

	async def update(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		pass

	async def pre_delete(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[PRE_HANDLER_RETURN, DictObj]:
		pass

	async def on_delete(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[ON_HANDLER_RETURN, DictObj]:
		pass

	async def delete(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		pass

	async def pre_create_file(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[PRE_HANDLER_RETURN, DictObj]:
		pass

	async def on_create_file(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[ON_HANDLER_RETURN, DictObj]:
		pass

	async def create_file(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		pass

	async def pre_delete_file(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[PRE_HANDLER_RETURN, DictObj]:
		pass

	async def on_delete_file(
		self,
		results: Dict[str, Any],
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[NAWAH_QUERY, Query],
		doc: NAWAH_DOC,
		payload: Dict[str, Any],
	) -> Union[ON_HANDLER_RETURN, DictObj]:
		pass

	async def delete_file(
		self,
		skip_events: NAWAH_EVENTS = [],
		env: NAWAH_ENV = {},
		query: Union[NAWAH_QUERY, Query] = [],
		doc: NAWAH_DOC = {},
	) -> DictObj:
		pass


class ATTR_MOD_CONDITION(Protocol):
	def __call__(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[Query, NAWAH_QUERY],
		doc: NAWAH_DOC,
		scope: Optional[NAWAH_DOC],
	) -> bool:
		...


class ATTR_MOD_DEFAULT(Protocol):
	def __call__(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[Query, NAWAH_QUERY],
		doc: NAWAH_DOC,
		scope: Optional[NAWAH_DOC],
	) -> Any:
		...


class ATTR_MOD:
	condition: ATTR_MOD_CONDITION
	default: Union[ATTR_MOD_DEFAULT, Any]

	def __repr__(self):
		return f'<ATTR_MOD:{self.condition},{self.default}>'

	def __init__(
		self,
		*,
		condition: ATTR_MOD_CONDITION,
		default: Union[ATTR_MOD_DEFAULT, Any],
	):
		setattr(self, 'condition', condition)
		self.default = default


class PERM:
	privilege: str
	query_mod: Dict[str, Optional[Union[ATTR, ATTR_MOD, Literal['$__date', '$__user']]]]
	doc_mod: Dict[str, Optional[Union[ATTR, ATTR_MOD, Literal['$__date', '$__user']]]]

	def __repr__(self):
		return f'<PERM:{self.privilege},{self.query_mod},{self.doc_mod}>'

	def __init__(
		self,
		*,
		privilege: str,
		query_mod: Optional[
			Dict[str, Optional[Union[ATTR, ATTR_MOD, Literal['$__date', '$__user']]]]
		] = None,
		doc_mod: Optional[
			Dict[str, Optional[Union[ATTR, ATTR_MOD, Literal['$__date', '$__user']]]]
		] = None,
	):
		if not query_mod:
			query_mod = {}
		if not doc_mod:
			doc_mod = {}
		self.privilege = privilege
		self.query_mod = query_mod
		self.doc_mod = doc_mod


class EXTN:
	module: str
	skip_events: Optional[List[Event]]
	query: Optional[NAWAH_QUERY]
	attrs: List[str]
	force: bool = False

	def __repr__(self):
		return f'<EXTN:{self.module},{self.attrs},{self.force}>'

	def __init__(
		self,
		*,
		module: str,
		skip_events: List[Event] = None,
		query: NAWAH_QUERY = None,
		attrs: List[str],
		force: bool = False,
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
		List[Dict[str, ATTR]],
		Dict[str, ATTR],
	]
	doc_args: Union[
		None,
		List[Dict[str, ATTR]],
		Dict[str, ATTR],
	] = None
	get_method: bool
	post_method: bool
	watch_method: bool
	_callable: BaseMethod

	def __init__(
		self,
		*,
		permissions: List[PERM],
		query_args: Union[
			None,
			List[Dict[str, ATTR]],
			Dict[str, ATTR],
		] = None,
		doc_args: Union[
			None,
			List[Dict[str, ATTR]],
			Dict[str, ATTR],
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
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[Query, NAWAH_QUERY],
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
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[Query, NAWAH_QUERY],
		doc: NAWAH_DOC,
		method: str,
	) -> bool:
		...


class ANALYTIC_DOC(Protocol):
	def __call__(
		self,
		skip_events: NAWAH_EVENTS,
		env: NAWAH_ENV,
		query: Union[Query, NAWAH_QUERY],
		doc: NAWAH_DOC,
		method: str,
	) -> NAWAH_DOC:
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
