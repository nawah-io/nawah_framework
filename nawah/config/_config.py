from nawah.enums import Event, LOCALE_STRATEGY
from nawah.classes import (
	DictObj,
	BaseModel,
	NAWAH_DOC,
	NAWAH_ENV,
	ATTR,
	APP_CONFIG,
	PACKAGE_CONFIG,
	CLIENT_APP,
	ANALYTICS_EVENTS,
	SYS_DOC,
	USER_SETTING,
	JOB,
)

from typing import (
	List,
	Dict,
	Callable,
	Any,
	Union,
	Set,
	Tuple,
	Literal,
	TypedDict,
	Optional,
	cast,
	TYPE_CHECKING,
)

from croniter import croniter
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from passlib.hash import pbkdf2_sha512

import os, logging, datetime, time, requests

if TYPE_CHECKING:
	from nawah.base_module import BaseModule

logger = logging.getLogger('nawah')


def process_config(*, config: Union[APP_CONFIG, PACKAGE_CONFIG], pkgname: str = None):
	from nawah.utils import deep_update

	if type(config) not in [APP_CONFIG, PACKAGE_CONFIG]:
		logger.error(f'Config object of type \'{type(config)}\' is invalid. Exiting.')
		exit(1)

	if type(config) == PACKAGE_CONFIG and not pkgname:
		logger.error(
			'Provided Config object of type \'PACKAGE_CONFIG\' without \'pkgname\'. Exiting.'
		)
		exit(1)

	app_only_attrs = APP_CONFIG.__annotations__.keys()

	for config_attr in dir(config):
		config_attr_val = getattr(config, config_attr)

		# [DOC] Check existence of of api_level, version Config Attrs
		if type(config) == PACKAGE_CONFIG and config_attr in ['api_level', 'version']:
			if config_attr_val == None:
				logger.error(
					f'Package \'{pkgname}\' is missing \'{config_attr}\' Config Attr. Exiting.'
				)
				exit(1)
			# [DOC] Check type of api_level, version Config Attrs
			elif type(config_attr_val) != str:
				logger.error(
					f'Package \'{pkgname}\' is having invalid type of \'{config_attr}\'. Exiting.'
				)
				exit(1)
			else:
				# [DOC] Update corresponding Config
				getattr(Config, f'packages_{config_attr}s')[pkgname] = config_attr_val
		# [DOC] Skip non Config Attr attrs
		elif (
			config_attr.startswith('__')
			or config_attr_val == None
			or config_attr in app_only_attrs
		):
			continue
		# [DOC] For vars_types Config Attr, preserve package name for debugging purposes
		elif config_attr == 'vars_types':
			for var in config_attr_val.keys():
				Config.vars_types[var] = {'package': pkgname, 'type': config_attr_val[var]}
		elif type(config_attr_val) == list:
			for j in config_attr_val:
				getattr(Config, config_attr).append(j)
			if config_attr == 'locales':
				Config.locales = list(set(Config.locales))
		elif type(config_attr_val) == dict:
			if not getattr(Config, config_attr):
				setattr(Config, config_attr, {})
			deep_update(target=getattr(Config, config_attr), new_values=config_attr_val)
		else:
			setattr(Config, config_attr, config_attr_val)


class Config:
	debug: bool = False
	env: str
	port: int = 8081

	_sys_conn: AsyncIOMotorClient
	_sys_env: NAWAH_ENV
	_sys_docs: Dict[ObjectId, SYS_DOC] = {}
	_jobs_base: datetime.datetime

	_nawah_version: str
	packages_api_levels: Dict[str, str] = {}
	packages_versions: Dict[str, str] = {}

	_app_name: str
	_app_version: str
	_app_default_package: str
	_app_path: str
	_app_packages: Dict[str, str]

	test: bool = False

	emulate_test: bool = False
	force_admin_check: bool = False

	generate_ref: bool = False
	_api_ref: str

	generate_models: bool = False
	_api_models: str

	vars_types: Dict[str, Union[ATTR, Dict[str, Any]]] = {}
	vars: Dict[str, Any] = {}

	client_apps: Dict[str, CLIENT_APP] = {}

	analytics_events: ANALYTICS_EVENTS = {
		'app_conn_verified': True,
		'session_conn_auth': True,
		'session_user_auth': True,
		'session_conn_reauth': True,
		'session_user_reauth': True,
		'session_conn_deauth': True,
		'session_user_deauth': True,
	}

	conn_timeout: int = 120
	quota_anon_min: int = 40
	quota_auth_min: int = 100
	quota_ip_min: int = 500
	file_upload_limit: int = -1
	file_upload_timeout: int = 300

	data_server: str = 'mongodb://localhost'
	data_name: str = 'nawah_data'
	data_ssl: bool = False
	data_ca_name: Optional[str] = None
	data_ca: Optional[str] = None
	data_disk_use: bool = False

	data_azure_mongo: bool = False

	locales: List[str] = ['ar_AE', 'en_AE']
	locale: str = 'ar_AE'
	locale_strategy: LOCALE_STRATEGY = LOCALE_STRATEGY.DUPLICATE

	admin_doc: NAWAH_DOC = {}
	admin_password: str = '__0xADMIN'

	anon_token: str = '__ANON_TOKEN_f00000000000000000000012'
	anon_privileges: Dict[str, List[str]] = {}

	user_attrs: Dict[str, ATTR] = {}
	user_settings: Dict[str, USER_SETTING] = {}
	user_doc_settings: List[str] = []

	groups: List[Dict[str, Any]] = []
	default_privileges: Dict[str, List[str]] = {}

	data_indexes: List[Dict[str, Any]] = []

	docs: List[SYS_DOC] = []

	l10n: Dict[str, Dict[str, Any]] = {}

	jobs: Dict[str, JOB] = {}

	gateways: Dict[str, Callable] = {}

	types: Dict[str, Callable] = {}

	modules: Dict[str, 'BaseModule'] = {}
	modules_packages: Dict[str, List[str]] = {}

	@classmethod
	async def config_data(cls) -> None:
		from nawah.utils import generate_attr

		# [TODO] Add validator for user_attrs, user_doc_settings

		# [DOC] Check app packages
		if cls._app_packages or len(cls.packages_versions.keys()) > 2:
			logger.debug(
				'Found \'_app_packages\' Config Attr. Attempting to validate all loaded packages are matching _app_packages Config Attr value.'
			)

			cls._app_packages['core'] = cls.packages_versions['core']
			cls._app_packages[cls._app_default_package] = cls.packages_versions[
				cls._app_default_package
			]

			missing_packages = [
				package
				for package in cls._app_packages.keys()
				if package not in cls.packages_versions.keys()
			]
			if missing_packages:
				logger.error(
					f'At least one package is missing that is required by app. Missing package[s]: \'{", ".join(missing_packages)}\'. Exiting.'
				)
				exit(1)

			extra_packages = [
				package
				for package in cls.packages_versions.keys()
				if package not in cls._app_packages.keys()
			]
			if extra_packages:
				logger.error(
					f'At least one extra package is present in \'packages\' folder that is not required by app. Extra package[s]: \'{", ".join(extra_packages)}\'. Exiting.'
				)
				exit(1)

			# [DOC] Check for version mismatch
			for package, version in cls._app_packages.items():
				# [DOC] Skip core and default_packages
				if package in ['core', cls._app_default_package]:
					continue
				if version != cls.packages_versions[package]:
					logger.error(
						f'Package \'{package}\' version \'{cls.packages_versions[package]}\' is added to app but not matching required version \'{version}\'. Exiting.'
					)
					exit(1)

		# [DOC] Check API version
		if not cls.packages_api_levels:
			logger.warning(
				'No API-level specified for the app. Nawah would continue to run the app, but the developer should consider adding API-level to eliminate specs mismatch.'
			)
		else:
			nawah_level = '.'.join(cls._nawah_version.split('.')[0:2])
			for package, api_level in cls.packages_api_levels.items():
				if api_level != nawah_level:
					logger.error(
						f'Nawah framework is on API-level \'{nawah_level}\', but the app package \'{package}\' requires API-level \'{api_level}\'. Exiting.'
					)
					exit(1)
			try:
				versions = (
					(
						requests.get(
							'https://raw.githubusercontent.com/masaar/nawah_versions/master/versions.txt'
						).content
					)
					.decode('utf-8')
					.split('\n')
				)
				version_detected = ''
				for version in versions:
					if version.startswith(f'{nawah_level}.'):
						if version_detected and int(version.split('.')[-1]) < int(
							version_detected.split('.')[-1]
						):
							continue
						version_detected = version
				if version_detected and version_detected != cls._nawah_version:
					logger.warning(
						f'Your app is using Nawah version \'{cls._nawah_version}\' while newer version \'{version_detected}\' of the API-level is available. Please, update.'
					)
			except:
				logger.warning(
					'An error occurred while attempting to check for latest update to Nawah. Please, check for updates on your own.'
				)

		# [DOC] Check for jobs
		if cls.jobs:
			# [DOC] Check jobs schedule validity
			cls._jobs_base = datetime.datetime.utcnow()
			for job_name in cls.jobs.keys():
				job = cls.jobs[job_name]
				if not croniter.is_valid(job.schedule):
					logger.error(f'Job with schedule \'{job_name}\' schedule is invalid. Exiting.')
					exit(1)

				job._cron_schedule = croniter(job.schedule, cls._jobs_base)
				job._next_time = datetime.datetime.fromtimestamp(
					job._cron_schedule.get_next(), datetime.timezone.utc
				).isoformat()[:16]

		# [DOC] Check for presence of user_auth_attrs
		if not cls.user_attrs.keys():
			logger.error('No \'user_attrs\' are provided. Exiting.')
			exit(1)

		# [DOC] Check default values
		security_warning = '[SECURITY WARNING] {config_attr} is not explicitly set. It has been defaulted to \'{val}\' but in production environment you should consider setting it to your own to protect your app from breaches.'
		if cls.admin_password == '__ADMIN':
			logger.warning(security_warning.format(config_attr='Admin password', val='__ADMIN'))
		if cls.anon_token == '__ANON_TOKEN_f00000000000000000000012':
			logger.warning(
				security_warning.format(
					config_attr='Anon token',
					val='__ANON_TOKEN_f00000000000000000000012',
				)
			)

		# [DOC] Check for Env Vars
		attrs_defaults = {
			'data_server': 'mongodb://localhost',
			'data_name': 'nawah_data',
			'data_ssl': False,
			'data_ca_name': False,
			'data_ca': False,
			'emulate_test': False,
		}
		for attr_name in attrs_defaults.keys():
			attr_val = getattr(cls, attr_name)
			if type(attr_val) == str and attr_val.startswith('$__env.'):
				logger.debug(f'Detected Env Variable for config attr \'{attr_name}\'')
				if not os.getenv(attr_val[7:]):
					logger.warning(
						f'Couldn\'t read Env Variable for config attr \'{attr_name}\'. Defaulting to \'{attrs_defaults[attr_name]}\''
					)
					setattr(cls, attr_name, attrs_defaults[attr_name])
				else:
					# [DOC] Set data_ssl to True rather than string Env Variable value
					if attr_name == 'ssl':
						attr_val = True
					else:
						attr_val = os.getenv(attr_val[7:])
					logger.warning(
						f'Setting Env Variable for config attr \'{attr_name}\' to \'{attr_val}\''
					)
					setattr(cls, attr_name, attr_val)

		# [DOC] Check SSL settings
		if cls.data_ca and cls.data_ca_name:
			__location__ = os.path.realpath(os.path.join('.'))
			if not os.path.exists(os.path.join(__location__, 'certs')):
				os.makedirs(os.path.join(__location__, 'certs'))
			with open(os.path.join(__location__, 'certs', cls.data_ca_name), 'w') as f:
				f.write(cls.data_ca)

		from nawah import data as Data

		# [DOC] Create default env dict
		anon_user = cls.compile_anon_user()
		anon_session = DictObj(cls.compile_anon_session())
		anon_session = cast(BaseModel, anon_session)
		anon_session['user'] = DictObj(anon_user)
		cls._sys_conn = Data.create_conn()
		cls._sys_env = {
			'conn': cls._sys_conn,
			'REMOTE_ADDR': '127.0.0.1',
			'HTTP_USER_AGENT': 'Nawah',
			'client_app': '__sys',
			'session': anon_session,
			'watch_tasks': {},
		}

		if cls.data_azure_mongo:
			for module in cls.modules.keys():
				try:
					if cls.modules[module].collection:
						logger.debug(
							f'Attempting to create shard collection: {cls.modules[module].collection}.'
						)
						cls._sys_conn[cls.data_name].command(
							'shardCollection',
							f'{cls.data_name}.{cls.modules[module].collection}',
							key={'_id': 'hashed'},
						)
					else:
						logger.debug(f'Skipping service module: {module}.')
				except Exception as err:
					logger.error(err)

		# [DOC] Check test mode
		if cls.test:
			logger.debug('Test mode detected.')
			logger.setLevel(logging.DEBUG)
			__location__ = os.path.realpath(os.path.join('.'))
			if not os.path.exists(os.path.join(__location__, 'tests')):
				os.makedirs(os.path.join(__location__, 'tests'))
			for module in cls.modules.keys():
				module_collection = cls.modules[module].collection
				if module_collection:
					logger.debug(
						f'Updating collection name \'{module_collection}\' of module {module}'
					)
					module_collection = cls.modules[module].collection = f'test_{module_collection}'
					if cls.test:
						logger.debug(f'Flushing test collection \'{module_collection}\'')
						await Data.drop(
							env=cls._sys_env,
							collection_name=module_collection,
						)
				else:
					logger.debug(f'Skipping service module {module}')

		# [DOC] Test user_settings
		logger.debug('Testing user_settings.')
		if cls.user_settings:
			for user_setting in cls.user_settings.keys():
				logger.debug(f'Testing {user_setting}')
				if type(cls.user_settings[user_setting]) != USER_SETTING:
					logger.error(
						f'Invalid Config Attr \'user_settings\' with key \'{user_setting}\' of type \'{type(cls.user_settings[user_setting])}\' with required type \'USER_SETTING\'. Exiting.'
					)
					exit(1)

				# [DOC] Validate USER_SETTING
				cls.user_settings[user_setting]._validate()

		# [DOC] Checking users collection
		# [TODO] Updated sequence to handle users
		logger.debug('Testing users collection.')
		user_results = await cls.modules['user'].read(
			skip_events=[Event.PERM, Event.ON],
			env=cls._sys_env,
			query=[{'_id': 'f00000000000000000000010'}],
		)
		if not user_results.args.count:
			logger.debug('ADMIN user not found, creating it.')
			# [DOC] Prepare base ADMIN user doc
			admin_create_doc = {
				'_id': ObjectId('f00000000000000000000010'),
				'name': {cls.locale: '__ADMIN'},
				'groups': [],
				'privileges': {'*': ['*']},
				'locale': cls.locale,
			}
			# [DOC] Update ADMIN user doc with admin_doc Config Attr
			admin_create_doc.update(cls.admin_doc)

			for auth_attr in cls.user_attrs.keys():
				admin_create_doc[f'{auth_attr}_hash'] = pbkdf2_sha512.using(rounds=100000).hash(
					f'{auth_attr}{admin_create_doc[auth_attr]}{cls.admin_password}{cls.anon_token}'.encode(
						'utf-8'
					)
				)
			admin_results = await cls.modules['user'].create(
				skip_events=[Event.PERM],
				env=cls._sys_env,
				doc=admin_create_doc,
			)
			logger.debug(f'ADMIN user creation results: {admin_results}')
			if admin_results.status != 200:
				logger.error('Config step failed. Exiting.')
				exit(1)
		elif not cls.force_admin_check:
			logger.warning(
				'ADMIN user found, skipping check due to force_admin_check Config Attr.'
			)
		else:
			logger.warning('ADMIN user found, checking it due to force_admin_check Config Attr.')
			admin_doc: BaseModel = user_results.args.docs[0]
			admin_doc_update = {}
			for attr in cls.admin_doc.keys():
				if (
					attr not in admin_doc
					or not admin_doc[attr]
					or cls.admin_doc[attr] != admin_doc[attr]
				):
					if (
						type(cls.admin_doc[attr]) == dict
						and cls.locale in cls.admin_doc[attr].keys()
						and type(admin_doc[attr]) == dict
						and (
							(
								cls.locale in admin_doc[attr].keys()
								and cls.admin_doc[attr][cls.locale] == admin_doc[attr][cls.locale]
							)
							or (cls.locale not in admin_doc[attr].keys())
						)
					):
						continue
					logger.debug(f'Detected change in \'admin_doc.{attr}\' Config Attr.')
					admin_doc_update[attr] = cls.admin_doc[attr]
			for auth_attr in cls.user_attrs.keys():
				auth_attr_hash = pbkdf2_sha512.using(rounds=100000).hash(
					f'{auth_attr}{admin_doc[auth_attr]}{cls.admin_password}{cls.anon_token}'.encode(
						'utf-8'
					)
				)
				if (
					f'{auth_attr}_hash' not in admin_doc
					or auth_attr_hash != admin_doc[f'{auth_attr}_hash']
				):
					logger.debug(f'Detected change in \'admin_password\' Config Attr.')
					admin_doc_update[f'{auth_attr}_hash'] = auth_attr_hash
			if len(admin_doc_update.keys()):
				logger.debug(f'Attempting to update ADMIN user with doc: \'{admin_doc_update}\'')
				admin_results = await cls.modules['user'].update(
					skip_events=[Event.PERM, Event.PRE, Event.ON],
					env=cls._sys_env,
					query=[{'_id': ObjectId('f00000000000000000000010')}],
					doc=admin_doc_update,
				)
				logger.debug(f'ADMIN user update results: {admin_results}')
				if admin_results.status != 200:
					logger.error('Config step failed. Exiting.')
					exit(1)
			else:
				logger.debug('ADMIN user is up-to-date.')

		cls._sys_docs[ObjectId('f00000000000000000000010')] = SYS_DOC(module='user')

		# [DOC] Test if ANON user exists
		user_results = await cls.modules['user'].read(
			skip_events=[Event.PERM, Event.ON],
			env=cls._sys_env,
			query=[{'_id': 'f00000000000000000000011'}],
		)
		if not user_results.args.count:
			logger.debug('ANON user not found, creating it.')
			anon_results = await cls.modules['user'].create(
				skip_events=[Event.PERM, Event.PRE, Event.ON],
				env=cls._sys_env,
				doc=cls.compile_anon_user(),
			)
			logger.debug(f'ANON user creation results: {anon_results}')
			if anon_results.status != 200:
				logger.error('Config step failed. Exiting.')
				exit(1)
		else:
			logger.debug('ANON user found, checking it.')
			anon_doc = cls.compile_anon_user()
			anon_doc_update = {}
			for attr in cls.user_attrs.keys():
				if attr not in anon_doc or not anon_doc[attr]:
					logger.debug(f'Detected change in \'anon_doc.{attr}\' Config Attr.')
					anon_doc_update[attr] = generate_attr(attr_type=cls.user_attrs[attr])
			for module in cls.anon_privileges.keys():
				if module not in anon_doc or set(anon_doc[module]) != set(
					cls.anon_privileges[module]
				):
					logger.debug(f'Detected change in \'anon_privileges\' Config Attr.')
					anon_doc_update[f'privileges.{module}'] = cls.anon_privileges[module]
			for auth_attr in cls.user_attrs.keys():
				if (
					f'{auth_attr}_hash' not in anon_doc
					or anon_doc[f'{auth_attr}_hash'] != cls.anon_token
				):
					logger.debug(f'Detected change in \'anon_token\' Config Attr.')
					anon_doc_update[attr] = cls.anon_token
				anon_doc_update[f'{auth_attr}_hash'] = cls.anon_token
			if len(anon_doc_update.keys()):
				logger.debug(f'Attempting to update ANON user with doc: \'{anon_doc_update}\'')
				anon_results = await cls.modules['user'].update(
					skip_events=[Event.PERM, Event.PRE, Event.ON],
					env=cls._sys_env,
					query=[{'_id': ObjectId('f00000000000000000000011')}],
					doc=anon_doc_update,
				)
				logger.debug(f'ANON user update results: {anon_results}')
				if anon_results.status != 200:
					logger.error('Config step failed. Exiting.')
					exit(1)
			else:
				logger.debug('ANON user is up-to-date.')

		cls._sys_docs[ObjectId('f00000000000000000000011')] = SYS_DOC(module='user')

		logger.debug('Testing sessions collection.')
		# [DOC] Test if ANON session exists
		session_results = await cls.modules['session'].read(
			skip_events=[Event.PERM, Event.ON],
			env=cls._sys_env,
			query=[{'_id': 'f00000000000000000000012'}],
		)
		if not session_results.args.count:
			logger.debug('ANON session not found, creating it.')
			anon_results = await cls.modules['session'].create(
				skip_events=[Event.PERM, Event.PRE, Event.ON],
				env=cls._sys_env,
				doc=cls.compile_anon_session(),
			)
			logger.debug(f'ANON session creation results: {anon_results}')
			if anon_results.status != 200:
				logger.error('Config step failed. Exiting.')
				exit(1)
		cls._sys_docs[ObjectId('f00000000000000000000012')] = SYS_DOC(module='session')

		logger.debug('Testing groups collection.')
		# [DOC] Test if DEFAULT group exists
		group_results = await cls.modules['group'].read(
			skip_events=[Event.PERM, Event.ON],
			env=cls._sys_env,
			query=[{'_id': 'f00000000000000000000013'}],
		)
		if not group_results.args.count:
			logger.debug('DEFAULT group not found, creating it.')
			group_create_doc = {
				'_id': ObjectId('f00000000000000000000013'),
				'user': ObjectId('f00000000000000000000010'),
				'name': {locale: '__DEFAULT' for locale in cls.locales},
				'bio': {locale: '__DEFAULT' for locale in cls.locales},
				'privileges': cls.default_privileges,
			}
			group_results = await cls.modules['group'].create(
				skip_events=[Event.PERM, Event.PRE, Event.ON],
				env=cls._sys_env,
				doc=group_create_doc,
			)
			logger.debug(f'DEFAULT group creation results: {group_results}')
			if group_results.status != 200:
				logger.error('Config step failed. Exiting.')
				exit(1)
		else:
			logger.debug('DEFAULT group found, checking it.')
			default_doc = group_results.args.docs[0]
			default_doc_update: Dict[str, Any] = {}
			for module in cls.default_privileges.keys():
				if module not in default_doc.privileges.keys() or set(
					default_doc.privileges[module]
				) != set(cls.default_privileges[module]):
					logger.debug(f'Detected change in \'default_privileges\' Config Attr.')
					default_doc_update[f'privileges.{module}'] = cls.default_privileges[module]
			if len(default_doc_update.keys()):
				logger.debug(
					f'Attempting to update DEFAULT group with doc: \'{default_doc_update}\''
				)
				default_results = await cls.modules['group'].update(
					skip_events=[Event.PERM, Event.PRE, Event.ON],
					env=cls._sys_env,
					query=[{'_id': ObjectId('f00000000000000000000013')}],
					doc=default_doc_update,
				)
				logger.debug(f'DEFAULT group update results: {default_results}')
				if anon_results.status != 200:
					logger.error('Config step failed. Exiting.')
					exit(1)
			else:
				logger.debug('DEFAULT group is up-to-date.')

		cls._sys_docs[ObjectId('f00000000000000000000013')] = SYS_DOC(module='group')

		# [DOC] Test app-specific groups
		logger.debug('Testing app-specific groups collection.')
		for group in cls.groups:
			group_results = await cls.modules['group'].read(
				skip_events=[Event.PERM, Event.ON],
				env=cls._sys_env,
				query=[{'_id': group['_id']}],
			)
			if not group_results.args.count:
				logger.debug(
					f'App-specific group with name \'{group["name"]}\' not found, creating it.'
				)
				group_results = await cls.modules['group'].create(
					skip_events=[Event.PERM, Event.PRE, Event.ON],
					env=cls._sys_env,
					doc=group,
				)
				logger.debug(
					f'App-specific group with name {group["name"]} creation results: {group_results}'
				)
				if group_results.status != 200:
					logger.error('Config step failed. Exiting.')
					exit(1)
			else:
				logger.debug(
					f'App-specific group with name \'{group["name"]}\' found, checking it.'
				)
				group_doc = group_results.args.docs[0]
				group_doc_update = {}
				if 'privileges' in group.keys():
					for module in group['privileges'].keys():
						if module not in group_doc.privileges.keys() or set(
							group_doc.privileges[module]
						) != set(group['privileges'][module]):
							logger.debug(
								f'Detected change in \'privileges\' Doc Arg for group with name \'{group["name"]}\'.'
							)
							group_doc_update[f'privileges.{module}'] = group['privileges'][module]
				if len(group_doc_update.keys()):
					logger.debug(
						f'Attempting to update group with name \'{group["name"]}\' with doc: \'{group_doc_update}\''
					)
					group_results = await cls.modules['group'].update(
						skip_events=[Event.PERM, Event.PRE, Event.ON],
						env=cls._sys_env,
						query=[{'_id': group['_id']}],
						doc=group_doc_update,
					)
					logger.debug(
						f'Group with name \'{group["name"]}\' update results: {group_results}'
					)
					if group_results.status != 200:
						logger.error('Config step failed. Exiting.')
						exit(1)
				else:
					logger.debug(f'Group with name \'{group["name"]}\' is up-to-date.')

			cls._sys_docs[ObjectId(group['_id'])] = SYS_DOC(module='group')

		# [DOC] Test app-specific data indexes
		logger.debug('Testing data indexes')
		for index in cls.data_indexes:
			logger.debug(f'Attempting to create data index: {index}')
			try:
				cls._sys_conn[cls.data_name][index['collection']].create_index(index['index'])
			except Exception as e:
				logger.error(f'Failed to create data index: {index}, with error: {e}')
				logger.error('Evaluate error and take action manually.')

		logger.debug(
			'Creating \'var\', \'type\', \'user\' data indexes for settings collections.'
		)
		cls._sys_conn[cls.data_name]['settings'].create_index([('var', 1)])
		cls._sys_conn[cls.data_name]['settings'].create_index([('type', 1)])
		cls._sys_conn[cls.data_name]['settings'].create_index([('user', 1)])
		logger.debug(
			'Creating \'user\', \'event\', \'subevent\' data indexes for analytics collections.'
		)
		cls._sys_conn[cls.data_name]['analytics'].create_index([('user', 1)])
		cls._sys_conn[cls.data_name]['analytics'].create_index([('event', 1)])
		cls._sys_conn[cls.data_name]['analytics'].create_index([('subevent', 1)])
		logger.debug('Creating \'__deleted\' data indexes for all collections.')
		for module in cls.modules:
			if cls.modules[module].collection:
				logger.debug(
					f'Attempting to create \'__deleted\' data index for collection: {cls.modules[module].collection}'
				)
				cls._sys_conn[cls.data_name][cls.modules[module].collection].create_index(
					[('__deleted', 1)]
				)

		# [DOC] Test app-specific docs
		logger.debug('Testing docs.')
		for doc in cls.docs:
			if type(doc) != SYS_DOC:
				logger.error(f'Invalid Config Attr \'docs\'. Exiting.')
				exit(1)

			doc_results = await cls.modules[doc.module].read(
				skip_events=[Event.PERM, Event.PRE, Event.ON, Event.ARGS],
				env=cls._sys_env,
				query=[{doc.key: doc.key_value}],  # type: ignore
			)
			if not doc_results.args.count:
				skip_events = [Event.PERM]
				if doc.skip_args == True:
					skip_events.append(Event.ARGS)
				doc.doc = cast(NAWAH_DOC, doc.doc)
				doc_results = await cls.modules[doc.module].create(
					skip_events=skip_events, env=cls._sys_env, doc=doc.doc
				)
				logger.debug(
					'App-specific doc with %s \'%s\' of module \'%s\' creation results: %s',
					doc.key,
					doc.key_value,
					doc.module,
					doc_results,
				)
				if doc_results.status != 200:
					logger.error('Config step failed. Exiting.')
					exit(1)
			cls._sys_docs[ObjectId(doc_results.args.docs[0]._id)] = SYS_DOC(module=doc.module)

		# [DOC] Check for emulate_test mode
		if cls.emulate_test:
			cls.test = True

	@classmethod
	def compile_anon_user(cls):
		from nawah.utils import generate_attr

		anon_doc = {
			'_id': ObjectId('f00000000000000000000011'),
			'name': {cls.locale: '__ANON'},
			'groups': [],
			'privileges': cls.anon_privileges,
			'locale': cls.locale,
		}
		for attr in cls.user_attrs.keys():
			anon_doc[attr] = generate_attr(attr_type=cls.user_attrs[attr])
		for auth_attr in cls.user_attrs.keys():
			anon_doc[f'{auth_attr}_hash'] = cls.anon_token
		return anon_doc

	@classmethod
	def compile_anon_session(cls):
		session_doc = {
			'_id': ObjectId('f00000000000000000000012'),
			'user': ObjectId('f00000000000000000000011'),
			'host_add': '127.0.0.1',
			'user_agent': cls.anon_token,
			'timestamp': '1970-01-01T00:00:00',
			'expiry': '1970-01-01T00:00:00',
			'token': cls.anon_token,
			'token_hash': cls.anon_token,
		}
		return session_doc
