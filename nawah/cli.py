from nawah import __version__

from typing import Dict, Literal, Any, Optional

import argparse, os, logging, datetime, sys, subprocess, asyncio, traceback, shutil, urllib.request, re, tarfile, string, random, tempfile, pkgutil, glob

logger = logging.getLogger('nawah')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s]  %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.INFO)

# [DOC] Constatnt TESTING_COMPATIBILITY indicates whether package is loaded in testing compatibility mode
TESTING_COMPATIBILITY = False


def nawah_cli():
	global sys, os

	if sys.version_info.major != 3 or sys.version_info.minor < 8:
		print('Nawah framework CLI can only run with Python >= 3.8. Exiting.')
		exit(1)

	parser = argparse.ArgumentParser()
	parser.add_argument(
		'--version',
		help='Show Nawah framework version and exit',
		action='version',
		version=f'Nawah framework v{__version__}',
	)

	subparsers = parser.add_subparsers(
		title='Command', description='Nawah framework CLI command to run', dest='command'
	)

	parser_launch = subparsers.add_parser('launch', help='Launch Nawah app')
	parser_launch.set_defaults(func=launch)
	parser_launch.add_argument('--env', help='Choose specific env')
	parser_launch.add_argument('--debug', help='Enable debug mode', action='store_true')
	parser_launch.add_argument(
		'--log',
		help='Enable debug mode and log all debug messages to log file',
		action='store_true',
	)
	parser_launch.add_argument('-p', '--port', help='Set custom port [default 8081]')
	parser_launch.add_argument(
		'--force-admin-check',
		help='Force ADMIN doc checked and updated, if ADMIN doc is changed',
		action='store_true',
	)
	parser_launch.add_argument(
		'--test-collections', help='Enable Test Collections Mode', action='store_true'
	)

	parser_test = subparsers.add_parser('test', help='Test Nawah app')
	parser_test.set_defaults(func=test)
	parser_test.add_argument('test_name', type=str, help='Name of the test to run')
	parser_test.add_argument('--env', help='Choose specific env')
	parser_test.add_argument(
		'--skip-flush',
		help='Skip flushing previous test data collections',
		action='store_true',
	)
	parser_test.add_argument(
		'--force',
		help='Force running all test steps even if one is failed',
		action='store_true',
	)
	parser_test.add_argument(
		'--use-env',
		help='Run tests on selected env rather than sandbox env',
		action='store_true',
	)
	parser_test.add_argument(
		'--breakpoint',
		help='Create debugger breakpoint upon failure of test',
		action='store_true',
	)
	parser_test.add_argument('--debug', help='Enable debug mode', action='store_true')

	parser_packages = subparsers.add_parser('packages', help='Manage Nawah app packages')
	parser_packages.set_defaults(func=lambda _: None)
	packages_subparser = parser_packages.add_subparsers(
		title='Packages Command',
		description='Packages command to run',
		dest='packages_command',
	)

	parser_packages_install = packages_subparser.add_parser(
		'install', help='Install Nawah app packages'
	)
	parser_packages_install.set_defaults(func=packages_install)

	parser_packages_add = packages_subparser.add_parser(
		'add', help='Add package to Nawah app'
	)
	parser_packages_add.set_defaults(
		func=lambda args: _packages_add(
			package_name=args.package_name,
			source=args.source,
			version=args.version,
			auth=args.auth,
		)
	)
	parser_packages_add.add_argument(
		'package_name', help='Package name to add to Nawah app'
	)
	parser_packages_add.add_argument(
		'--source',
		help='Package source [default https://gitlab.com/api/v4/projects/24381550/packages/pypi/simple]',
		default='https://gitlab.com/api/v4/projects/24381550/packages/pypi/simple',
	)
	parser_packages_add.add_argument(
		'--version',
		help='Package version (repo tag name) to install [default latest]',
		default='latest',
	)
	parser_packages_add.add_argument(
		'--auth',
		help='String representing colon-separated username and password combination to authorise the source',
	)

	parser_packages_rm = packages_subparser.add_parser(
		'rm', help='Remove package from Nawah app'
	)
	parser_packages_rm.set_defaults(
		func=lambda args: _packages_rm(package_name=args.package_name, confirm=not args.y)
	)
	parser_packages_rm.add_argument(
		'package_name', help='Package name to remove from Nawah app'
	)
	parser_packages_rm.add_argument('-y', help='Skip confirmation', action='store_true')

	parser_packages_audit = packages_subparser.add_parser(
		'audit', help='Audit packages in Nawah app'
	)
	parser_packages_audit.set_defaults(func=packages_audit)

	parser_ref = subparsers.add_parser('generate_ref', help='Generate Nawah app reference')
	parser_ref.set_defaults(func=generate_ref)
	parser_ref.add_argument('--debug', help='Enable debug mode', action='store_true')

	parser_ref = subparsers.add_parser('generate_models', help='Generate Nawah app models')
	parser_ref.set_defaults(func=generate_models)
	parser_ref.add_argument('format', help='Format of models', choices=['js', 'ts'])
	parser_ref.add_argument('--debug', help='Enable debug mode', action='store_true')

	args = parser.parse_args()

	if args.command:
		if args.command == 'packages' and not args.packages_command:
			parser_packages.print_help()
		else:
			args.func(args)
	else:
		parser.print_help()


def launch(
	args: argparse.Namespace,
	custom_launch: Literal['test', 'generate_ref', 'generate_models'] = None,
):
	global os, asyncio
	global handler

	# [DOC] Update Config with Nawah CLI args
	from nawah.config import Config, process_config

	Config._nawah_version = __version__
	if custom_launch not in ['generate_ref', 'generate_models']:
		Config.env = args.env
	if not custom_launch:
		Config.test_collections = args.test_collections
		Config.force_admin_check = args.force_admin_check

	# [DOC] Check for debug CLI Arg
	if args.debug:
		Config.debug = True
		logger.setLevel(logging.DEBUG)
	# [DOC] Check for log CLI Arg
	if not custom_launch and args.log:
		logger.removeHandler(handler)
		if not os.path.exists(os.path.join('.', 'logs')):
			os.makedirs(os.path.join('.', 'logs'))
		handler = logging.FileHandler(
			filename=os.path.join(
				'.',
				'logs',
				f'{datetime.datetime.utcnow().strftime("%d-%b-%Y")}.log',
			)
		)
		handler.setFormatter(formatter)
		logger.addHandler(handler)
		logger.setLevel(logging.DEBUG)

	from nawah.app import run_app
	import json

	try:
		try:
			sys.path.append('.')
			nawah_app = __import__('nawah_app')
			app_config = nawah_app.config

			with open('packages.json') as f:
				packages = json.loads(f.read())

			Config._app_packages = {k: v['version'] for k, v in packages.items()}
		except ModuleNotFoundError:
			logger.error(f'No \'nawah_app.py\' file found in CWD. Exiting.')
			exit(1)
		except AttributeError:
			logger.error(
				f'File \'nawah_app.py\' was found but it doesn\'t have \'config\' method. Exiting.'
			)
			exit(1)
		logger.info(
			f'Found app \'{app_config.name} (v{app_config.version})\'. Attempting to load App Config.'
		)
		Config._app_name = app_config.name
		Config._app_version = app_config.version
		Config._app_default_package = app_config.default_package

		# [DOC] Check all required values of App Config are present
		if not Config._app_name or not Config._app_version or not Config._app_default_package:
			logger.error(
				f'App Config are missing at least one of the following \'name, version, default_package\'. Exiting.'
			)
			exit(1)

		Config._app_path = os.path.realpath('.')
		# [DOC] Read app_config and update Config accordingly
		# [DOC] Check envs, env
		if custom_launch not in ['generate_ref', 'generate_models'] and app_config.envs:
			if not args.env and not app_config.env:
				logger.error(
					'App Config Attr \'envs\' found, but no \'env\' App Config Attr, or CLI Attr were defined.'
				)
				exit(1)
			if args.env:
				if args.env in app_config.envs.keys():
					logger.info(f'Setting \'env\' Config Attr to \'env\' CLI Arg value \'{args.env}\'')
				else:
					logger.error(
						f'Found value \'{args.env}\' for \'env\' CLI Arg, but not defined in \'envs\' App Config Attr. Exiting.'
					)
					exit(1)
			else:
				if app_config.env in app_config.envs.keys():
					logger.info(
						f'Setting \'env\' Config Attr to \'env\' App Config Attr value \'{app_config.env}\''
					)
					Config.env = app_config.env
				elif app_config.env.startswith('$__env.'):
					logger.info(
						'Found Env Variable for \'env\' App Config Attr. Attempting to process it.'
					)
					env_env_var = app_config.env.replace('$__env.', '')
					env = os.getenv(env_env_var)
					if env:
						logger.info(
							f'Setting \'env\' Config Attr to Env Variable \'{env_env_var}\' value \'{env}\'.'
						)
						Config.env = env
					else:
						logger.error(f'No value found for Env Variable \'{env_env_var}\'. Exiting.')
						exit(1)
				else:
					logger.error(
						f'Found value \'{args.env}\' for \'env\' CLI Arg, but not defined in \'envs\' App Config Attr. Exiting.'
					)
					exit(1)
			logger.info(
				f'Beginning to extract Config Attrs defined in selected \'env\', \'{Config.env}\', to App Config Attrs.'
			)
			for config_attr in dir(app_config.envs[Config.env]):
				if (
					config_attr.startswith('__')
					or getattr(app_config.envs[Config.env], config_attr) == None
				):
					continue
				logger.info(f'Extracting \'{config_attr}\' Config Attr to App Config Attr')
				setattr(
					app_config,
					config_attr,
					getattr(app_config.envs[Config.env], config_attr),
				)
				setattr(
					Config,
					config_attr,
					getattr(app_config.envs[Config.env], config_attr),
				)
		# [DOC] Check port Config Attr
		if not custom_launch and app_config.port:
			if args.port:
				logger.info(
					f'Ignoring \'port\' App Config Attr in favour of \'port\' CLI Arg with value \'{args.port}\'.'
				)
				try:
					Config.port = int(args.port)
				except:
					logger.error(f'Port should be in integer format. Exiting.')
					exit(1)
			else:
				logger.info('Found \'port\' App Config Attr. Attempting to process it.')
				if type(app_config.port) == int:
					Config.port = app_config.port
					logger.info(f'Setting \'port\' Config Attr to \'{Config.port}\'.')
				elif type(app_config.port) == str and app_config.port.startswith('$__env.'):
					logger.info(
						'Found Env Variable for \'port\' App Config Attr. Attempting to process it.'
					)
					port_env_var = app_config.port.replace('$__env.', '')
					port = os.getenv(port_env_var)
					if port:
						logger.info(
							f'Setting \'port\' Config Attr to Env Variable \'{port_env_var}\' value \'{port}\'.'
						)
						try:
							Config.port = int(port)
						except:
							logger.error(
								f'Env Variable \'{port_env_var}\' value \'{port}\' can\'t be converted to integer. Exiting.'
							)
							exit(1)
					else:
						logger.error(f'No value found for Env Variable \'{port_env_var}\'. Exiting.')
						exit(1)
				else:
					logger.error(
						f'Invalid value type for \'port\' Config Attr with value \'{app_config.port}\'. Exiting.'
					)
					exit(1)
		# [DOC] Check debug Config Attr
		if app_config.debug:
			if args.debug:
				logger.info(
					f'Ignoring \'debug\' App Config Attr in favour of \'debug\' CLI Arg with value \'{args.debug}\'.'
				)
				Config.debug = args.debug
			else:
				logger.info('Found \'debug\' App Config Attr. Attempting to process it.')
				if type(app_config.debug) == bool:
					Config.debug = app_config.debug
					logger.info(f'Setting \'debug\' Config Attr to \'{Config.debug}\'.')
				elif type(app_config.debug) == str and app_config.debug.startswith('$__env.'):
					logger.info(
						'Found Env Variable for \'debug\' App Config Attr. Attempting to process it.'
					)
					debug_env_var = app_config.debug.replace('$__env.', '')
					debug = os.getenv(debug_env_var)
					if debug:
						logger.info(
							f'Setting \'debug\' Config Attr to Env Variable \'{debug_env_var}\' as \'True\'.'
						)
						Config.debug = True
					else:
						logger.info(
							f'No value found for Env Variable \'{debug_env_var}\'. Setting \'debug\' to \'False\'.'
						)
						Config.debug = False
				else:
					logger.error(
						f'Invalid value type for \'debug\' Config Attr with value \'{app_config.debug}\'. Exiting.'
					)
					exit(1)
				if Config.debug:
					logger.setLevel(logging.DEBUG)
		# [DOC] Check force_admin_check Config Attr
		if not custom_launch and app_config.force_admin_check:
			if args.force_admin_check:
				logger.info(
					f'Ignoring \'force_admin_check\' App Config Attr in favour of \'force_admin_check\' CLI Arg with value \'{args.force_admin_check}\'.'
				)
				Config.force_admin_check = True
			else:
				logger.info(
					'Found \'force_admin_check\' App Config Attr. Attempting to process it.'
				)
				if type(app_config.force_admin_check) == bool:
					Config.force_admin_check = app_config.force_admin_check
					logger.info(
						f'Setting \'force_admin_check\' Config Attr to \'{Config.force_admin_check}\'.'
					)
				elif type(
					app_config.force_admin_check
				) == str and app_config.force_admin_check.startswith('$__env.'):
					logger.info(
						'Found Env Variable for \'force_admin_check\' App Config Attr. Attempting to process it.'
					)
					check_env_var = app_config.force_admin_check.replace('$__env.', '')
					check = os.getenv(check_env_var)
					if check:
						logger.info(
							f'Setting \'force_admin_check\' Config Attr to Env Variable \'{check_env_var}\' as \'True\'.'
						)
						Config.force_admin_check = True
					else:
						logger.info(
							f'No value found for Env Variable \'{check_env_var}\'. Setting \'force_admin_check\' to \'False\'.'
						)
						Config.force_admin_check = False
				else:
					logger.error(
						f'Invalid value type for \'force_admin_check\' Config Attr with value \'{app_config.force_admin_check}\'. Exiting.'
					)
					exit(1)
		# [TODO] Implement realm APP Config Attr checks
		# [DOC] Process other app config attrs as PACKAGE_CONFIG
		process_config(config=app_config)
	except:
		logger.error(
			'An unexpected exception happened while attempting to process Nawah app. Exception details:'
		)
		logger.error(traceback.format_exc())
		logger.error('Exiting.')
		exit(1)

	asyncio.run(run_app())


def test(args: argparse.Namespace):
	# [DOC] Update Config with Nawah framework CLI args
	from nawah.config import Config

	Config.test = True
	Config.test_name = args.test_name
	Config.test_skip_flush = args.skip_flush
	Config.test_force = args.force
	Config.test_env = args.use_env
	Config.test_breakpoint = args.breakpoint
	launch(args=args, custom_launch='test')


def packages_install(args: argparse.Namespace):
	import json

	app_path = os.path.realpath('.')
	sys.path.insert(0, app_path)

	with open(os.path.join(app_path, 'packages.json')) as f:
		packages = json.loads(f.read())

	for package_name in packages:
		logger.info(f'Attempting to install package \'{package_name}\'')
		_packages_add(
			package_name=package_name,
			source=packages[package_name]['source'],
			version=packages[package_name]['version'],
			auth=packages[package_name]['auth']
			if 'auth' in packages[package_name].keys()
			else None,
		)

	logger.info('Done installing all packages!')


# [DOC] The single underscore to indicate this is not being called directly by argsparser but through a proxy callable
def _packages_add(*, package_name: str, source: str, version: str, auth: Optional[str]):
	import json

	global TESTING_COMPATIBILITY
	TESTING_COMPATIBILITY = True
	logger.info('Checking packages conflicts.')
	app_path = os.path.realpath(os.path.join('.'))
	packages_path = os.path.realpath(os.path.join('.', 'packages'))
	package_path = os.path.realpath(os.path.join('.', 'packages', package_name))

	with open(os.path.join(app_path, 'packages.json')) as f:
		packages = json.loads(f.read())

	api_level = '.'.join(__version__.split('.')[:2])

	if os.path.exists(package_path):
		logger.info(
			f'Package \'{package_name}\' already exists in app. Attempting to test compatibility with API Level and version.'
		)
		try:
			sys.path.insert(0, os.path.realpath('.'))
			sys.path.insert(0, packages_path)
			package = __import__(package_name)
		except:
			logger.error('Failed to load package to test compatibility and version. Exiting.')
			exit(1)

		if package.config.api_level != api_level:
			logger.error(
				f'App is using API Level {api_level}, but package is on API Level {package.config.api_level}. Exiting.'
			)
			exit(1)

		logger.info(f'Package is compatible with app API Level. Attempting to check version.')

		if package.config.version != (package_version := packages[package_name]['version']):
			logger.error(
				f'Package is on version {package.config.version}, but app requires version {package_version}. Exiting.'
			)
			exit(1)

		logger.info(f'Package is already installed with correct version.')

		TESTING_COMPATIBILITY = False

		return

	authed_source = source
	try:
		if auth:
			logger.info(
				f'Detected \'auth\' configuration for source. Attempting to authorise source.'
			)
			auth_username, auth_password = auth.split(':')
			if auth_username.startswith('__env.'):
				logger.info(
					f'Detected environement variable for \'auth_username\' configuration. Setting it.'
				)
				auth_username = os.environ[auth_username.replace('__env.', '')]
			if auth_password.startswith('__env.'):
				logger.info(
					f'Detected environement variable for \'auth_password\' configuration. Setting it.'
				)
				auth_password = os.environ[auth_password.replace('__env.', '')]
			authed_source = (
				authed_source.split('://', 1)[0]
				+ '://'
				+ auth_username
				+ ':'
				+ auth_password
				+ '@'
				+ authed_source.split('://', 1)[1]
			)
			logger.info(f'Processed \'auth\' configuration successfully.')
	except:
		logger.error(f'Failed to process \'auth\' configuration. Exiting.')
		exit(1)

	logger.info(f'Attempting to add package \'{package_name}\' from source \'{source}\'.')

	pip_command = [
		sys.executable,
		'-m',
		'pip',
		'install',
		'--no-deps',
		'--target',
		packages_path,
		'--extra-index-url',
		authed_source,
		package_name if version == 'latest' else f'{package_name}=={version}',
	]

	pip_call = subprocess.call(pip_command)

	if pip_call != 0:
		logger.error('Last \'pip\' call failed. Check console for more details. Exiting.')
		exit(1)

	logger.info(
		f'Package installed. Attempting to test compatibility with API Level {api_level}.'
	)

	try:
		sys.path.insert(0, os.path.realpath('.'))
		sys.path.insert(0, packages_path)
		package = __import__(package_name)
	except:
		logger.error('Failed to load package to test compatibility. Exiting.')
		exit(1)

	if package.config.api_level != api_level:
		logger.error(
			f'App is using API Level {api_level}, but package is on API Level {package.config.api_level}.'
		)
		_packages_rm(package_name=package_name, confirm=False)

	logger.info(
		f'Package is compatible with app API Level. Attempting to install package requirements.'
	)

	requirements_path = os.path.join(package_path, 'requirements.txt')

	pip_command = [
		sys.executable,
		'-m',
		'pip',
		'install',
		'--user',
		'-r',
		requirements_path,
	]

	pip_call = subprocess.call(pip_command)

	if pip_call != 0:
		logger.error('Last \'pip\' call failed. Check console for more details.')

	logger.info('Attempting to update \'packages.json\'.')

	with open(os.path.realpath(os.path.join('.', 'packages.json')), 'r') as f:
		packages = json.loads(f.read())
		packages[package_name] = {'version': package.config.version, 'source': source}
		if auth:
			packages[package_name]['auth'] = auth

	with open(os.path.realpath(os.path.join('.', 'packages.json')), 'w') as f:
		f.write(json.dumps(packages))

	logger.info('Successfully updated \'packages.json\'.')
	logger.info(
		'Remember to check package docs for any \'vars\' you are required to add to your app.'
	)

	TESTING_COMPATIBILITY = False


def _packages_rm(*, package_name: str, confirm: bool = True):
	if confirm:
		confirmation = input(
			f'Are you sure you want to remove package \'{package_name}\'? [yN] '
		)
		if not len(confirmation) or confirmation.lower()[0] != 'y':
			logger.info(f'Cancelled removing package \'{package_name}\'. Exiting.')
			exit(0)

	global TESTING_COMPATIBILITY
	TESTING_COMPATIBILITY = True

	try:
		packages_path = os.path.realpath(os.path.join('.', 'packages'))
		package_path = os.path.realpath(os.path.join('.', 'packages', package_name))
		sys.path.insert(0, packages_path)
		package = __import__(package_name)
	except:
		logger.error(
			'Failed to load package to remove it Confirm package name is correct. Exiting.'
		)
		exit(1)

	logger.warning(f'Removing package \'{package_name}\'...')
	# [DOC] Handle removing files for Windows/NT when shutil.rmtree fails
	# [REF] https://stackoverflow.com/a/28476782/2393762
	def errorRemoveReadonly(func, path, exc):
		excvalue = exc[1]
		if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
			os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
			func(path)

	shutil.rmtree(package_path, ignore_errors=False, onerror=errorRemoveReadonly)
	shutil.rmtree(
		os.path.join(packages_path, f'{package_name}-{package.config.version}.dist-info'),
		ignore_errors=False,
		onerror=errorRemoveReadonly,
	)
	logger.info(f'Package \'{package_name}\' removed. Exiting.')
	exit(1)


def packages_audit(args: argparse.Namespace):
	import json

	logger.info(
		'Attempting to audit packages in \'nawah_pacakges.py\' against packages added to \'packages\' folder.'
	)

	app_path = os.path.realpath('.')
	packages_path = os.path.realpath(os.path.join('.', 'packages'))
	sys.path.insert(0, app_path)
	sys.path.append(packages_path)
	import nawah_app

	with open(os.path.join(app_path, 'packages.json')) as f:
		req_packages: Dict[str, Any] = json.loads(f.read())

	logger.info('Packages in \'nawah_pacakges.py\' are:')
	for package_name in req_packages.keys():
		logger.info(f'- {package_name}: {req_packages[package_name]}')

	logger.info('Attempting to check packages added in \'packages\'.')
	added_packages = {}
	for _, pkgname, ispkg in pkgutil.iter_modules([packages_path]):
		if not ispkg:
			continue
		logger.info(f'- Importing package: {pkgname}')
		package = __import__(pkgname, fromlist='*')
		added_packages[pkgname] = package.config.version
		logger.info(f'- Imported package with version: {package.config.version}')

	logger.info('Attempting to audit missing, extra, version-mismatching packages.')

	missing_packages = [
		package for package in req_packages if package not in added_packages.keys()
	]
	if missing_packages:
		logger.info(
			'Following packages are required by your app but not added to \'packages\':'
		)
		for package in missing_packages:
			logger.info(f'- {package}')
	else:
		logger.info('Great! Your app is not missing any of the required package.')

	extra_packages = [
		package
		for package in added_packages
		if package not in req_packages.keys() and package != nawah_app.config.default_package
	]
	if extra_packages:
		logger.info(
			'Following packages are added to \'packages\' but not required by your app:'
		)
		for package in extra_packages:
			logger.info(f'- {package}')
	else:
		logger.info('Great! Your app is not having any extra package.')

	mismatch_packages = [
		package
		for package in req_packages
		if package in added_packages.keys()
		and added_packages[package] != req_packages[package]['version']
	]
	if mismatch_packages:
		logger.warning(
			'Following packages are having mismatch between required and added version:'
		)
		for package in mismatch_packages:
			logger.info(
				f'- {package} requires version \'{req_packages[package]}\' but \'{added_packages[package]}\' is added'
			)
	else:
		logger.info('Great! Your app is not having any version-mismatching package.')


def generate_ref(args: argparse.Namespace):
	# [DOC] Update Config with Nawah framework CLI args
	from nawah.config import Config

	Config.generate_ref = True
	launch(args=args, custom_launch='generate_ref')


def generate_models(args: argparse.Namespace):
	# [DOC] Update Config with Nawah framework CLI args
	from nawah.config import Config

	Config.generate_models = True
	launch(args=args, custom_launch='generate_models')
