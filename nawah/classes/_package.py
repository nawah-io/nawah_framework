from bson import ObjectId
from dataclasses import dataclass
from typing import (
	Optional,
	Dict,
	Any,
	TypedDict,
	Literal,
	List,
	Callable,
	Union,
	Optional,
	cast,
	Protocol,
	TYPE_CHECKING,
)

from croniter import croniter

from ._types import NAWAH_DOC

if TYPE_CHECKING:
	from ._attr import ATTR
	from ._types import NAWAH_ENV


CLIENT_APP = TypedDict(
	'CLIENT_APP',
	{
		'name': str,
		'type': Literal['web', 'ios', 'android'],
		'origin': List[str],
		'hash': str,
	},
)


class USER_SETTING:
	type: Literal['user', 'user_sys']
	val_type: 'ATTR'
	default: Optional[Any]

	def __init__(
		self,
		*,
		type: Literal['user', 'user_sys'],
		val_type: 'ATTR',
		default: Optional[Any] = None,
	):
		self.type = type
		self.val_type = val_type
		self.default = default

	def _validate(self):
		from ._attr import ATTR

		# [DOC] Validate type
		if type(self.type) != str or self.type not in ['user', 'user_sys']:
			raise Exception(
				f'Invalid \'type\' of type \'{type(self.type)}\' with required \'user\', or \'user_sys\'.'
			)

		# [DOC] Validate val_type
		if type(self.val_type) != ATTR:
			raise Exception(
				f'Invalid \'val_type\' of type \'{type(self.val_type)}\' with required type \'ATTR\'.'
			)

		# [DOC] Validate val_type Attr Type
		ATTR.validate_type(attr_type=self.val_type)


ANALYTICS_EVENTS = TypedDict(
	'ANALYTICS_EVENTS',
	{
		'app_conn_verified': bool,
		'session_conn_auth': bool,
		'session_user_auth': bool,
		'session_conn_reauth': bool,
		'session_user_reauth': bool,
		'session_conn_deauth': bool,
		'session_user_deauth': bool,
	},
)


class SYS_DOC:
	module: str
	key: Optional[str]
	skip_args: bool
	doc: Optional[NAWAH_DOC]

	@property
	def key_value(self) -> Any:
		if not (self.doc):
			raise Exception(f'SYS_DOC instance was initialised with no \'doc\'.')
		self.key = cast(str, self.key)
		return self.doc[self.key]

	def __init__(
		self,
		*,
		module: str,
		key: str = None,
		skip_args: bool = False,
		doc: NAWAH_DOC = None,
	):
		if doc != None:
			if type(doc) != dict:
				raise Exception(
					f'Argument \'doc\' is not a valid \'NAWAH_DOC\'. Expecting type \'dict\' but got \'{type(dict)}\'.'
				)
			doc = cast(NAWAH_DOC, doc)
			if not key:
				key = '_id'
			if key not in doc.keys():
				raise Exception(f'Attr \'{key}\' is not present on \'doc\'.')
			if key == '_id' and type(doc["_id"]) != ObjectId:
				raise Exception(
					f'Invalid attr \'_id\' of type \'{type(doc["_id"])}\' with required type \'ID\''
				)
		else:
			if key or skip_args:
				raise Exception('Arguments \'attr, skip_args\' should only be used with \'doc\'.')

		self.module = module
		self.key = key
		self.skip_args = skip_args
		self.doc = doc


class JOB_CALLABLE(Protocol):
	def __call__(
		self,
		env: 'NAWAH_ENV',
	) -> bool:
		...


class JOB:
	job: JOB_CALLABLE
	schedule: str
	prevent_disable: bool
	_cron_schedule: croniter
	_next_time: Optional[str] = None
	_disabled: bool = False

	def __init__(
		self,
		*,
		job: JOB_CALLABLE,
		schedule: str,
		prevent_disable: bool = False,
	):
		self.job = job
		self.schedule = schedule
		self.prevent_disable = prevent_disable


class L10N(dict):
	pass


@dataclass
class PACKAGE_CONFIG:
	api_level: Optional[str] = None
	version: Optional[str] = None
	emulate_test: Optional[bool] = None
	debug: Optional[bool] = None
	port: Optional[int] = None
	env: Optional[str] = None
	force_admin_check: Optional[bool] = None
	vars_types: Optional[Dict[str, 'ATTR']] = None
	vars: Optional[Dict[str, Any]] = None
	client_apps: Optional[Dict[str, CLIENT_APP]] = None
	analytics_events: Optional[ANALYTICS_EVENTS] = None
	conn_timeout: Optional[int] = None
	quota_anon_min: Optional[int] = None
	quota_auth_min: Optional[int] = None
	quota_ip_min: Optional[int] = None
	data_server: Optional[str] = None
	data_name: Optional[str] = None
	data_ssl: Optional[bool] = None
	data_ca_name: Optional[str] = None
	data_ca: Optional[str] = None
	data_disk_use: Optional[bool] = None
	data_azure_mongo: Optional[bool] = None
	locales: Optional[List[str]] = None
	locale: Optional[str] = None
	admin_doc: Optional[NAWAH_DOC] = None
	admin_password: Optional[str] = None
	anon_token: Optional[str] = None
	anon_privileges: Optional[Dict[str, List[str]]] = None
	user_attrs: Optional[Dict[str, 'ATTR']] = None
	user_settings: Optional[Dict[str, USER_SETTING]] = None
	user_doc_settings: Optional[List[str]] = None
	groups: Optional[List[Dict[str, Any]]] = None
	default_privileges: Optional[Dict[str, List[str]]] = None
	data_indexes: Optional[List[Dict[str, Any]]] = None
	docs: Optional[List[SYS_DOC]] = None
	jobs: Optional[Dict[str, JOB]] = None
	gateways: Optional[Dict[str, Callable]] = None
	types: Optional[Dict[str, Callable]] = None


@dataclass
class APP_CONFIG(PACKAGE_CONFIG):
	name: Optional[str] = None
	version: Optional[str] = None
	default_package: Optional[str] = None
	debug: Optional[bool] = False
	port: Optional[int] = None
	env: Optional[str] = None
	envs: Optional[Dict[str, PACKAGE_CONFIG]] = None
	force_admin_check: Optional[bool] = None
