from nawah.config import Config
from nawah.classes import ATTR, DictObj

from typing import Dict, List, TYPE_CHECKING

import logging, datetime, re

if TYPE_CHECKING:
	from nawah.base_module import BaseModule

logger = logging.getLogger('nawah')


def generate_models():
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
	Config._api_models += '};\n'
	Config._api_models += (
		'export type LOCALES = \'' + '\' | \''.join(Config.locales) + '\';\n'
	)
	Config._api_models += 'export type ID<T> = string & T;\n'
	Config._api_models += 'export interface FILE<T> { name: string; lastModified: number; type: T; size: number; content: string | boolean; };\n'
	# [DOC] Iterate over packages in ascending order
	for package in sorted(Config.modules_packages.keys()):
		# [DOC] Add package header
		Config._api_models += f'\n// Package: {package.replace("modules.", "")}\n'
		if not len(Config.modules_packages[package]):
			Config._api_models += f'// No modules\n'
		# [DOC] Iterate over package modules in ascending order
		for module in sorted(Config.modules_packages[package]):
			module_class = str(Config.modules[module].__class__).split('.')[-1].split('\'')[0]
			# [DOC] Add module header
			Config._api_models += f'// Module: {module_class}\n'

			# [DOC] Add module interface definition
			Config._api_models += f'export interface {module_class} extends String, Doc {{\n'
			# [DOC] Iterate over module attrs to add attrs types, defaults (if any)
			for attr in Config.modules[module].attrs.keys():
				attr_model = ''
				if Config.modules[module].attrs[attr]._desc:
					attr_model += (
						f'\t// @property {{__TYPE__}} {Config.modules[module].attrs[attr]._desc}\n'
					)
				attr_model += f'\t{attr}__DEFAULT__: __TYPE__;\n'
				for default_attr in Config.modules[module].defaults.keys():
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
				attr_model = attr_model.replace(
					'__TYPE__',
					_generate_model_typing(
						module=Config.modules[module],
						attr_name=attr,
						attr_type=Config.modules[module].attrs[attr],
					),
				)

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


def _generate_model_typing(*, module: 'BaseModule', attr_name: str, attr_type: ATTR):
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
		key_typing = _generate_model_typing(
			module=module, attr_name=attr_name, attr_type=attr_type._args['key']
		)
		val_typing = _generate_model_typing(
			module=module, attr_name=attr_name, attr_type=attr_type._args['val']
		)
		return f'{{ [key: {key_typing}]: {val_typing} }}'

	elif attr_type._type == 'TYPED_DICT':
		typing = '{ '
		for child_attr_type in attr_type._args['dict'].keys():
			typing += child_attr_type
			typing += ': '
			typing += _generate_model_typing(
				module=module,
				attr_name=attr_name,
				attr_type=attr_type._args['dict'][child_attr_type],
			)
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

				extn_module_class = re.sub(
					r'(.*?)_([a-zA-Z])',
					lambda match: match.group(1) + match.group(2).upper(),
					module.extns[attr].module,
				)
				return f'ID<{extn_module_class[0].upper()}{extn_module_class[1:]}>'
		return 'ID<string>'

	elif attr_type._type == 'INT':
		return 'number'

	elif attr_type._type == 'IP':
		return 'string'

	elif attr_type._type == 'LIST':
		list_typings = []
		for child_attr_type in attr_type._args['list']:
			list_typings.append(
				_generate_model_typing(
					module=module, attr_name=attr_name, attr_type=child_attr_type
				)
			)
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
		return ' | '.join(
			[
				_generate_model_typing(
					module=module, attr_name=attr_name, attr_type=child_attr_type
				)
				for child_attr_type in attr_type._args['union']
			]
		)

	elif attr_type._type == 'TYPE':
		return 'any'