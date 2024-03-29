import nawah
from nawah.config import Config
from nawah.classes import L10N, ATTR

import logging, sys, os.path, pkgutil, inspect, re

from ._validate import validate_attr
from ._config import _process_config

logger = logging.getLogger('nawah')


async def _import_modules():
	sys.path.append(os.path.join(nawah.__path__[0], 'packages'))
	sys.path.append(os.path.join(Config._app_path, 'packages'))

	# [DOC] Iterate over packages in modules folder
	for _, pkgname, ispkg in pkgutil.iter_modules(
		[
			os.path.join(nawah.__path__[0], 'packages'),
			os.path.join(Config._app_path, 'packages'),
		]
	):
		if not ispkg:
			continue

		logger.debug(f'Importing package: {pkgname}')

		# [DOC] Load package and attempt to load config
		package = __import__(pkgname, fromlist='*')
		_process_config(config=package.config, pkgname=pkgname)

		# [DOC] Add package to loaded packages dict
		Config.modules_packages[pkgname] = []

		# [DOC] Iterate over python modules in package
		package_prefix = package.__name__ + '.'
		for _, modname, ispkg in pkgutil.iter_modules(package.__path__, package_prefix):
			# [DOC] Iterate over Python modules in package
			module = __import__(modname, fromlist='*')
			# [DOC] For __l10n__ Python module, extract all l10n dicts and skip processing
			if modname.endswith('__l10n__'):
				for l10n_name in dir(module):
					if type(getattr(module, l10n_name)) == L10N:
						if l10n_name not in Config.l10n.keys():
							Config.l10n[l10n_name] = {}
						Config.l10n[l10n_name].update(getattr(module, l10n_name))
				continue

			for clsname in dir(module):
				# [DOC] Confirm class is subclass of BaseModule
				if (
					clsname != 'BaseModule'
					and inspect.isclass(getattr(module, clsname))
					and getattr(getattr(module, clsname), '_nawah_module', False)
				):
					# [DOC] Deny loading Nawah-reserved named Nawah modules
					if clsname.lower() in ['conn', 'heart', 'watch']:
						logger.error(
							f'Module with Nawah-reserved name \'{clsname.lower()}\' was found. Exiting.'
						)
						exit(1)
					# [DOC] Load Nawah module and assign module_name attr
					cls = getattr(module, clsname)
					module_name = re.sub(r'([A-Z])', r'_\1', clsname[0].lower() + clsname[1:]).lower()
					# [DOC] Deny duplicate Nawah modules names
					if module_name in Config.modules.keys():
						logger.error(f'Duplicate module name \'{module_name}\'. Exiting.')
						exit(1)
					# [DOC] Add module to loaded modules dict
					Config.modules[module_name] = cls()
					Config.modules_packages[pkgname].append(module_name)

	# [DOC] Update User, Session modules with populated attrs
	Config.modules['user'].attrs.update(Config.user_attrs)
	if (
		sum(1 for attr in Config.user_settings.keys() if attr in Config.user_attrs.keys())
		!= 0
	):
		logger.error(
			'At least on attr from \'user_settings\' is conflicting with an attr from \'user_attrs\'. Exiting.'
		)
		exit(1)
	Config.modules['user'].defaults['locale'] = Config.locale
	for attr in Config.user_attrs.keys():
		Config.modules['user'].unique_attrs.append(attr)
		Config.modules['user'].attrs[f'{attr}_hash'] = ATTR.STR()
		Config.modules['session'].methods['auth'].doc_args.append(
			{
				'hash': ATTR.STR(),
				attr: Config.user_attrs[attr],
				'groups': ATTR.LIST(list=[ATTR.ID()]),
			}
		)
		Config.modules['session'].methods['auth'].doc_args.append(
			{'hash': ATTR.STR(), attr: Config.user_attrs[attr]}
		)

	# [DOC] Attempt to validate all packages required vars (via vars_types Config Attr) are met
	for var in Config.vars_types.keys():
		if var not in Config.vars.keys():
			logger.error(
				f'Package \'{Config.vars_types[var]["package"]}\' requires \'{var}\' Var, but not found in App Config. Exiting.'
			)
			exit(1)
		try:
			await validate_attr(
				mode='create',
				attr_name=var,
				attr_type=Config.vars_types[var]['type'],
				attr_val=Config.vars[var],
			)
		except:
			logger.error(
				f'Package \'{Config.vars_types[var]["package"]}\' requires \'{var}\' Var of type \'{Config.vars_types[var]["type"]._type}\', but validation failed. Exiting.'
			)
			exit(1)

	# [DOC] Call update_modules, effectively finalise initialising modules
	for module in Config.modules.values():
		module._initialise()
