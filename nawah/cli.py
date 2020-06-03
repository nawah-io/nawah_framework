from nawah import __version__

from typing import Literal, Any

import argparse, os, logging, datetime, sys, subprocess, asyncio, traceback, shutil, urllib.request, re, tarfile, string, random

logger = logging.getLogger('nawah')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s  [%(levelname)s]  %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.INFO)


def nawah_cli():
	global sys, os

	if sys.version_info.major != 3 or sys.version_info.minor != 8:
		print('Nawah framework CLI can only run with Python3.8. Exiting.')
		exit()

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
	parser_install.add_argument(
		'app_path',
		type=str,
		nargs='?',
		help='Path of the app to discover its dependencies. [default .]',
		default='.',
	)

	parser_launch = subparsers.add_parser('launch', help='Launch Nawah app')
	parser_launch.set_defaults(func=launch)
	parser_launch.add_argument(
		'app_path',
		type=str,
		nargs='?',
		help='Path of the app to discover its dependencies. [default .]',
		default='.',
	)
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
	parser_test.add_argument(
		'app_path',
		type=str,
		nargs='?',
		help='Path of the app to discover its dependencies. [default .]',
		default='.',
	)
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

	parser_ref = subparsers.add_parser(
		'generate_ref', help='Generate Nawah app reference'
	)
	parser_ref.set_defaults(func=generate_ref)
	parser_ref.add_argument(
		'app_path',
		type=str,
		nargs='?',
		help='Path of the app to discover its dependencies. [default .]',
		default='.',
	)
	parser_ref.add_argument('--debug', help='Enable debug mode', action='store_true')

	args = parser.parse_args()
	if args.command:
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
		for d in os.listdir(os.path.join(args.app_path, 'packages'))
		if os.path.isdir(os.path.join(args.app_path, 'packages', d))
	]
	# [DOC] Iterate over packages to find requirements.txt files
	for package in dirs:
		logger.debug(f'Checking package \'{package}\' for \'requirements.txt\' file.')
		if os.path.exists(
			os.path.join(args.app_path, 'packages', package, 'requirements.txt')
		):
			logger.debug(
				'File \'requirements.txt\' found! Attempting to install package dependencies.'
			)
			pip_call = subprocess.call(
				pip_command
				+ [os.path.join(args.app_path, 'packages', package, 'requirements.txt')]
			)
			if pip_call != 0:
				logger.error(
					'Last \'pip\' call failed. Check console for more details. Exiting.'
				)
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
	if custom_launch != 'generate_ref':
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
		if not os.path.exists(os.path.join(args.app_path, 'logs')):
			os.makedirs(os.path.join(args.app_path, 'logs'))
		handler = logging.FileHandler(
			filename=os.path.join(
				args.app_path,
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
			sys.path.append(args.app_path)
			nawah_app = __import__('nawah_app')
			app_config = nawah_app.config
			Config._app_packages = getattr(nawah_app, 'packages', None)
		except ModuleNotFoundError:
			logger.error(
				f'No \'nawah_app.py\' file found in specified path: \'{args.app_path}\'. Exiting.'
			)
			exit()
		except AttributeError:
			logger.error(
				f'File \'nawah_app.py\' was found but it doesn\'t have \'config\' method. Exiting.'
			)
			exit()
		logger.info(
			f'Found app \'{app_config.name} (v{app_config.version})\'. Attempting to load App Config.'
		)
		Config._app_name = app_config.name
		Config._app_version = app_config.version
		Config._app_path = os.path.realpath(args.app_path)
		# [DOC] Read app_config and update Config accordingly
		# [DOC] Check envs, env
		if custom_launch not in ['generate_ref'] and app_config.envs:
			if not args.env and not app_config.env:
				logger.error(
					'App Config Attr \'envs\' found, but no \'env\' App Config Attr, or CLI Attr were defined.'
				)
				exit()
			if args.env:
				if args.env in app_config.envs.keys():
					logger.info(
						f'Setting \'env\' Config Attr to \'env\' CLI Arg value \'{args.env}\''
					)
				else:
					logger.error(
						f'Found value \'{args.env}\' for \'env\' CLI Arg, but not defined in \'envs\' App Config Attr. Exiting.'
					)
					exit()
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
						logger.error(
							f'No value found for Env Variable \'{env_env_var}\'. Exiting.'
						)
						exit()
				else:
					logger.error(
						f'Found value \'{args.env}\' for \'env\' CLI Arg, but not defined in \'envs\' App Config Attr. Exiting.'
					)
					exit()
			logger.info(
				f'Beginning to extract Config Attrs defined in selected \'env\', \'{Config.env}\', to App Config Attrs.'
			)
			for config_attr in dir(app_config.envs[Config.env]):
				if (
					config_attr.startswith('__')
					or getattr(app_config.envs[Config.env], config_attr) == None
				):
					continue
				logger.info(
					f'Extracting \'{config_attr}\' Config Attr to App Config Attr'
				)
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
					exit()
			else:
				logger.info('Found \'port\' App Config Attr. Attempting to process it.')
				if type(app_config.port) == int:
					Config.port = app_config.port
					logger.info(f'Setting \'port\' Config Attr to \'{Config.port}\'.')
				elif type(app_config.port) == str and app_config.port.startswith(
					'$__env.'
				):
					logger.info(
						'Found Env Variable for \'port\' App Config Attr. Attempting to process it.'
					)
					port_env_var = app_config.port.replace('$__env.', '')
					port = os.getenv(port_env_var)
					if port:
						logger.info(
							f'Setting \'port\' Config Attr to Env Variable \'{port_env_var}\' value \'{port}\'.'
						)
						Config.port = port
					else:
						logger.error(
							f'No value found for Env Variable \'{port_env_var}\'. Exiting.'
						)
						exit()
				else:
					logger.error(
						f'Invalid value type for \'port\' Config Attr with value \'{app_config.port}\'. Exiting.'
					)
					exit()
		# [DOC] Check debug Config Attr
		if app_config.debug:
			if args.debug:
				logger.info(
					f'Ignoring \'debug\' App Config Attr in favour of \'debug\' CLI Arg with value \'{args.debug}\'.'
				)
				Config.debug = args.debug
			else:
				logger.info(
					'Found \'debug\' App Config Attr. Attempting to process it.'
				)
				if type(app_config.debug) == bool:
					Config.debug = app_config.debug
					logger.info(f'Setting \'debug\' Config Attr to \'{Config.debug}\'.')
				elif type(app_config.debug) == str and app_config.debug.startswith(
					'$__env.'
				):
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
					exit()
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
					exit()
		# [TODO] Implement realm APP Config Attr checks
		# [DOC] Process other app config attrs as PACKAGE_CONFIG
		process_config(config=app_config)
	except Exception:
		logger.error(
			'An unexpected exception happened while attempting to process Nawah app. Exception details:'
		)
		logger.error(traceback.format_exc())
		logger.error('Exiting.')
		exit()

	asyncio.run(run_app())


def test(args: argparse.Namespace):
	# [DOC] Update Config with Nawah framework CLI args
	from nawah.config import Config

	Config.test = args.test_name
	Config.test_skip_flush = args.skip_flush
	Config.test_force = args.force
	Config.test_env = args.use_env
	Config.test_breakpoint = args.breakpoint
	launch(args=args, custom_launch='test')


def generate_ref(args: argparse.Namespace):
	# [DOC] Update Config with Nawah framework CLI args
	from nawah.config import Config

	Config.generate_ref = True
	launch(args=args, custom_launch='generate_ref')

