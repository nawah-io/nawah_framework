from dataclasses import dataclass
from typing import Optional, Dict, Any, TypedDict, Literal, List, Callable, Union

from ._attr import ATTR
from ._types import NAWAH_DOC

CLIENT_APP = TypedDict(
	'CLIENT_APP',
	{
		'name': str,
		'type': Literal['web', 'ios', 'android'],
		'origin': List[str],
		'hash': str,
	},
)

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
	vars_types: Optional[Dict[str, ATTR]] = None
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
	email_auth: Optional[Dict[str, str]] = None
	locales: Optional[List[str]] = None
	locale: Optional[str] = None
	admin_doc: Optional[NAWAH_DOC] = None
	admin_password: Optional[str] = None
	anon_token: Optional[str] = None
	anon_privileges: Optional[Dict[str, List[str]]] = None
	user_attrs: Optional[Dict[str, ATTR]] = None
	user_settings: Optional[
		Dict[str, Dict[Literal['type', 'val'], Union[Literal['user', 'user_sys'], Any]]]
	] = None
	user_doc_settings: Optional[List[str]] = None
	groups: Optional[List[Dict[str, Any]]] = None
	default_privileges: Optional[Dict[str, List[str]]] = None
	data_indexes: Optional[List[Dict[str, Any]]] = None
	docs: Optional[List[Dict[str, Any]]] = None
	jobs: Optional[List[Dict[str, Any]]] = None
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
	realm: Optional[bool] = None
	force_admin_check: Optional[bool] = None