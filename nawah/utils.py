from nawah.classes import (
	NAWAH_DOC,
	ATTR,
	ATTR_MOD,
	EXTN,
	PERM,
	DictObj,
	BaseModel,
	Query,
	NAWAH_QUERY,
	L10N,
	NAWAH_MODULE,
	NAWAH_ENV,
	ATTRS_TYPES,
	InvalidAttrTypeException,
	CACHE,
	ANALYTIC
)
from nawah.enums import Event, NAWAH_VALUES, LOCALE_STRATEGY

from typing import Dict, Union, Literal, List, Tuple, Callable, TypedDict, Any
from bson import ObjectId, binary

import logging, pkgutil, inspect, re, datetime, time, math, random, copy, os, sys, asyncio

logger = logging.getLogger('nawah')


def nawah_module(
	*,
	collection: Union[str, bool] = None,
	proxy: str = None,
	attrs: Dict[str, ATTR] = None,
	diff: Union[bool, ATTR_MOD] = None,
	defaults: Dict[str, Any] = None,
	unique_attrs: List[str] = None,
	extns: Dict[str, EXTN] = None,
	privileges: List[str] = None,
	methods: TypedDict(
		'METHODS',
		permissions=List[PERM],
		query_args=Dict[str, Union[ATTR, ATTR_MOD]],
		doc_args=Dict[str, Union[ATTR, ATTR_MOD]],
		get_method=bool,
		post_method=bool,
		watch_method=bool,
	) = None,
	cache: List[CACHE] = None,
	analytics: List[ANALYTIC] = None,
) -> Callable[[Any], NAWAH_MODULE]:
	def nawah_module_decorator(cls):
		from nawah.config import Config

		cls.collection = collection
		cls.proxy = proxy
		cls.attrs = attrs
		cls.diff = diff
		cls.defaults = defaults
		cls.unique_attrs = unique_attrs
		cls.extns = extns
		cls.privileges = privileges
		cls.methods = methods
		cls.cache = cache
		cls.analytics = analytics
		
		cls._instance = cls()

		pkgname = str(cls).split('.')[0].split('\'')[-1]
		clsname = str(cls).split('.')[-1].split('\'')[0]
		# [DOC] Deny loading Nawah-reserved named Nawah modules
		if clsname.lower() in ['conn', 'heart', 'watch']:
			logger.error(
				f'Module with Nawah-reserved name \'{clsname.lower()}\' was found. Exiting.'
			)
			exit(1)
		# [DOC] Load Nawah module and assign module_name attr
		module_name = re.sub(r'([A-Z])', r'_\1', clsname[0].lower() + clsname[1:]).lower()
		# [DOC] Deny duplicate Nawah modules names
		if module_name in Config.modules.keys():
			logger.error(f'Duplicate module name \'{module_name}\'. Exiting.')
			exit(1)
		# [DOC] Add module to loaded modules dict
		Config.modules[module_name] = cls._instance
		Config.modules_packages[pkgname].append(module_name)
		breakpoint()
		def wrapper():
			return cls._instance

		return wrapper
	return nawah_module_decorator



async def import_modules():
	import nawah
	from nawah.base_module import BaseModule
	from nawah.config import Config, process_config
	from nawah.test import TEST

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
		process_config(config=package.config, pkgname=pkgname)

		# [DOC] Add package to loaded packages dict
		Config.modules_packages[pkgname] = []

		# [DOC] Iterate over python modules in package
		package_prefix = package.__name__ + '.'
		for _, modname, ispkg in pkgutil.iter_modules(package.__path__, package_prefix):
			# [DOC] Iterate over python classes in module
			module = __import__(modname, fromlist='*')
			if modname.endswith('__tests__'):
				for test_name in dir(module):
					if type(getattr(module, test_name)) == TEST:
						Config.tests[test_name] = getattr(module, test_name)
				continue
			elif modname.endswith('__l10n__'):
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
	breakpoint()
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
		Config.modules['session'].methods['auth']['doc_args'].append(
			{
				'hash': ATTR.STR(),
				attr: Config.user_attrs[attr],
				'groups': ATTR.LIST(list=[ATTR.ID()]),
			}
		)
		Config.modules['session'].methods['auth']['doc_args'].append(
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
				attr_name=var, attr_type=Config.vars_types[var]['type'], attr_val=Config.vars[var]
			)
		except:
			logger.error(
				f'Package \'{Config.vars_types[var]["package"]}\' requires \'{var}\' Var of type \'{Config.vars_types[var]["type"]._type}\', but validation failed. Exiting.'
			)
			exit(1)

	# [DOC] Call update_modules, effectively finalise initialising modules
	for module in Config.modules.values():
		module._initialise()
	# [DOC] Write api_ref if generate_ref mode
	if Config.generate_ref:
		generate_ref(modules_packages=Config.modules_packages, modules=Config.modules)
	# [DOC] Write api_models if generate_models mode
	if Config.generate_models:
		generate_models(modules_packages=Config.modules_packages, modules=Config.modules)


def extract_lambda_body(lambda_func):
	lambda_body = re.sub(
		r'^[a-z]+\s*=\s*lambda\s', '', inspect.getsource(lambda_func).strip()
	)
	if lambda_body.endswith(','):
		lambda_body = lambda_body[:-1]
	return lambda_body


def generate_ref(
	*, modules_packages: Dict[str, List[str]], modules: Dict[str, 'BaseModule']
):
	from nawah.config import Config
	from nawah.base_module import BaseModule

	# [DOC] Initialise _api_ref Config Attr
	Config._api_ref = '# API Reference\n'
	# [DOC] Iterate over packages in ascending order
	for package in sorted(modules_packages.keys()):
		# [DOC] Add package header
		Config._api_ref += f'- - -\n## Package: {package.replace("modules.", "")}\n'
		if not len(modules_packages[package]):
			Config._api_ref += f'No modules\n'
		# [DOC] Iterate over package modules in ascending order
		for module in sorted(modules_packages[package]):
			# [DOC] Add module header
			Config._api_ref += f'### Module: {module}\n'
			# [DOC] Add module description
			Config._api_ref += f'{modules[module].__doc__}\n'
			# [DOC] Add module attrs header
			Config._api_ref += '#### Attrs\n'
			# [DOC] Iterate over module attrs to add attrs types, defaults (if any)
			for attr in modules[module].attrs.keys():
				attr_ref = f'* {attr}:\n'
				if modules[module].attrs[attr]._desc:
					attr_ref += f'  * {modules[module].attrs[attr]._desc}\n'
				attr_ref += f'  * Type: `{modules[module].attrs[attr]}`\n'
				for default_attr in modules[module].defaults.keys():
					if (
						default_attr == attr
						or default_attr.startswith(f'{attr}.')
						or default_attr.startswith(f'{attr}:')
					):
						if type(modules[module].defaults[default_attr]) == ATTR_MOD:
							attr_ref += f'  * Default [{default_attr}]:\n'
							attr_ref += f'	* ATTR_MOD condition: `{extract_lambda_body(modules[module].defaults[default_attr].condition)}`\n'
							if callable(modules[module].defaults[default_attr].default):
								attr_ref += f'	* ATTR_MOD default: `{extract_lambda_body(modules[module].defaults[default_attr].default)}`\n'
							else:
								attr_ref += (
									f'	* ATTR_MOD default: {modules[module].defaults[default_attr].default}\n'
								)
						else:
							attr_ref += (
								f'  * Default [{default_attr}]: {modules[module].defaults[default_attr]}\n'
							)
				Config._api_ref += attr_ref
			if modules[module].diff:
				Config._api_ref += f'#### Attrs Diff: {modules[module].diff}\n'
			# [DOC] Add module methods
			Config._api_ref += '#### Methods\n'
			for method in modules[module].methods.keys():
				Config._api_ref += f'##### Method: {method}\n'
				Config._api_ref += f'* Permissions Sets:\n'
				for permission in modules[module].methods[method].permissions:
					Config._api_ref += f'  * {permission.privilege}\n'
					# [DOC] Add Query Modifier
					if permission.query_mod:
						Config._api_ref += f'	* Query Modifier:\n'
						if type(permission.query_mod) == dict:
							permission.query_mod = [permission.query_mod]
						for i in range(len(permission.query_mod)):
							Config._api_ref += f'	  * Set {i}:\n'
							# [TODO] Improve nested list sets
							if type(permission.query_mod[i]) != dict:
								Config._api_ref += f'		* List: {permission.query_mod[i]}\n'
								continue
							for attr in permission.query_mod[i].keys():
								if type(permission.query_mod[i][attr]) == ATTR_MOD:
									Config._api_ref += f'		* {attr}:\n'
									Config._api_ref += f'		  * ATTR_MOD condition: {extract_lambda_body(permission.query_mod[i][attr].condition)}\n'
									if callable(permission.query_mod[i][attr].default):
										Config._api_ref += f'		  * ATTR_MOD default: {extract_lambda_body(permission.query_mod[i][attr].default)}\n'
									else:
										Config._api_ref += (
											f'		  * ATTR_MOD default: {permission.query_mod[i][attr].default}\n'
										)
								else:
									Config._api_ref += f'		* {attr}: {permission.query_mod[i][attr]}\n'
					else:
						Config._api_ref += f'	* Query Modifier: None\n'
					# [DOC] Add Doc Modifier
					if permission.doc_mod:
						Config._api_ref += f'	* Doc Modifier:\n'
						if type(permission.doc_mod) == dict:
							permission.doc_mod = [permission.doc_mod]
						for i in range(len(permission.doc_mod)):
							Config._api_ref += f'	  * Set {i}:\n'
							for attr in permission.doc_mod[i].keys():
								if type(permission.doc_mod[i][attr]) == ATTR_MOD:
									Config._api_ref += f'		* {attr}:\n'
									Config._api_ref += f'		  * ATTR_MOD condition: `{extract_lambda_body(permission.doc_mod[i][attr].condition)}`\n'
									if callable(permission.doc_mod[i][attr].default):
										Config._api_ref += f'		  * ATTR_MOD default: {extract_lambda_body(permission.doc_mod[i][attr].default)}\n'
									else:
										Config._api_ref += (
											f'		  * ATTR_MOD default: {permission.doc_mod[i][attr].default}\n'
										)
								else:
									Config._api_ref += f'		* {attr}: {permission.doc_mod[i][attr]}\n'
					else:
						Config._api_ref += f'	* Doc Modifier: None\n'
				# [DOC] Add Query Args
				if modules[module].methods[method].query_args:
					Config._api_ref += f'* Query Args Sets:\n'
					for query_args_set in modules[module].methods[method].query_args:
						Config._api_ref += f'  * `{query_args_set}`\n'
				else:
					Config._api_ref += f'* Query Args Sets: None\n'
				# [DOC] Add Doc Args
				if modules[module].methods[method].doc_args:
					Config._api_ref += f'* DOC Args Sets:\n'
					for doc_args_set in modules[module].methods[method].doc_args:
						Config._api_ref += f'  * `{doc_args_set}`\n'
				else:
					Config._api_ref += f'* Doc Args Sets: None\n'
			# [DOC] Add module extns
			if modules[module].extns.keys():
				Config._api_ref += '#### Extended Attrs\n'
				for attr in modules[module].extns.keys():
					Config._api_ref += f'* {attr}:\n'
					if type(modules[module].extns[attr]) == EXTN:
						Config._api_ref += f'  * Module: \'{modules[module].extns[attr].module}\'\n'
						Config._api_ref += f'  * Extend Attrs: \'{modules[module].extns[attr].attrs}\'\n'
						Config._api_ref += f'  * Force: \'{modules[module].extns[attr].force}\'\n'
					elif type(modules[module].extns[attr]) == ATTR_MOD:
						Config._api_ref += f'  * ATTR_MOD condition: `{extract_lambda_body(modules[module].extns[attr].condition)}`\n'
						Config._api_ref += f'  * ATTR_MOD default: `{extract_lambda_body(modules[module].extns[attr].default)}`\n'
			else:
				Config._api_ref += '#### Extended Attrs: None\n'
			# [DOC] Add module cache sets
			if modules[module].cache:
				Config._api_ref += '#### Cache Sets\n'
				for i in range(len(modules[module].cache)):
					Config._api_ref += f'* Set {i}:\n'
					Config._api_ref += f'  * CACHE condition: `{extract_lambda_body(modules[module].cache[i].condition)}`\n'
					Config._api_ref += f'  * CACHE period: {modules[module].cache[i].period}\n'
			else:
				Config._api_ref += '#### Cache Sets: None\n'
			# [DOC] Add module analytics sets
			if modules[module].analytics:
				Config._api_ref += '#### Analytics Sets\n'
				for i in range(len(modules[module].analytics)):
					Config._api_ref += f'* Set {i}:\n'
					Config._api_ref += f'  * ANALYTIC condition: `{extract_lambda_body(modules[module].analytics[i].condition)}`\n'
					Config._api_ref += (
						f'  * ANALYTIC doc: `{extract_lambda_body(modules[module].analytics[i].doc)}`\n'
					)
			else:
				Config._api_ref += '#### Analytics Sets: None\n'
	import os

	ref_file = os.path.join(
		Config._app_path,
		'refs',
		f'NAWAH_API_REF_{datetime.datetime.utcnow().strftime("%d-%b-%Y")}.md',
	)
	with open(ref_file, 'w') as f:
		f.write(Config._api_ref)
		logger.info(f'API reference generated and saved to: \'{ref_file}\'. Exiting.')
		exit(0)


def generate_models(
	*, modules_packages: Dict[str, List[str]], modules: Dict[str, 'BaseModule']
):
	from nawah.config import Config
	from nawah.base_module import BaseModule

	# [DOC] Initialise _api_models Config Attr
	Config._api_models = '// Nawah Models\n'
	# [DOC] Add interface for DOC, LOCALE, LOCALES, FILE typing
	Config._api_models += 'interface Doc { _id: string; };\n'
	Config._api_models += 'export interface LOCALE { '
	for locale in Config.locales:
		Config._api_models += locale
		if locale != Config.locale:
			Config._api_models += '?'
		Config._api_models += ': string; '
	Config._api_models +=  '};\n'
	Config._api_models += 'export type LOCALES = \'' + '\' | \''.join(Config.locales) + '\';\n'
	Config._api_models += 'export type ID<T> = string & T;\n'
	Config._api_models += 'export interface FILE<T> { name: string; lastModified: number; type: T; size: number; content: string | boolean; };\n'
	# [DOC] Iterate over packages in ascending order
	for package in sorted(modules_packages.keys()):
		# [DOC] Add package header
		Config._api_models += f'\n// Package: {package.replace("modules.", "")}\n'
		if not len(modules_packages[package]):
			Config._api_models += f'// No modules\n'
		# [DOC] Iterate over package modules in ascending order
		for module in sorted(modules_packages[package]):
			module_class = str(modules[module].__class__).split('.')[-1].split('\'')[0]
			# [DOC] Add module header
			Config._api_models += f'// Module: {module_class}\n'
			
			# [DOC] Add module interface definition
			Config._api_models += f'export interface {module_class} extends String, Doc {{\n'
			# [DOC] Iterate over module attrs to add attrs types, defaults (if any)
			for attr in modules[module].attrs.keys():
				attr_model = ''
				if modules[module].attrs[attr]._desc:
					attr_model += f'\t// @property {{__TYPE__}} {modules[module].attrs[attr]._desc}\n'
				attr_model += f'\t{attr}__DEFAULT__: __TYPE__;\n'
				for default_attr in modules[module].defaults.keys():
					if (
						default_attr == attr
						or default_attr.startswith(f'{attr}.')
						or default_attr.startswith(f'{attr}:')
					):
						# [DOC] Attr is in defaults, indicate the same
						attr_model = attr_model.replace('__DEFAULT__', '?')
				# [DOC] Attempt to replace __DEFAULT__ with empty string if it still exists, effectively no default value
				attr_model = attr_model.replace('__DEFAULT__', '')

				# [DOC] Add typing
				attr_model = attr_model.replace('__TYPE__', _generate_model_typing(module=modules[module], attr_name=attr, attr_type=modules[module].attrs[attr]))

				Config._api_models += attr_model
			
			# [DOC] Add closing braces
			Config._api_models += '};\n'
		Config._api_models += '\n'
	import os

	models_file = os.path.join(
		Config._app_path,
		'models',
		f'NAWAH_API_MODELS_{datetime.datetime.utcnow().strftime("%d-%b-%Y")}.ts',
	)
	with open(models_file, 'w') as f:
		f.write(Config._api_models)
		logger.info(f'API models generated and saved to: \'{models_file}\'. Exiting.')
		exit(0)


def _generate_model_typing(*, module: NAWAH_MODULE, attr_name: str, attr_type: ATTR):
	if attr_type._type == 'ANY':
		return 'any'

	elif attr_type._type == 'ACCESS':
		return '{ anon: boolean; users: Array<string>; groups: Array<string>; }'

	elif attr_type._type == 'BOOL':
		return 'boolean'
	
	elif attr_type._type == 'COUNTER':
		return 'string'

	elif attr_type._type == 'DATE':
		return 'string'

	elif attr_type._type == 'DATETIME':
		return 'string'

	elif attr_type._type == 'DYNAMIC_ATTR':
		return '{ type: string; args: { [key: string]: any; }; allow_none?: boolean; default: any; }'

	elif attr_type._type == 'DYNAMIC_VAL':
		return 'any'

	elif attr_type._type == 'KV_DICT':
		key_typing = _generate_model_typing(module=module, attr_name=attr_name, attr_type=attr_type._args['key'])
		val_typing = _generate_model_typing(module=module, attr_name=attr_name, attr_type=attr_type._args['val'])
		return f'{{ [key: {key_typing}]: {val_typing} }}'

	elif attr_type._type == 'TYPED_DICT':
		typing = '{ '
		for child_attr_type in attr_type._args['dict'].keys():
			typing += child_attr_type
			typing += ': '
			typing += _generate_model_typing(module=module, attr_name=attr_name, attr_type=attr_type._args['dict'][child_attr_type])
			typing += '; '
		typing += '}'
		return typing

	elif attr_type._type == 'EMAIL':
		return 'string'

	elif attr_type._type == 'FILE':
		types = 'string'
		if attr_type._args['types']:
			types = '\'' + '\' | \''.join(attr_type._args['types']) + '\''
			if '*' in types:
				types = 'string'
		
		return f'FILE<{types}>'

	elif attr_type._type == 'FLOAT':
		return 'number'

	elif attr_type._type == 'GEO':
		return '{ type: \'Point\'; coordinates: [number, number]; }'

	elif attr_type._type == 'ID':
		for attr in module.extns.keys():
			if attr.split('.')[0].split(':')[0] == attr_name:
				# [REF]: https://dev.to/rrampage/snake-case-to-camel-case-and-back-using-regular-expressions-and-python-m9j

				extn_module_class = re.sub(r'(.*?)_([a-zA-Z])', lambda match: match.group(1) + match.group(2).upper(), module.extns[attr].module)
				return f'ID<{extn_module_class[0].upper()}{extn_module_class[1:]}>'
		return 'ID<string>'

	elif attr_type._type == 'INT':
		return 'number'

	elif attr_type._type == 'IP':
		return 'string'

	elif attr_type._type == 'LIST':
		list_typings = []
		for child_attr_type in attr_type._args['list']:
			list_typings.append(_generate_model_typing(module=module, attr_name=attr_name, attr_type=child_attr_type))
		list_typing = ' | '.join(list_typings)
		return f'Array<{list_typing}>'

	elif attr_type._type == 'LOCALE':
		return 'LOCALE'

	elif attr_type._type == 'LOCALES':
		return 'LOCALES'

	elif attr_type._type == 'PHONE':
		return 'string'

	elif attr_type._type == 'STR':
		return 'string'

	elif attr_type._type == 'TIME':
		return 'string'

	elif attr_type._type == 'URI_WEB':
		return 'string'

	elif attr_type._type == 'LITERAL':
		return '\'' + '\' | \''.join(attr_type._args['literal']) + '\''

	elif attr_type._type == 'UNION':
		return ' | '.join([_generate_model_typing(module=module, attr_name=attr_name, attr_type=child_attr_type) for child_attr_type in attr_type._args['union']])
	
	elif attr_type._type == 'TYPE':
		return 'any'

def update_attr_values(
	*, attr: ATTR, value: Literal['default', 'extn'], value_path: str, value_val: Any
):
	value_path = value_path.split('.')
	for child_default_path in value_path:
		if ':' in child_default_path:
			attr = attr._args['dict'][child_default_path.split(':')[0]]._args['list'][
				int(child_default_path.split(':')[1])
			]
		else:
			if child_default_path == 'val' and attr._type == 'KV_DICT':
				attr = attr._args['val']
			else:
				attr = attr._args['dict'][child_default_path]
	setattr(attr, f'_{value}', value_val)


async def process_file_obj(
	*, doc: NAWAH_DOC, modules: Dict[str, NAWAH_MODULE], env: NAWAH_ENV
):
	if type(doc) == dict:
		doc_iter = doc.keys()
	elif type(doc) == list:
		doc_iter = range(len(doc))
	for j in doc_iter:
		if type(doc[j]) == dict:
			if '__file' in doc[j].keys():
				file_id = doc[j]['__file']
				logger.debug(
					f'Detected file in doc. Retrieving file from File module with _id: \'{file_id}\'.'
				)
				try:
					file_results = await modules['file'].read(
						skip_events=[Event.PERM], env=env, query=[{'_id': file_id}]
					)
					doc[j] = file_results.args.docs[0].file
					file_results = await modules['file'].delete(
						skip_events=[Event.PERM, Event.SOFT],
						env=env,
						query=[{'_id': file_id}],
					)
					if file_results.status != 200 or file_results.args.count != 1:
						logger.warning(
							f'Filed to delete doc _id \'{file_id}\' from File module after retrieving.'
						)
				except Exception as e:
					logger.error(f'Failed to retrieve doc _id \'{file_id}\', with error:')
					logger.error(e)
					doc[j] = None
			else:
				await process_file_obj(doc=doc[j], modules=modules, env=env)
		elif type(doc[j]) == list:
			await process_file_obj(doc=doc[j], modules=modules, env=env)


def extract_attr(*, scope: Dict[str, Any], attr_path: str):
	if attr_path.startswith('$__'):
		attr_path = attr_path[3:].split('.')
	else:
		attr_path = attr_path.split('.')
	attr = scope
	for i in range(len(attr_path)):
		child_attr = attr_path[i]
		try:
			logger.debug(f'Attempting to extract {child_attr} from {attr}.')
			if ':' in child_attr:
				child_attr = child_attr.split(':')
				attr = attr[child_attr[0]]
				for i in range(1, len(child_attr)):
					attr = attr[int(child_attr[i])]
			else:
				attr = attr[child_attr]
		except Exception as e:
			logger.error(f'Failed to extract {child_attr} from {attr}.')
			raise e
	return attr


def set_attr(*, scope: Dict[str, Any], attr_path: str, value: Any):
	if attr_path.startswith('$__'):
		attr_path = attr_path[3:].split('.')
	else:
		attr_path = attr_path.split('.')
	attr = scope
	for i in range(len(attr_path) - 1):
		child_attr = attr_path[i]
		try:
			if ':' in child_attr:
				child_attr = child_attr.split(':')
				attr = attr[child_attr[0]]
				for i in range(1, len(child_attr)):
					attr = attr[int(child_attr[i])]
			else:
				attr = attr[child_attr]
		except Exception as e:
			logger.error(f'Failed to extract {child_attr} from {attr}.')
			raise e
	if ':' in attr_path[-1]:
		attr_path[-1] = attr_path[-1].split(':')
		attr = attr[attr_path[-1][0]]
		for i in range(1, len(attr_path[-1]) - 1):
			attr = attr[int(attr_path[-1][i])]
		attr[int(attr_path[-1][-1])] = value
	else:
		attr[attr_path[-1]] = value


def expand_attr(*, doc: Dict[str, Any], expanded_doc: Dict[str, Any] = None):
	if not expanded_doc:
		expanded_doc = {}
	for attr in doc.keys():
		if type(doc[attr]) == dict:
			doc[attr] = expand_attr(doc=doc[attr])
		if '.' in attr:
			attr_path = attr.split('.')
			scope = expanded_doc
			for i in range(len(attr_path) - 1):
				try:
					if type(scope[attr_path[i]]) != dict:
						scope[attr_path[i]] = {}
				except KeyError:
					scope[attr_path[i]] = {}
				scope = scope[attr_path[i]]
			scope[attr_path[-1]] = doc[attr]
		else:
			expanded_doc[attr] = doc[attr]
	return expanded_doc


def deep_update(*, target: Union[List, Dict], new_values: Union[List, Dict]):
	if type(target) != type(new_values):
		logger.error(
			f'Type \'{type(target)}\' of \'target\' is not the same as \'{type(new_values)}\' of \'new_values\'. Exiting.'
		)
		exit(1)
	if type(new_values) == dict:
		for k in new_values.keys():
			if k not in target.keys():
				target[k] = new_values[k]
			else:
				deep_update(target=target[k], new_values=new_values[k])
	elif type(new_values) == list:
		for j in new_values:
			if j not in target:
				target.append(j)


class MissingAttrException(Exception):
	def __init__(self, *, attr_name):
		self.attr_name = attr_name
		logger.debug(f'MissingAttrException: {str(self)}')

	def __str__(self):
		return f'Missing attr \'{self.attr_name}\''


class InvalidAttrException(Exception):
	def __init__(self, *, attr_name, attr_type, val_type):
		self.attr_name = attr_name
		self.attr_type = attr_type
		self.val_type = val_type
		logger.debug(f'InvalidAttrException: {str(self)}')

	def __str__(self):
		return f'Invalid attr \'{self.attr_name}\' of type \'{self.val_type}\' with required type \'{self.attr_type._type}\''


class ConvertAttrException(Exception):
	def __init__(self, *, attr_name, attr_type, val_type):
		self.attr_name = attr_name
		self.attr_type = attr_type
		self.val_type = val_type
		logger.debug(f'ConvertAttrException: {str(self)}')

	def __str__(self):
		return f'Can\'t convert attr \'{self.attr_name}\' of type \'{self.val_type}\' to type \'{self.attr_type._type}\''


async def validate_doc(
	*,
	doc: NAWAH_DOC,
	attrs: Dict[str, ATTR],
	allow_update: bool = False,
	skip_events: List[str] = None,
	env: Dict[str, Any] = None,
	query: Union[NAWAH_QUERY, Query] = None,
):
	from nawah.config import Config

	attrs_map = {attr.split('.')[0]: attr for attr in doc.keys()}

	for attr in attrs.keys():
		if attr not in attrs_map.keys():
			if not allow_update:
				doc[attr] = None
			else:
				continue
		elif allow_update and doc[attrs_map[attr]] == None:
			continue
		elif allow_update and doc[attrs_map[attr]] != None:
			attr = attrs_map[attr]

		try:
			if allow_update and '.' in attr:
				doc[attr] = await validate_dot_notated(
					attr=attr,
					doc=doc,
					attrs=attrs,
					skip_events=skip_events,
					env=env,
					query=query,
				)
			else:
				doc[attr] = await validate_attr(
					attr_name=attr,
					attr_type=attrs[attr],
					attr_val=doc[attr],
					allow_update=allow_update,
					skip_events=skip_events,
					env=env,
					query=query,
					doc=doc,
				)
		except Exception as e:
			if type(e) in [InvalidAttrException, ConvertAttrException]:
				if doc[attr] == None:
					raise MissingAttrException(attr_name=attr)
				else:
					raise e
			else:
				raise e


async def validate_dot_notated(
	attr: str,
	doc: NAWAH_DOC,
	attrs: Dict[str, ATTR],
	skip_events: List[str],
	env: Dict[str, Any],
	query: Union[NAWAH_QUERY, Query],
):
	from nawah.config import Config

	attr_path = attr.split('.')
	attr_path_len = len(attr_path)
	attr_type: Union[Dict[str, ATTR], ATTR] = attrs

	try:
		for i in range(attr_path_len):
			# [DOC] Iterate over attr_path to reach last valid Attr Type
			if type(attr_type) == dict:
				attr_type = attr_type[attr_path[i]]
			elif type(attr_type) == ATTR and attr_type._type == 'ANY':
				return doc[attr]
			elif type(attr_type) == ATTR and attr_type._type == 'LOCALE':
				if attr_path[i] not in Config.locales:
					raise Exception()
				attr_type = ATTR.STR()
			elif type(attr_type) == ATTR and attr_type._type == 'TYPED_DICT':
				attr_type = attr_type._args['dict'][attr_path[i]]
			elif type(attr_type) == ATTR and attr_type._type == 'KV_DICT':
				attr_type = attr_type._args['val']
			# [DOC] However, if list or union, start a new validate_dot_notated call as it is required to check all the provided types
			elif type(attr_type) == ATTR and attr_type._type in ['LIST', 'UNION']:
				if attr_type._type == 'LIST':
					attr_type_iter = attr_type._args['list']
				else:
					attr_type_iter = attr_type._args['union']
				for child_attr_type in attr_type_iter:
					attr_val = await validate_dot_notated(
						attr='.'.join(attr_path[i:]),
						doc={'.'.join(attr_path[i:]): doc[attr]},
						attrs={attr_path[i]: child_attr_type},
						skip_events=skip_events,
						env=env,
						query=query,
					)
					if attr_val != None:
						return attr_val
				raise Exception()
			else:
				raise Exception()

		# [DOC] Validate val against final Attr Type
		attr_val = await validate_attr(
			attr_name=attr,
			attr_type=attr_type,
			attr_val=doc[attr],
			allow_update=True,
			skip_events=skip_events,
			env=env,
			query=query,
			doc=doc,
		)
		return attr_val
	except:
		raise InvalidAttrException(
			attr_name=attr, attr_type=attrs[attr_path[0]], val_type=type(doc[attr])
		)


async def validate_default(
	*,
	attr_type: ATTR,
	attr_val: Any,
	skip_events: List[str],
	env: Dict[str, Any],
	query: Union[NAWAH_QUERY, Query],
	doc: NAWAH_DOC,
	scope: NAWAH_DOC,
	allow_none: bool,
):
	if not allow_none and type(attr_type._default) == ATTR_MOD:
		if attr_type._default.condition(
			skip_events=skip_events, env=env, query=query, doc=doc, scope=scope
		):
			if callable(attr_type._default.default):
				attr_val = attr_type._default.default(
					skip_events=skip_events, env=env, query=query, doc=doc, scope=scope
				)
			else:
				attr_val = attr_type._default.default
			return copy.deepcopy(attr_val)

	elif attr_type._type == 'COUNTER':
		from nawah.config import Config

		counter_groups = re.findall(
			r'(\$__(?:values:[0-9]+|counters\.[a-z0-9_]+))', attr_type._args['pattern']
		)
		counter_val = attr_type._args['pattern']
		for group in counter_groups:
			for group in counter_groups:
				if group.startswith('$__values:'):
					value_callable = attr_type._args['values'][int(group.replace('$__values:', ''))]
					counter_val = counter_val.replace(
						group, str(value_callable(skip_events=skip_events, env=env, query=query, doc=doc))
					)
				elif group.startswith('$__counters.'):
					counter_name = group.replace('$__counters.', '')
					setting_results = await Config.modules['setting'].read(
						skip_events=[Event.PERM],
						env=env,
						query=[
							{
								'var': '__counter:' + counter_name,
								'type': 'global',
							}
						],
					)
					setting = setting_results.args.docs[0]
					setting_results = asyncio.create_task(
						Config.modules['setting'].update(
							skip_events=[Event.PERM],
							env=env,
							query=[{'_id': setting._id, 'type': 'global'}],
							doc={'val': {'$add': 1}},
						)
					)
					# [DOC] Condition "not task.cancelled()" is added to avoid exceptions with the task getting cancelled during its run as such it might be running in test mode, or at time of shutting down Nawah
					setting_update_callback = (
						lambda task: logger.error(
							f'Failed to update Setting doc for counter \'{counter_name}\''
						)
						if not task.cancelled() and task.result().status != 200
						else None
					)
					setting_results.add_done_callback(setting_update_callback)
					counter_val = counter_val.replace(group, str(setting.val + 1))
		return counter_val

	elif attr_val == None:
		if allow_none:
			return attr_val
		elif attr_type._default != NAWAH_VALUES.NONE_VALUE:
			return copy.deepcopy(attr_type._default)

	raise Exception('No default set to validate.')


async def validate_attr(
	*,
	attr_name: str,
	attr_type: ATTR,
	attr_val: Any,
	allow_update: bool = False,
	skip_events: List[str] = None,
	env: Dict[str, Any] = None,
	query: Union[NAWAH_QUERY, Query] = None,
	doc: NAWAH_DOC = None,
	scope: NAWAH_DOC = None,
):
	from nawah.config import Config

	try:
		return await validate_default(
			attr_type=attr_type,
			attr_val=attr_val,
			skip_events=skip_events,
			env=env,
			query=query,
			doc=doc,
			scope=scope if scope else doc,
			allow_none=allow_update,
		)
	except:
		pass

	attr_oper = None
	attr_oper_args = {}
	if allow_update and type(attr_val) == dict:
		if '$add' in attr_val.keys():
			attr_oper = '$add'
			attr_val = attr_val['$add']
		elif '$multiply' in attr_val.keys():
			attr_oper = '$multiply'
			attr_val = attr_val['$multiply']
		elif '$append' in attr_val.keys():
			attr_oper = '$append'
			if '$unique' in attr_val.keys() and attr_val['$unique'] == True:
				attr_oper_args['$unique'] = True
			else:
				attr_oper_args['$unique'] = False
			attr_val = [attr_val['$append']]
		elif '$set_index' in attr_val.keys():
			attr_oper = '$set_index'
			attr_oper_args['$index'] = attr_val['$set_index']
			attr_val = [attr_val['$set_index']]
		elif '$del_val' in attr_val.keys():
			attr_oper = '$del_val'
			attr_val = attr_val['$del_val']
			if attr_type._type != 'LIST' or type(attr_val) != list:
				raise InvalidAttrException(
					attr_name=attr_name, attr_type=attr_type, val_type=type(attr_val)
				)
			return return_valid_attr(
				attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
			)
		elif '$del_index' in attr_val.keys():
			attr_oper = '$del_index'
			attr_oper_args['$index'] = attr_val['$del_index']
			attr_val = attr_val['$del_index']
			if (attr_type._type == 'LIST' and type(attr_val) == int) or (
				attr_type._type == 'KV_DICT' and type(attr_val) == str
			):
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)
			else:
				raise InvalidAttrException(
					attr_name=attr_name, attr_type=attr_type, val_type=type(attr_val)
				)

	# [DOC] Deepcopy attr_val to eliminate changes in in original object
	attr_val = copy.deepcopy(attr_val)

	try:
		if attr_type._type == 'ANY':
			if attr_val != None:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'ACCESS':
			if (
				type(attr_val) == dict
				and set(attr_val.keys()) == {'anon', 'users', 'groups'}
				and type(attr_val['anon']) == bool
				and type(attr_val['users']) == list
				and type(attr_val['groups']) == list
			):
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'BOOL':
			if type(attr_val) == bool:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'DATE':
			if re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$', attr_val):
				if attr_type._args['ranges']:
					for date_range in attr_type._args['ranges']:
						date_range = copy.deepcopy(date_range)
						for i in [0, 1]:
							if date_range[i][0] in ['+', '-']:
								date_range_delta = {}
								if date_range[i][-1] == 'd':
									date_range_delta = {'days': int(date_range[i][:-1])}
								elif date_range[i][-1] == 'w':
									date_range_delta = {'weeks': int(date_range[i][:-1])}
								date_range[i] = (
									(datetime.datetime.utcnow() + datetime.timedelta(**date_range_delta))
									.isoformat()
									.split('T')[0]
								)
						if attr_val >= date_range[0] and attr_val < date_range[1]:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'DATETIME':
			if re.match(
				r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{6})?)?$',
				attr_val,
			):
				if attr_type._args['ranges']:
					for datetime_range in attr_type._args['ranges']:
						datetime_range = copy.deepcopy(datetime_range)
						for i in [0, 1]:
							if datetime_range[i][0] in ['+', '-']:
								datetime_range_delta = {}
								if datetime_range[i][-1] == 'd':
									datetime_range_delta = {'days': int(datetime_range[i][:-1])}
								elif datetime_range[i][-1] == 's':
									datetime_range_delta = {'seconds': int(datetime_range[i][:-1])}
								elif datetime_range[i][-1] == 'm':
									datetime_range_delta = {'minutes': int(datetime_range[i][:-1])}
								elif datetime_range[i][-1] == 'h':
									datetime_range_delta = {'hours': int(datetime_range[i][:-1])}
								elif datetime_range[i][-1] == 'w':
									datetime_range_delta = {'weeks': int(datetime_range[i][:-1])}
								datetime_range[i] = (
									datetime.datetime.utcnow() + datetime.timedelta(**datetime_range_delta)
								).isoformat()
						if attr_val >= datetime_range[0] and attr_val < datetime_range[1]:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'DYNAMIC_ATTR':
			if type(attr_val) == dict:
				try:
					if (not attr_type._args['types']) or (
						attr_type._args['types'] and attr_val['type'] in attr_type._args['types']
					):
						_, attr_val = generate_dynamic_attr(dynamic_attr=attr_val)
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
				except:
					pass

		elif attr_type._type == 'DYNAMIC_VAL':
			# [DOC] Populate setting_query
			setting_query = {}
			if attr_type._args['dynamic_attr'].startswith('$__settings.global/'):
				setting_query['type'] = 'global'
				setting_query['var'] = attr_type._args['dynamic_attr'].split('/')[1]
			elif attr_type._args['dynamic_attr'].startswith('$__settings.user/'):
				setting_query['type'] = 'user'
				_, setting_query['user'], setting_query['var'] = attr_type._args[
					'dynamic_attr'
				].split('/')
			# [DOC] Check if variables are present in setting_query['var']
			for setting_query_var in re.findall(
				r'(\$__doc\.([a-zA-Z0-9_]+))', setting_query['var']
			):
				setting_query['var'] = setting_query['var'].replace(
					setting_query_var[0], str(extract_attr(scope=doc, attr_path=setting_query_var[1]))
				)
			# [DOC] Read setting val
			setting_results = await Config.modules['setting'].read(
				skip_events=[Event.PERM], env=env, query=[setting_query]
			)
			setting = setting_results.args.docs[0]
			dynamic_attr = generate_dynamic_attr(dynamic_attr=setting.val)[0]
			attr_val = await validate_attr(
				attr_name=attr_name, attr_type=dynamic_attr, attr_val=attr_val
			)
			return return_valid_attr(
				attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
			)

		elif attr_type._type == 'KV_DICT':
			if type(attr_val) == dict:
				if attr_type._args['min']:
					if len(attr_val.keys()) < attr_type._args['min']:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				if attr_type._args['max']:
					if len(attr_val.keys()) > attr_type._args['max']:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				if attr_type._args['req']:
					for req_key in attr_type._args['req']:
						if req_key not in attr_val.keys():
							raise InvalidAttrException(
								attr_name=attr_name,
								attr_type=attr_type,
								val_type=type(attr_val),
							)
				shadow_attr_val = {}
				for child_attr_val in attr_val.keys():
					shadow_attr_val[
						await validate_attr(
							attr_name=f'{attr_name}.{child_attr_val}',
							attr_type=attr_type._args['key'],
							attr_val=child_attr_val,
							allow_update=allow_update,
							skip_events=skip_events,
							env=env,
							query=query,
							doc=doc,
							scope=attr_val,
						)
					] = await validate_attr(
						attr_name=f'{attr_name}.{child_attr_val}',
						attr_type=attr_type._args['val'],
						attr_val=attr_val[child_attr_val],
						allow_update=allow_update,
						skip_events=skip_events,
						env=env,
						query=query,
						doc=doc,
						scope=attr_val,
					)
				return return_valid_attr(
					attr_val=shadow_attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'TYPED_DICT':
			if type(attr_val) == dict:
				if set(attr_val.keys()) != set(attr_type._args['dict'].keys()):
					raise InvalidAttrException(
						attr_name=attr_name,
						attr_type=attr_type,
						val_type=type(attr_val),
					)
				for child_attr_type in attr_type._args['dict'].keys():
					if child_attr_type not in attr_val.keys():
						attr_val[child_attr_type] = None
					attr_val[child_attr_type] = await validate_attr(
						attr_name=f'{attr_name}.{child_attr_type}',
						attr_type=attr_type._args['dict'][child_attr_type],
						attr_val=attr_val[child_attr_type],
						allow_update=allow_update,
						skip_events=skip_events,
						env=env,
						query=query,
						doc=doc,
						scope=attr_val,
					)
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'EMAIL':
			if type(attr_val) == str and re.match(r'^[^@]+@[^@]+\.[^@]+$', attr_val):
				if attr_type._args['allowed_domains']:
					for domain in attr_type._args['allowed_domains']:
						if attr_type._args['strict']:
							domain = f'@{domain}'
						if attr_val.endswith(domain):
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				elif attr_type._args['disallowed_domains']:
					for domain in attr_type._args['disallowed_domains']:
						if attr_type._args['strict']:
							domain = f'@{domain}'
						if attr_val.endswith(domain):
							break
					else:
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'FILE':
			if type(attr_val) == list and len(attr_val):
				try:
					attr_val = await validate_attr(
						attr_name=attr_name,
						attr_type=attr_type,
						attr_val=attr_val[0],
						allow_update=allow_update,
						skip_events=skip_events,
						env=env,
						query=query,
						doc=doc,
						scope=attr_val,
					)
				except:
					raise InvalidAttrException(
						attr_name=attr_name,
						attr_type=attr_type,
						val_type=type(attr_val),
					)
			file_type = (
				type(attr_val) == dict
				and set(attr_val.keys()) == {'name', 'lastModified', 'type', 'size', 'content'}
				and type(attr_val['name']) == str
				and type(attr_val['type']) == str
				and type(attr_val['lastModified']) == int
				and type(attr_val['size']) == int
				and type(attr_val['content']) in [binary.Binary, bytes]
			)
			if not file_type:
				raise InvalidAttrException(
					attr_name=attr_name, attr_type=attr_type, val_type=type(attr_val)
				)
			if attr_type._args['types']:
				for file_type in attr_type._args['types']:
					if attr_val['type'].split('/')[0] == file_type.split('/')[0]:
						if (
							file_type.split('/')[1] == '*'
							or attr_val['type'].split('/')[1] == file_type.split('/')[1]
						):
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
			else:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'FLOAT':
			if type(attr_val) == str and re.match(r'^[0-9]+(\.[0-9]+)?$', attr_val):
				attr_val = float(attr_val)
			elif type(attr_val) == int:
				attr_val = float(attr_val)

			if type(attr_val) == float:
				if attr_type._args['ranges']:
					for _range in attr_type._args['ranges']:
						if attr_val >= _range[0] and attr_val < _range[1]:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'GEO':
			if (
				type(attr_val) == dict
				and set(attr_val.keys()) == {'type', 'coordinates'}
				and attr_val['type'] in ['Point']
				and type(attr_val['coordinates']) == list
				and len(attr_val['coordinates']) == 2
				and type(attr_val['coordinates'][0]) in [int, float]
				and type(attr_val['coordinates'][1]) in [int, float]
			):
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'ID':
			if type(attr_val) == BaseModel or type(attr_val) == DictObj:
				return return_valid_attr(
					attr_val=attr_val._id, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)
			elif type(attr_val) == ObjectId:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)
			elif type(attr_val) == str:
				try:
					return return_valid_attr(
						attr_val=ObjectId(attr_val), attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)
				except:
					raise ConvertAttrException(
						attr_name=attr_name,
						attr_type=attr_type,
						val_type=type(attr_val),
					)

		elif attr_type._type == 'INT':
			if type(attr_val) == str and re.match(r'^[0-9]+$', attr_val):
				attr_val = int(attr_val)

			if type(attr_val) == int:
				if attr_type._args['ranges']:
					for _range in attr_type._args['ranges']:
						if attr_val in range(*_range):
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'IP':
			if re.match(
				r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
				attr_val,
			):
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'LIST':
			if type(attr_val) == list:
				if attr_type._args['min']:
					if len(attr_val) < attr_type._args['min']:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				if attr_type._args['max']:
					if len(attr_val) > attr_type._args['max']:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				for i in range(len(attr_val)):
					child_attr_val = attr_val[i]
					child_attr_check = False
					for child_attr_type in attr_type._args['list']:
						try:
							attr_val[i] = await validate_attr(
								attr_name=attr_name,
								attr_type=child_attr_type,
								attr_val=child_attr_val,
								allow_update=allow_update,
								skip_events=skip_events,
								env=env,
								query=query,
								doc=doc,
								scope=attr_val,
							)
							child_attr_check = True
							break
						except:
							pass
					if not child_attr_check:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'LOCALE':
			attr_val = await validate_attr(
				attr_name=attr_name,
				attr_type=ATTR.KV_DICT(
					key=ATTR.LITERAL(literal=[locale for locale in Config.locales]),
					val=ATTR.STR(),
					min=1,
					req=[Config.locale],
				),
				attr_val=attr_val,
				allow_update=allow_update,
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				scope=attr_val,
			)
			if Config.locale_strategy == LOCALE_STRATEGY.NONE_VALUE:
				attr_val = {
					locale: attr_val[locale] if locale in attr_val.keys() else None
					for locale in Config.locales
				}
			elif callable(Config.locale_strategy):
				attr_val = {
					locale: attr_val[locale]
					if locale in attr_val.keys()
					else Config.locale_strategy(attr_val=attr_val, locale=locale)
					for locale in Config.locales
				}
			else:
				attr_val = {
					locale: attr_val[locale] if locale in attr_val.keys() else attr_val[Config.locale]
					for locale in Config.locales
				}
			return return_valid_attr(
				attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
			)

		elif attr_type._type == 'LOCALES':
			if attr_val in Config.locales:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'PHONE':
			if attr_type._args['codes']:
				for phone_code in attr_type._args['codes']:
					if re.match(fr'^\+{phone_code}[0-9]+$', attr_val):
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
			else:
				if re.match(r'^\+[0-9]+$', attr_val):
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'STR':
			if type(attr_val) == str:
				if attr_type._args['pattern']:
					if re.match(f'^{attr_type._args["pattern"]}$', attr_val):
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'TIME':
			if re.match(r'^[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{6})?)?$', attr_val):
				if attr_type._args['ranges']:
					for time_range in attr_type._args['ranges']:
						time_range = copy.deepcopy(time_range)
						for i in [0, 1]:
							if time_range[i][0] in ['+', '-']:
								time_range_delta = {}
								if time_range[i][-1] == 's':
									time_range_delta = {'seconds': int(time_range[i][:-1])}
								elif time_range[i][-1] == 'm':
									time_range_delta = {'minutes': int(time_range[i][:-1])}
								elif time_range[i][-1] == 'h':
									time_range_delta = {'hours': int(time_range[i][:-1])}
								time_range[i] = (
									(datetime.datetime.utcnow() + datetime.timedelta(**time_range_delta))
									.isoformat()
									.split('T')[1]
								)
						if attr_val >= time_range[0] and attr_val < time_range[1]:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'URI_WEB':
			if re.match(r'^https?:\/\/(?:[\w\-\_]+\.)(?:\.?[\w]{2,})+([\?\/].*)?$', attr_val):
				if attr_type._args['allowed_domains']:
					attr_val_domain = attr_val.split('/')[2]
					for domain in attr_type._args['allowed_domains']:
						if attr_type._args['strict'] and attr_val_domain == domain:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
						elif not attr_type._args['strict'] and attr_val_domain.endswith(domain):
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				elif attr_type._args['disallowed_domains']:
					attr_val_domain = attr_val.split('/')[2]
					for domain in attr_type._args['disallowed_domains']:
						if attr_type._args['strict'] and attr_val_domain == domain:
							break
						elif not attr_type._args['strict'] and attr_val_domain.endswith(domain):
							break
					else:
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'LITERAL':
			if attr_val in attr_type._args['literal']:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'UNION':
			for child_attr in attr_type._args['union']:
				try:
					attr_val = await validate_attr(
						attr_name=attr_name,
						attr_type=child_attr,
						attr_val=attr_val,
						allow_update=allow_update,
						skip_events=skip_events,
						env=env,
						query=query,
						doc=doc,
						scope=attr_val,
					)
				except:
					continue
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'TYPE':
			return return_valid_attr(
				attr_val=Config.types[attr_type._args['type']](
					attr_name=attr_name, attr_type=attr_type, attr_val=attr_val
				),
				attr_oper=attr_oper,
				attr_oper_args=attr_oper_args,
			)

	except Exception as e:
		pass
	try:
		e
	except:
		e = InvalidAttrException(
			attr_name=attr_name, attr_type=attr_type, val_type=type(attr_val)
		)
	if type(e) in [InvalidAttrException, ConvertAttrException]:
		if allow_update:
			return None
		elif attr_type._default != NAWAH_VALUES.NONE_VALUE:
			return attr_type._default
		else:
			raise e


def return_valid_attr(
	*,
	attr_val: Any,
	attr_oper: Literal[
		None, '$add', '$multiply', '$append', '$set_index', '$del_val', '$del_index'
	],
	attr_oper_args: Dict[str, Any],
) -> Any:
	if not attr_oper:
		return attr_val
	elif attr_oper in ['$add', '$multiply', '$del_val']:
		return {attr_oper: attr_val}
	elif attr_oper == '$append':
		return {'$append': attr_val[0], '$unique': attr_oper_args['$unique']}
	elif attr_oper == '$set_index':
		return {'$set_index': attr_val[0], '$index': attr_oper_args['$index']}
	elif attr_oper == '$del_index':
		return {'$del_index': attr_oper_args['$index']}


def generate_dynamic_attr(
	*, dynamic_attr: Dict[str, Any]
) -> Tuple[ATTR, Dict[str, Any]]:
	# [DOC] Fail-safe checks
	if dynamic_attr['type'] not in ATTRS_TYPES.keys():
		raise InvalidAttrTypeException(attr_type=dynamic_attr['type'])
	if 'args' not in dynamic_attr.keys():
		dynamic_attr['args'] = {}

	# [DOC] Process args of type ATTR
	if dynamic_attr['type'] == 'LIST':
		shadow_arg_list = []
		for i in range(len(dynamic_attr['args']['list'])):
			shadow_arg_list.append(None)
			dynamic_attr['args']['list'][i], shadow_arg_list[i] = generate_dynamic_attr(
				dynamic_attr=dynamic_attr['args']['list'][i]
			)
	elif dynamic_attr['type'] == 'TYPED_DICT':
		shadow_arg_dict = {}
		for dict_attr in dynamic_attr['args']['dict'].keys():
			(
				dynamic_attr['args']['dict'][dict_attr],
				shadow_arg_dict[dict_attr],
			) = generate_dynamic_attr(
				dynamic_attr=dynamic_attr['args']['dict'][dict_attr]
			)
	elif dynamic_attr['type'] == 'KV_DICT':
		dynamic_attr['args']['key'], _ = generate_dynamic_attr(
			dynamic_attr=dynamic_attr['args']['key']
		)
		dynamic_attr['args']['val'], _ = generate_dynamic_attr(
			dynamic_attr=dynamic_attr['args']['val']
		)
	if dynamic_attr['type'] == 'UNION':
		shadow_arg_union = []
		for i in range(len(dynamic_attr['args']['union'])):
			shadow_arg_list.append(None)
			dynamic_attr['args']['union'][i], shadow_arg_union[i] = generate_dynamic_attr(
				dynamic_attr=dynamic_attr['args']['union'][i]
			)
	# [DOC] Generate dynamic ATTR using ATTR controller
	dynamic_attr_type = getattr(ATTR, dynamic_attr['type'])(**dynamic_attr['args'])
	# [DOC] Reset values for args of type ATTR
	if dynamic_attr['type'] == 'LIST':
		dynamic_attr['args']['list'] = shadow_arg_list
	elif dynamic_attr['type'] == 'TYPED_DICT':
		dynamic_attr['args']['dict'] = shadow_arg_dict
	elif dynamic_attr['type'] == 'UNION':
		dynamic_attr['args']['dict'] = shadow_arg_union
	# [DOC] Set defaults for optional args
	if 'allow_none' not in dynamic_attr.keys():
		dynamic_attr['allow_none'] = False
	if 'default' not in dynamic_attr.keys():
		dynamic_attr['default'] = None

	return (dynamic_attr_type, dynamic_attr)


def encode_attr_type(*, attr_type: ATTR) -> Dict[str, Any]:
	encoded_attr_type = {
		'type': attr_type._type,
		'args': copy.deepcopy(attr_type._args),
		'allow_none': attr_type._default != NAWAH_VALUES.NONE_VALUE,
		'default': attr_type._default
		if attr_type._default != NAWAH_VALUES.NONE_VALUE
		else None,
	}
	# [DOC] Process args of type ATTR
	if attr_type._type == 'LIST':
		for i in range(len(attr_type._args['list'])):
			encoded_attr_type['args']['list'][i] = encode_attr_type(
				attr_type=attr_type._args['list'][i]
			)
	elif attr_type._type == 'TYPED_DICT':
		for dict_attr in attr_type._args['dict'].keys():
			encoded_attr_type['args']['dict'][dict_attr] = encode_attr_type(
				attr_type=attr_type._args['dict'][dict_attr]
			)
	elif attr_type._type == 'KV_DICT':
		encoded_attr_type['args']['key'] = encode_attr_type(attr_type=attr_type._args['key'])
		encoded_attr_type['args']['val'] = encode_attr_type(attr_type=attr_type._args['val'])
	elif attr_type._type == 'UNION':
		for i in range(len(attr_type._args['union'])):
			encoded_attr_type['args']['union'][i] = encode_attr_type(
				attr_type=attr_type._args['union'][i]
			)

	return encoded_attr_type


def generate_attr(*, attr_type: ATTR) -> Any:
	from nawah.config import Config

	if attr_type._type == 'ANY':
		return '__any'

	elif attr_type._type == 'ACCESS':
		return {'anon': True, 'users': [], 'groups': []}

	elif attr_type._type == 'BOOL':
		attr_val = random.choice([True, False])
		return attr_val

	elif attr_type._type == 'COUNTER':
		counter_groups = re.findall(
			r'(\$__(?:values:[0-9]+|counters\.[a-z0-9_]+))', attr_type._args['pattern']
		)
		attr_val = attr_type._args['pattern']
		for group in counter_groups:
			for group in counter_groups:
				if group.startswith('$__values:'):
					value_callable = attr_type._args['values'][int(group.replace('$__values:', ''))]
					attr_val = attr_val.replace(
						group, str(value_callable(skip_events=[], env={}, query=[], doc={}))
					)
				elif group.startswith('$__counters.'):
					attr_val = attr_val.replace(group, str(42))
		return attr_val

	elif attr_type._type == 'DATE':
		if attr_type._args['ranges']:
			datetime_range = attr_type._args['ranges'][0]
			# [DOC] Be lazy! find a whether start, end of range is a datetime and base the value on it
			if datetime_range[0][0] in ['+', '-'] and datetime_range[1][0] in ['+', '-']:
				# [DOC] Both start, end are dynamic, process start
				datetime_range_delta = {}
				if datetime_range[0][-1] == 'd':
					datetime_range_delta = {'days': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'w':
					datetime_range_delta = {'weeks': int(datetime_range[0][:-1])}
				attr_val = (
					(datetime.datetime.utcnow() + datetime.timedelta(**datetime_range_delta))
					.isoformat()
					.split('T')[0]
				)
			else:
				if datetime_range[0][0] not in ['+', '-']:
					attr_val = datetime_range[0]
				else:
					attr_val = (
						(datetime.datetime.fromisoformat(datetime_range[1]) - datetime.timedelta(days=1))
						.isoformat()
						.split('T')[0]
					)
		else:
			attr_val = datetime.datetime.utcnow().isoformat().split('T')[0]
		return attr_val

	elif attr_type._type == 'DATETIME':
		if attr_type._args['ranges']:
			datetime_range = attr_type._args['ranges'][0]
			# [DOC] Be lazy! find a whether start, end of range is a datetime and base the value on it
			if datetime_range[0][0] in ['+', '-'] and datetime_range[1][0] in ['+', '-']:
				# [DOC] Both start, end are dynamic, process start
				datetime_range_delta = {}
				if datetime_range[0][-1] == 'd':
					datetime_range_delta = {'days': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 's':
					datetime_range_delta = {'seconds': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'm':
					datetime_range_delta = {'minutes': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'h':
					datetime_range_delta = {'hours': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'w':
					datetime_range_delta = {'weeks': int(datetime_range[0][:-1])}
				attr_val = (
					datetime.datetime.utcnow() + datetime.timedelta(**datetime_range_delta)
				).isoformat()
			else:
				if datetime_range[0][0] not in ['+', '-']:
					attr_val = datetime_range[0]
				else:
					attr_val = (
						datetime.datetime.fromisoformat(datetime_range[1]) - datetime.timedelta(days=1)
					).isoformat()
		else:
			attr_val = datetime.datetime.utcnow().isoformat()
		return attr_val

	elif attr_type._type == 'KV_DICT':
		attr_val = {
			generate_attr(attr_type=attr_type._args['key']): generate_attr(
				attr_type=attr_type._args['val']
			)
			for _ in range(attr_type._args['min'] or 0)
		}
		if len(attr_val.keys()) < (attr_type._args['min'] or 0):
			attr_val = generate_attr(attr_type=attr_type)
		return attr_val

	elif attr_type._type == 'TYPED_DICT':
		attr_val = {
			child_attr: generate_attr(attr_type=attr_type._args['dict'][child_attr])
			for child_attr in attr_type._args['dict'].keys()
		}
		return attr_val

	elif attr_type._type == 'EMAIL':
		attr_val = f'some-{math.ceil(random.random() * 10000)}@mail.provider.com'
		if attr_type._args['allowed_domains']:
			if attr_type._args['strict']:
				domain = 'mail.provider.com'
			else:
				domain = 'provider.com'
			attr_val = attr_val.replace(
				domain, random.choice(attr_type._args['allowed_domains'])
			)
		return attr_val

	elif attr_type._type == 'FILE':
		attr_file_type = 'text/plain'
		attr_file_extension = 'txt'
		if attr_type._args['types']:
			for file_type in attr_type._args['types']:
				if '/' in file_type:
					attr_file_type = file_type
				if '*.' in file_type:
					attr_file_extension = file_type.replace('*.', '')
		file_name = f'__file-{math.ceil(random.random() * 10000)}.{attr_file_extension}'
		return {
			'name': file_name,
			'lastModified': 100000,
			'type': attr_file_type,
			'size': 6,
			'content': b'__file',
		}

	elif attr_type._type == 'FLOAT':
		if attr_type._args['ranges']:
			attr_val = random.choice(
				range(
					math.ceil(attr_type._args['ranges'][0][0]),
					math.floor(attr_type._args['ranges'][0][1]),
				)
			)
			if (
				attr_val != attr_type._args['ranges'][0][0]
				and (attr_val - 0.01) != attr_type._args['ranges'][0][0]
			):
				attr_val -= 0.01
			elif (attr_val + 0.01) < attr_type._args['ranges'][0][1]:
				attr_val += 0.01
			else:
				attr_val = float(attr_val)
		else:
			attr_val = random.random() * 10000
		return attr_val

	elif attr_type._type == 'GEO':
		return {
			'type': 'Point',
			'coordinates': [
				math.ceil(random.random() * 100000) / 1000,
				math.ceil(random.random() * 100000) / 1000,
			],
		}

	elif attr_type._type == 'ID':
		return ObjectId()

	elif attr_type._type == 'INT':
		if attr_type._args['ranges']:
			attr_val = random.choice(
				range(attr_type._args['ranges'][0][0], attr_type._args['ranges'][0][1])
			)
		else:
			attr_val = math.ceil(random.random() * 10000)
		return attr_val

	elif attr_type._type == 'IP':
		return '127.0.0.1'

	elif attr_type._type == 'LIST':
		return [
			generate_attr(attr_type=random.choice(attr_type._args['list']))
			for _ in range(attr_type._args['min'] or 0)
		]

	elif attr_type._type == 'LOCALE':
		return {
			locale: f'__locale-{math.ceil(random.random() * 10000)}' for locale in Config.locales
		}

	elif attr_type._type == 'LOCALES':
		from nawah.config import Config

		return Config.locale

	elif attr_type._type == 'PHONE':
		attr_phone_code = '000'
		if attr_type._args['codes']:
			attr_phone_code = random.choice(attr_type._args['codes'])
		return f'+{attr_phone_code}{math.ceil(random.random() * 10000)}'

	elif attr_type._type == 'STR':
		if attr_type._args['pattern']:
			logger.warning('Generator for Attr Type STR can\'t handle patterns. Ignoring.')
		return f'__str-{math.ceil(random.random() * 10000)}'

	elif attr_type._type == 'TIME':
		if attr_type._args['ranges']:
			datetime_range = attr_type._args['ranges'][0]
			# [DOC] Be lazy! find a whether start, end of range is a datetime and base the value on it
			if datetime_range[0][0] in ['+', '-'] and datetime_range[1][0] in ['+', '-']:
				# [DOC] Both start, end are dynamic, process start
				datetime_range_delta = {}
				if datetime_range[0][-1] == 's':
					datetime_range_delta = {'seconds': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'm':
					datetime_range_delta = {'minutes': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'h':
					datetime_range_delta = {'hours': int(datetime_range[0][:-1])}
				attr_val = (
					(datetime.datetime.utcnow() + datetime.timedelta(**datetime_range_delta))
					.isoformat()
					.split('T')[1]
				)
			else:
				if datetime_range[0][0] not in ['+', '-']:
					attr_val = datetime_range[0]
				else:
					# [REF]: https://stackoverflow.com/a/656394/2393762
					attr_val = (
						(
							datetime.datetime.combine(
								datetime.date.today(), datetime.time.fromisoformat(datetime_range[1])
							)
							- datetime.timedelta(minutes=1)
						)
						.isoformat()
						.split('T')[1]
					)
		else:
			attr_val = datetime.datetime.utcnow().isoformat().split('T')[1]
		return attr_val

	elif attr_type._type == 'URI_WEB':
		attr_val = f'https://sub.domain.com/page-{math.ceil(random.random() * 10000)}/'
		if attr_type._args['allowed_domains']:
			if attr_type._args['strict']:
				domain = 'sub.domain.com'
			else:
				domain = 'domain.com'
			attr_val = attr_val.replace(
				domain, random.choice(attr_type._args['allowed_domains'])
			)
		return attr_val

	elif attr_type._type == 'LITERAL':
		attr_val = random.choice(attr_type._args['literal'])
		return attr_val

	elif attr_type._type == 'UNION':
		attr_val = generate_attr(attr_type=random.choice(attr_type._args['union']))
		return attr_val

	raise Exception(f'Unknown generator attr \'{attr_type}\'')
