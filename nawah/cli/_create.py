from nawah import __version__

from typing import Dict, Any

import argparse, logging, os, sys, re, json, tarfile, tempfile, urllib.request, subprocess, random, string

logger = logging.getLogger('nawah')
__api_level__ = '.'.join(__version__.split('.')[:-1])


def create(args: argparse.Namespace):
	global os, subprocess

	if args.app_name == 'nawah_app':
		logger.error(
			'Value for \'app_name\' CLI Arg is invalid. Name can\'t be \'nawah_app\''
		)
		exit(1)
	elif not re.match(r'^[a-z][a-z0-9_]+$', args.app_name):
		logger.error(
			'Value for \'app_name\' CLI Arg is invalid. Name should have only small letters, numbers, and underscores.'
		)
		exit(1)

	app_path = os.path.realpath(os.path.join(args.app_path, args.app_name))
	progress_path = os.path.realpath(
		os.path.join(args.app_path, args.app_name, 'progress.json')
	)

	progress = None

	if os.path.exists(app_path):
		logger.info(
			'Specified \'app_name\' already existing in \'app_path\'. Attempting to check for earlier progress.'
		)
		if os.path.exists(progress_path):
			logger.info('File \'progress.json\' found. Attempting to process it.')
			try:
				with open(progress_path, 'r') as progress_file:
					progress_config = json.loads(progress_file.read())
					progress = progress_config['step']
					app_config = progress_config['config']
			except Exception as e:
				logger.error(
					'An exception occurred while attempting to process file \'progress.json\'.'
				)
				logger.error(f'Exception details: {e}')
				logger.error('Exiting.')
				exit(1)
		else:
			logger.error('File \'progress.json\' was not found. Exiting.')
			exit(1)

	# [DOC] Populating app_config
	if not progress:
		app_config = _create_step_config(args=args)
		logger.info('This will create an app with the following config:')
		for config_attr, config_set in app_config.items():
			logger.info(f'- {config_attr}: \'{config_set[1]}\'')
	else:
		logger.info('Continuing to create app with loaded progress config:')
		for config_attr, config_set in app_config.items():
			logger.info(f'- {config_attr}: \'{config_set[1]}\'')

	# [DOC] Create app workspace
	if not progress:
		cli_dir, cli_filename = os.path.split(__file__)
		template_archive = os.path.join(cli_dir, 'template.tar.gz')

		logger.info(f'Attempting to extract template archive to: {app_path}')
		with tarfile.open(name=template_archive, mode='r:gz') as archive:
			archive.extractall(path=app_path)
		logger.info('Template archive extracted successfully!')

	if not progress or progress == 1:
		progress = None
		logger.info('Attempting to config app template for new Nawah app.')
		try:
			with open(
				os.path.realpath(os.path.join(args.app_path, args.app_name, 'nawah_app.py')), 'r'
			) as f:
				nawah_app_file = f.read()
			with open(
				os.path.realpath(os.path.join(args.app_path, args.app_name, 'nawah_app.py')), 'w'
			) as f:
				nawah_app_file = nawah_app_file.replace('__PROJECT_NAME__', args.app_name, 2)
				for config_set in app_config.values():
					nawah_app_file = nawah_app_file.replace(config_set[0], config_set[1], 1)
				f.write(nawah_app_file)
		except Exception as e:
			_dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=3)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	if not progress or progress == 2:
		progress = None
		try:
			gitignore_path = os.path.realpath(
				os.path.join(args.app_path, args.app_name, '.gitignore')
			)
			with open(gitignore_path, 'r') as f:
				gitignore_file = f.read()
			with open(gitignore_path, 'w') as f:
				f.write(gitignore_file.replace('PROJECT_NAME', args.app_name, 1))
		except Exception as e:
			_dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=4)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	if not progress or progress == 3:
		progress = None
		try:
			readme_path = os.path.realpath(
				os.path.join(args.app_path, args.app_name, 'README.md')
			)
			with open(readme_path, 'w') as f:
				f.write(
					f'''# {args.app_name}
This Nawas app project was created with Nawah CLI v{__version__}, with API Level {__api_level__}.'''
				)
		except Exception as e:
			_dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=6)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	if not progress or progress == 4:
		progress = None
		try:
			os.rename(
				os.path.realpath(
					os.path.join(args.app_path, args.app_name, 'packages', 'PROJECT_NAME')
				),
				os.path.realpath(
					os.path.join(args.app_path, args.app_name, 'packages', args.app_name)
				),
			)
		except Exception as e:
			_dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=7)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	if not progress or progress == 5:
		progress = None
		try:
			test_integration_path = os.path.realpath(
				os.path.join(
					args.app_path, args.app_name, 'tests', 'integration', 'test_integration.py'
				)
			)
			with open(test_integration_path, 'r') as f:
				test_integration_file = f.read()
			with open(test_integration_path, 'w') as f:
				f.write(test_integration_file.replace('PROJECT_NAME', args.app_name.upper(), 1))
		except Exception as e:
			_dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=4)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	if not progress or progress == 6:
		progress = None
		try:
			for unit_test_filename in ['test_read.py', 'test_create.py']:
				test_unit_path = os.path.realpath(
					os.path.join(
						args.app_path, args.app_name, 'tests', 'unit', 'doc', unit_test_filename
					)
				)
				with open(test_unit_path, 'r') as f:
					test_unit_file = f.read()
				with open(test_unit_path, 'w') as f:
					f.write(test_unit_file.replace('PROJECT_NAME', args.app_name, 1))
		except Exception as e:
			_dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=4)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	logger.info(f'Congrats! Your Nawah app {args.app_name} is successfully created!')


def _create_step_config(*, args: argparse.Namespace):
	app_config = {
		# [REF]: https://stackoverflow.com/a/47073723/2393762
		'admin_password': [
			'__ADMIN_PASSWORD__',
			''.join(
				[
					random.choice(string.ascii_letters + string.digits + string.punctuation)
					for n in range(18)
				]
			)
			.replace('\'', '^')
			.replace('\\', '/'),
		],
		'anon_token_suffix': [
			'__ANON_TOKEN_SUFFIX__',
			''.join([random.choice(string.digits) for n in range(24)]),
		],
	}

	envs_defaults = {
		'dev_local': 'mongodb://localhost',
		'dev_server': 'mongodb://admin:admin@mongodb',
		'prod': 'mongodb://admin:admin@prod',
	}

	if not args.default_config:
		# [DOC] Allow user to specify custom config per the following Config Attrs
		logger.info(
			'Not detected \'default-config\' CLI Arg. Attempting to create Nawah app with custom Config.'
		)
		logger.info(
			'If you would like to have app created with default config, stop the process, and re-run Nawah CLI with \'default-config\' CLI Arg.'
		)
		# [DOC] envs: data_server
		logger.info(
			'\'envs\' Config Attr provides environment-specific configuration. You will be required to specify \'data_server\' for each of the default available Nawah environments, namely \'dev_local\', \'dev_server\', and \'prod\'.'
		)
		for env in envs_defaults.keys():
			while True:
				config_attr_val = input(
					f'\n> What would be the value for \'data_server\' Config Attr for environment \'{env}\'; The connection string to connect to your MongoDB host? [{envs_defaults[env]}]\n- '
				)
				if not config_attr_val:
					logger.info(
						f'Setting \'data_server\' Config Attr for environment \'{env}\' to default \'{envs_defaults[env]}\'.'
					)
					app_config[f'{env}:data_server'] = [
						f'__{env.upper()}_DATA_SERVER__',
						(config_attr_val := envs_defaults[env]),
					]
				else:
					logger.info(
						f'Setting \'data_server\' Config Attr for environment \'{env}\' to: \'{config_attr_val}\'.'
					)
					app_config[f'{env}:data_server'] = [
						f'__{env.upper()}_DATA_SERVER__',
						config_attr_val,
					]
				break
		# [DOC] env
		while True:
			config_attr_val = input(
				'\n> What would be the value for \'env\'; Config Attr for default environnement to be used when invoking Nawah CLI \'launch\' command? [$__env.ENV]\n- '
			)
			if not config_attr_val:
				logger.info('Setting \'env\' Config Attr to default: \'$__env.ENV\'.')
				app_config['data_name'] = ['__ENV__', (config_attr_val := '$__env.ENV')]
				break
			elif config_attr_val not in list(envs_defaults.keys()) and not re.match(
				r'^\$__env\.[A-Za-z_]+$', config_attr_val
			):
				logger.error(
					'\'env\' Config Attr can only be one of the environments names defined in \'envs\' Config Attr, or a valid Env Variable.'
				)
			else:
				logger.info(f'Setting \'env\' Config Attr to: \'{config_attr_val}\'.')
				app_config['env'] = ['__ENV__', config_attr_val]
				break
		# [DOC] data_name
		while True:
			config_attr_val = input(
				'\n> What would be the value for \'data_name\'; Config Attr for database name to be created on \'data_server\'? [nawah_data]\n- '
			)
			if not config_attr_val:
				logger.info('Setting \'data_name\' Config Attr to default: \'nawah_data\'.')
				app_config['data_name'] = ['__DATA_NAME__', (config_attr_val := 'nawah_data')]
				break
			elif not re.match(r'^[a-zA-Z0-9\-_]+$', config_attr_val):
				logger.error(
					'\'data_name\' Config Attr can\'t have special characters other than underscores and hyphens in it.'
				)
			else:
				logger.info(f'Setting \'data_name\' Config Attr to: \'{config_attr_val}\'.')
				app_config['data_name'] = ['__DATA_NAME__', config_attr_val]
				break
		# [DOC] locales
		while True:
			config_attr_val = input(
				'\n> What would be the comma-separated, language_COUNTRY-formatted value for \'locales\'; Config Attr for localisations of your app? [ar_AE, en_AE]\n- '
			)
			if not config_attr_val:
				logger.info('Setting \'locales\' Config Attr to default: \'ar_AE, en_AE\'.')
				locales = ['ar_AE', 'en_AE']
				app_config['locales'] = ['__LOCALES__', (config_attr_val := 'ar_AE\', \'en_AE')]
				break
			else:
				try:
					locales = [
						re.match(r'^([a-z]{2}_[A-Z]{2})$', locale.strip()).group(0)  # type: ignore
						for locale in config_attr_val.split(',')
					]
					logger.info(f'Setting \'locales\' Config Attr to: \'{config_attr_val}\'.')
					app_config['locales'] = ['__LOCALES__', '\', \''.join(locales)]
					break
				except:
					logger.error('An exception occurred while attempting to process value provided.')
					logger.error(
						'\'locales\' Config Attr value should be provided as comma-separated, language_COUNTRY-formatted list of localisations.'
					)
		# [DOC] locale
		while True:
			config_attr_val = input(
				'\n> What would be the value for \'locale\'; Config Attr for default localisation of your app? [first value of \'locales\' Config Attr]\n- '
			)
			if not config_attr_val:
				logger.info(
					f'Setting \'locale\' Config Attr to first value of \'locales\' Config Attr: \'{locales[0]}\'.'
				)
				app_config['locale'] = ['__LOCALE__', (config_attr_val := locales[0])]
				break
			elif config_attr_val not in locales:
				logger.error(
					'\'locale\' Config Attr can only be one of the localisations defined in \'locales\' Config Attr.'
				)
			else:
				logger.info(f'Setting \'locale\' Config Attr to: \'{config_attr_val}\'.')
				app_config['locale'] = ['__LOCALE__', config_attr_val]
				break
		# [DOC] admin_doc: email
		while True:
			config_attr_val = input(
				'\n> What would be the value for \'admin_doc\'.\'email\'; Config Attr? [admin@app.nawah.localhost]\n- '
			)
			if not config_attr_val:
				logger.info(
					'Setting \'admin_doc\'.\'email\' Config Attr to default: \'admin@app.nawah.localhost\'.'
				)
				app_config['admin_doc:email'] = [
					'__ADMIN_DOC_EMAIL__',
					(config_attr_val := 'admin@app.nawah.localhost'),
				]
				break
			elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', config_attr_val):
				logger.error(
					'\'admin_doc\'.\'email\' Config Attr value is not a valid email address.'
				)
			else:
				logger.info(
					f'Setting \'admin_doc\'.\'email\' Config Attr to: \'{config_attr_val}\'.'
				)
				app_config['admin_doc:email'] = ['__ADMIN_DOC_EMAIL__', config_attr_val]
				break
	else:
		for env in envs_defaults.keys():
			app_config[f'{env}:data_server'] = [
				f'__{env.upper()}_DATA_SERVER__',
				envs_defaults[env],
			]
		app_config.update(
			{
				'env': ['__ENV__', '$__env.ENV'],
				'data_name': ['__DATA_NAME__', 'nawah_data'],
				'locales': ['__LOCALES__', '\', \''.join(['ar_AE', 'en_AE'])],
				'locale': ['__LOCALE__', 'ar_AE'],
				'admin_doc:email': ['__ADMIN_DOC_EMAIL__', 'admin@app.nawah.localhost'],
			}
		)

	return app_config


def _dump_progress(
	*, args: argparse.Namespace, app_config: Dict[Any, Any], progress_path: str, step: int
):
	with open(progress_path, 'w') as progress_file:
		progress_file.write(
			json.dumps(
				{
					'step': step,
					'args': {
						'app_path': args.app_path,
						'app_name': args.app_name,
					},
					'config': app_config,
				}
			)
		)
