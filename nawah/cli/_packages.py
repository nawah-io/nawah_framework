from nawah import __version__

from typing import Dict, Any, Optional

import argparse, os, sys, logging, json, subprocess, shutil, pkgutil, traceback

logger = logging.getLogger('nawah')


def packages_install(args: argparse.Namespace):
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
	from . import _set_testing
	import json

	_set_testing(True)
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

		_set_testing(False)

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
	except Exception as e:
		logger.error(traceback.format_exc())
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

	_set_testing(False)


def _packages_rm(*, package_name: str, confirm: bool = True):
	from . import _set_testing

	if confirm:
		confirmation = input(
			f'Are you sure you want to remove package \'{package_name}\'? [yN] '
		)
		if not len(confirmation) or confirmation.lower()[0] != 'y':
			logger.info(f'Cancelled removing package \'{package_name}\'. Exiting.')
			exit(0)

	_set_testing(True)

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
