from nawah.config import Config
from nawah.classes import EXTN

from typing import Dict, List

import logging, datetime, re, inspect

logger = logging.getLogger('nawah')


def generate_ref():
	# [TODO] Update function to replace ATTR_MOD checks with Attr Type TYPE
	# [DOC] Initialise _api_ref Config Attr
	Config._api_ref = '# API Reference\n'
	# [DOC] Iterate over packages in ascending order
	for package in sorted(Config.modules_packages.keys()):
		# [DOC] Add package header
		Config._api_ref += f'- - -\n## Package: {package.replace("modules.", "")}\n'
		if not len(Config.modules_packages[package]):
			Config._api_ref += f'No modules\n'
		# [DOC] Iterate over package modules in ascending order
		for module in sorted(Config.modules_packages[package]):
			# [DOC] Add module header
			Config._api_ref += f'### Module: {module}\n'
			# [DOC] Add module description
			Config._api_ref += f'{Config.modules[module].__doc__}\n'
			# [DOC] Add module attrs header
			Config._api_ref += '#### Attrs\n'
			# [DOC] Iterate over module attrs to add attrs types, defaults (if any)
			for attr in Config.modules[module].attrs.keys():
				attr_ref = f'* {attr}:\n'
				if Config.modules[module].attrs[attr]._desc:
					attr_ref += f'  * {Config.modules[module].attrs[attr]._desc}\n'
				attr_ref += f'  * Type: `{Config.modules[module].attrs[attr]}`\n'
				for default_attr in Config.modules[module].defaults.keys():
					if (
						default_attr == attr
						or default_attr.startswith(f'{attr}.')
						or default_attr.startswith(f'{attr}:')
					):
						# if type(Config.modules[module].defaults[default_attr]) == ATTR_MOD:
						# 	attr_ref += f'  * Default [{default_attr}]:\n'
						# 	attr_ref += f'	* ATTR_MOD condition: `{extract_lambda_body(Config.modules[module].defaults[default_attr].condition)}`\n'
						# 	if callable(Config.modules[module].defaults[default_attr].default):
						# 		attr_ref += f'	* ATTR_MOD default: `{extract_lambda_body(Config.modules[module].defaults[default_attr].default)}`\n'
						# 	else:
						# 		attr_ref += f'	* ATTR_MOD default: {Config.modules[module].defaults[default_attr].default}\n'
						# else:
						attr_ref += f'  * Default [{default_attr}]: {Config.modules[module].defaults[default_attr]}\n'
				Config._api_ref += attr_ref
			if Config.modules[module].diff:
				Config._api_ref += f'#### Attrs Diff: {Config.modules[module].diff}\n'
			# [DOC] Add module methods
			Config._api_ref += '#### Methods\n'
			for method in Config.modules[module].methods.keys():
				Config._api_ref += f'##### Method: {method}\n'
				Config._api_ref += f'* Permissions Sets:\n'
				for permission in Config.modules[module].methods[method].permissions:
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
				if Config.modules[module].methods[method].query_args:
					Config._api_ref += f'* Query Args Sets:\n'
					for query_args_set in Config.modules[module].methods[method].query_args:
						Config._api_ref += f'  * `{query_args_set}`\n'
				else:
					Config._api_ref += f'* Query Args Sets: None\n'
				# [DOC] Add Doc Args
				if Config.modules[module].methods[method].doc_args:
					Config._api_ref += f'* DOC Args Sets:\n'
					for doc_args_set in Config.modules[module].methods[method].doc_args:
						Config._api_ref += f'  * `{doc_args_set}`\n'
				else:
					Config._api_ref += f'* Doc Args Sets: None\n'
			# [DOC] Add module extns
			if Config.modules[module].extns.keys():
				Config._api_ref += '#### Extended Attrs\n'
				for attr in Config.modules[module].extns.keys():
					Config._api_ref += f'* {attr}:\n'
					if type(Config.modules[module].extns[attr]) == EXTN:
						Config._api_ref += (
							f'  * Module: \'{Config.modules[module].extns[attr].module}\'\n'
						)
						Config._api_ref += (
							f'  * Extend Attrs: \'{Config.modules[module].extns[attr].attrs}\'\n'
						)
						Config._api_ref += f'  * Force: \'{Config.modules[module].extns[attr].force}\'\n'
					elif type(Config.modules[module].extns[attr]) == ATTR_MOD:
						Config._api_ref += f'  * ATTR_MOD condition: `{extract_lambda_body(Config.modules[module].extns[attr].condition)}`\n'
						Config._api_ref += f'  * ATTR_MOD default: `{extract_lambda_body(Config.modules[module].extns[attr].default)}`\n'
			else:
				Config._api_ref += '#### Extended Attrs: None\n'
			# [DOC] Add module cache sets
			if Config.modules[module].cache:
				Config._api_ref += '#### Cache Sets\n'
				for i in range(len(Config.modules[module].cache)):
					Config._api_ref += f'* Set {i}:\n'
					Config._api_ref += f'  * CACHE condition: `{extract_lambda_body(Config.modules[module].cache[i].condition)}`\n'
					Config._api_ref += f'  * CACHE period: {Config.modules[module].cache[i].period}\n'
			else:
				Config._api_ref += '#### Cache Sets: None\n'
			# [DOC] Add module analytics sets
			if Config.modules[module].analytics:
				Config._api_ref += '#### Analytics Sets\n'
				for i in range(len(Config.modules[module].analytics)):
					Config._api_ref += f'* Set {i}:\n'
					Config._api_ref += f'  * ANALYTIC condition: `{extract_lambda_body(Config.modules[module].analytics[i].condition)}`\n'
					Config._api_ref += f'  * ANALYTIC doc: `{extract_lambda_body(Config.modules[module].analytics[i].doc)}`\n'
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


def extract_lambda_body(lambda_func):
	lambda_body = re.sub(
		r'^[a-z]+\s*=\s*lambda\s', '', inspect.getsource(lambda_func).strip()
	)
	if lambda_body.endswith(','):
		lambda_body = lambda_body[:-1]
	return lambda_body