from nawah.classes import ATTR

from typing import Union, List, Dict, cast, Any, Literal, MutableMapping

import logging

logger = logging.getLogger('nawah')


def extract_attr(*, scope: MutableMapping[str, Any], attr_path: str):
	if attr_path.startswith('$__'):
		attr_path_parts = attr_path[3:].split('.')
	else:
		attr_path_parts = attr_path.split('.')
	attr: Any = scope
	for i in range(len(attr_path_parts)):
		child_attr = attr_path_parts[i]
		try:
			logger.debug(f'Attempting to extract {child_attr} from {attr}.')
			if ':' in child_attr:
				child_attr_parts = child_attr.split(':')
				attr = attr[child_attr_parts[0]]
				for i in range(1, len(child_attr_parts)):
					attr = attr[int(child_attr_parts[i])]  # type: ignore
			else:
				attr = attr[child_attr]
		except Exception as e:
			logger.error(f'Failed to extract {child_attr} from {attr}.')
			raise e
	return attr


def set_attr(*, scope: Dict[str, Any], attr_path: str, value: Any):
	if attr_path.startswith('$__'):
		attr_path_parts = attr_path[3:].split('.')
	else:
		attr_path_parts = attr_path.split('.')
	attr = scope
	for i in range(len(attr_path_parts) - 1):
		child_attr = attr_path_parts[i]
		try:
			if ':' in child_attr:
				child_attr_parts = child_attr.split(':')
				attr = attr[child_attr_parts[0]]
				for i in range(1, len(child_attr_parts)):
					attr = attr[int(child_attr_parts[i])]  # type: ignore
			else:
				attr = attr[child_attr]
		except Exception as e:
			logger.error(f'Failed to extract {child_attr} from {attr}.')
			raise e
	if ':' in attr_path_parts[-1]:
		attr_path_parts_last = attr_path_parts[-1].split(':')
		attr = attr[attr_path_parts_last[0]]
		for i in range(1, len(attr_path_parts_last) - 1):
			attr = attr[int(attr_path_parts_last[i])]  # type: ignore
		attr[int(attr_path_parts_last[-1])] = value  # type: ignore
	else:
		attr[attr_path_parts[-1]] = value


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
		new_values = cast(dict, new_values)
		for k in new_values.keys():
			target = cast(dict, target)
			if k not in target.keys():
				target[k] = new_values[k]
			else:
				deep_update(target=target[k], new_values=new_values[k])
	elif type(new_values) == list:
		for j in new_values:
			target = cast(list, target)
			if j not in target:
				target.append(j)


def update_attr_values(
	*, attr: ATTR, value: Literal['default', 'extn'], value_path: str, value_val: Any
):

	value_path_part = value_path.split('.')
	for child_default_path in value_path_part:
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