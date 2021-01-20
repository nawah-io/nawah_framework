from nawah import __version__

from typing import Literal, Any

import argparse, os, logging, datetime, sys, subprocess, asyncio, traceback, shutil, urllib.request, re, tarfile, string, random, tempfile, pkgutil

logger = logging.getLogger('nawah')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s  [%(levelname)s]  %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.INFO)


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

	parser_install = subparsers.add_parser(
		'install_deps', help='Install dependencies of Nawah app'
	)
	parser_install.set_defaults(func=install_deps)

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

	parser_packages_add = packages_subparser.add_parser(
		'add', help='Add package to Nawah app'
	)
	parser_packages_add.set_defaults(func=packages_add)
	parser_packages_add.add_argument(
		'package', help='Package identifier/URI/path to add to Nawah app'
	)
	parser_packages_add.add_argument(
		'--source',
		help='Package source [default nawah]',
		choices=['nawah', 'local'],
		default='nawah',
	)

	parser_packages_rm = packages_subparser.add_parser(
		'rm', help='Remove package from Nawah app'
	)
	parser_packages_rm.set_defaults(func=packages_rm)
	parser_packages_rm.add_argument(
		'package_name', help='Package name to remove from Nawah app'
	)

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


def install_deps(args: argparse.Namespace):
	global sys, os, subprocess
	# [DOC] Change logging level to debug
	logger.setLevel(logging.DEBUG)
	logger.debug('Beginning to install dependencies')
	# [DOC] Create standard call command list
	pip_command = [sys.executable, '-m', 'pip', 'install', '--user', '-r']

	dirs = [
		d
		for d in os.listdir(os.path.join('.', 'packages'))
		if os.path.isdir(os.path.join('.', 'packages', d))
	]
	# [DOC] Iterate over packages to find requirements.txt files
	for package in dirs:
		logger.debug(f'Checking package \'{package}\' for \'requirements.txt\' file.')
		if os.path.exists(os.path.join('.', 'packages', package, 'requirements.txt')):
			logger.debug(
				'File \'requirements.txt\' found! Attempting to install package dependencies.'
			)
			pip_call = subprocess.call(
				pip_command + [os.path.join('.', 'packages', package, 'requirements.txt')]
			)
			if pip_call != 0:
				logger.error('Last \'pip\' call failed. Check console for more details. Exiting.')
				exit(1)


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

	try:
		try:
			sys.path.append('.')
			nawah_app = __import__('nawah_app')
			app_config = nawah_app.config
			Config._app_packages = nawah_app.packages
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
	except Exception:
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


def packages_add(args: argparse.Namespace):
	logger.info('Checking packages conflicts.')
	package_name = args.package
	package_path = os.path.realpath(os.path.join('.', 'packages', package_name))

	if os.path.exists(package_path):
		logger.error(f'Package \'{package_name}\' already exists in app. Exiting.')
		exit(1)

	api_level = '.'.join(__version__.split('.')[:2])

	if args.source == 'nawah':
		logger.info(f'Attempting to add package from Nawah source.')
		package_root = f'{package_name}-APIv{api_level}'
		package_url = (
			f'https://github.com/nawah-io/{package_name}/archive/APIv{api_level}.tar.gz'
		)
		logger.info(f'Attempting to download package from: {package_url}')
		# [REF] https://stackoverflow.com/a/7244263/2393762
		package_archive, _ = urllib.request.urlretrieve(package_url)
		logger.info('Package archive downloaded successfully!')

	elif args.source == 'local':
		logger.info(f'Attempting to add package from local source: \'{args.package}\'.')
		try:
			source_path = os.path.realpath(args.package)
			package_name = package_root = os.path.basename(source_path)
			sys.path.insert(0, source_path)
			package = __import__('__init__')
		except:
			logger.error('Failed to load package. Exiting.')
			exit(1)

		logger.info(f'Attempting to check package API Level matching \'{api_level}\'.')
		if package.config.api_level != api_level:
			logger.error(
				f'Package is using incompatible API Level \'{package.config.api_level}\'. Exiting.'
			)
			exit(1)

		logger.info('Attempting to archive package from local source.')
		temp_package_archive = tempfile.NamedTemporaryFile(mode='w')
		# [REF] https://stackoverflow.com/a/17081026
		# [REF] https://stackoverflow.com/a/16000963
		with tarfile.open(temp_package_archive.name, 'w:gz') as archive:
			archive.add(
				source_path,
				arcname=package_name,
				filter=lambda member: None if '.git/' in member.name else member,
			)
		logger.info('Package archive created successfully!')
		package_archive = temp_package_archive.name

	def archive_members(
		*, archive: tarfile.TarFile, root_path: str, search_path: str = None
	):
		l = len(f'{root_path}/')
		for member in archive.getmembers():
			if member.path.startswith(f'{root_path}/{search_path or ""}'):
				member.path = member.path[l:]
				yield member

	logger.info('Attempting to extract package archive to Nawah app \'packages\'.')
	with tarfile.open(name=package_archive, mode='r:gz') as archive:
		archive.extractall(
			path=package_path,
			members=archive_members(archive=archive, root_path=package_root),
		)
	logger.info('Package archive extracted successfully!')

	logger.info('Attempting to update \'nawah_packages.py\'.')

	sys.path.insert(0, os.path.realpath('.'))
	sys.path.insert(0, package_path)
	package = __import__('__init__')
	import nawah_packages

	packages = nawah_packages.packages
	packages[package_name] = package.config.version
	with open(os.path.realpath(os.path.join('.', 'nawah_packages.py')), 'w') as f:
		packages_string = ''
		for package in packages.keys():
			packages_string += f'    \'{package}\': \'{packages[package]}\',\n'
		f.write(f'packages = {{\n{packages_string}}}\n')
	logger.info('Successfully updated \'nawah_packages.py\'.')
	logger.info(
		'Remember to check package docs for any \'vars\' you are required to add to your app.'
	)


def packages_rm(args: argparse.Namespace):
	logger.warning(
		'Due to compatibility issues you will be required to manually remove the package from \'packages\' and \'nawah_packages.py\'. Exiting.'
	)
	exit(1)


def packages_audit(args: argparse.Namespace):
	logger.info(
		'Attempting to audit packages in \'nawah_pacakges.py\' against packages added to \'packages\' folder.'
	)

	app_path = os.path.realpath('.')
	packages_path = os.path.realpath(os.path.join('.', 'packages'))
	sys.path.insert(0, app_path)
	sys.path.append(packages_path)
	import nawah_app, nawah_packages

	req_packages = nawah_packages.packages
	logger.info('Packages in \'nawah_pacakges.py\' are:')
	for package in req_packages.keys():
		logger.info(f'- {package}: {req_packages[package]}')

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
		and added_packages[package] != req_packages[package]
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
