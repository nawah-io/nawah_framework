from collections.abc import MutableMapping
from typing import Dict, Any, Union, cast

import logging, copy

logger = logging.getLogger('nawah')

# [REF]: https://treyhunner.com/2019/04/why-you-shouldnt-inherit-from-list-and-dict-in-python/
class DictObj(MutableMapping):
	__attrs: Dict[str, Any]

	def __repr__(self):
		return f'<DictObj:{self.__attrs}>'

	def __init__(self, data: Union['DictObj', Dict[str, Any]]):
		if type(data) == DictObj:
			data = cast(DictObj, data)
			data = data._attrs()
		elif type(data) != dict:
			raise TypeError(
				f'DictObj can be initialised using DictObj or dict types only. Got \'{type(data)}\' instead.'
			)
		self.__attrs = {}
		self.update(data)

	def __getattribute__(self, attr):
		if attr in object.__getattribute__(self, '_DictObj__attrs').keys():
			return object.__getattribute__(self, '_DictObj__attrs')[attr]
		else:
			return object.__getattribute__(self, attr)

	def __deepcopy__(self, memo):
		return DictObj(copy.deepcopy(self.__attrs))

	def __setattr__(self, attr, val):
		if not attr.endswith('__attrs'):
			raise AttributeError(
				f'Can\'t assign to DictObj attr \'{attr}\' using __setattr__. Use __setitem__ instead.'
			)
		object.__setattr__(self, attr, val)

	def __getitem__(self, attr):
		try:
			return self.__attrs[attr]
		except Exception as e:
			logger.debug(f'Unable to __getitem__ {attr} of {self.__attrs.keys()}.')
			raise e

	def __setitem__(self, attr, val):
		self.__attrs[attr] = val

	def __delitem__(self, attr):
		del self.__attrs[attr]

	def __iter__(self):
		return iter(self.__attrs)

	def __len__(self):
		return len(self.__attrs)

	def __contains__(self, attr):
		return attr in self.__attrs.keys()

	def _attrs(self):
		return copy.deepcopy(self.__attrs)
