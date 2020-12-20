from nawah.classes import ATTR
from nawah.enums import NAWAH_VALUES

from typing import Dict, Any

import copy


def encode_attr_type(*, attr_type: ATTR) -> Dict[str, Any]:
	encoded_attr_type: Dict[str, Any] = {
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