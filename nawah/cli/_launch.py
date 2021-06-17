from nawah import __version__

from typing import Literal

import argparse, os, sys, logging, asyncio, datetime, traceback

from ._logging import logger, handler, formatter


def launch(
	args: argparse.Namespace,
	custom_launch: Literal['test', 'generate_ref', 'generate_models'] = None,
):

	# [DOC] Update Config with Nawah CLI args
	from nawah.config import Config
	from nawah.utils import _process_config

	Config._nawah_version = __version__
	if custom_launch not in ['generate_ref', 'generate_models']:
		Config.env = args.env
	if not custom_launch:
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
		file_handler = logging.FileHandler(
			filename=os.path.join(
				'.',
				'logs',
				f'{datetime.datetime.utcnow().strftime("%d-%b-%Y")}.log',
			)
		)
		file_handler.setFormatter(formatter)
		logger.addHandler(file_handler)
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

		# [DOC] Process other app config attrs as PACKAGE_CONFIG
		_process_config(config=app_config)
	except:
		logger.error(
			'An unexpected exception happened while attempting to process Nawah app. Exception details:'
		)
		logger.error(traceback.format_exc())
		logger.error('Exiting.')
		exit(1)

	if not custom_launch:
		asyncio.run(run_app())
	elif custom_launch == 'generate_ref':

		async def _():
			from nawah.utils import _import_modules, _generate_ref

			await _import_modules()
			_generate_ref()

		asyncio.run(_())
	elif custom_launch == 'generate_models':

		async def _():
			from nawah.utils import _import_modules, _generate_models

			await _import_modules()
			_generate_models()

		asyncio.run(_())
