from typing import Dict, Any

import copy


class DictObj(dict):
	__attrs: Dict[str, Any] = {}

	def __repr__(self):
		return f'<DictObj:{self.__attrs}>'

	def __init__(self, attrs):
		if type(attrs) == DictObj:
			attrs = attrs._attrs()
		elif type(attrs) != dict:
			raise TypeError(
				f'DictObj can be initialised using DictObj or dict types only. Got \'{type(attrs)}\' instead.'
			)
		super().__init__(attrs)
		self.__attrs = attrs

	def __deepcopy__(self, memo):
		return DictObj(copy.deepcopy(self.__attrs))

	def __getattr__(self, attr):
		return self.__attrs[attr]

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

	def __contains__(self, attr):
		return attr in self.__attrs.keys()

	def _attrs(self):
		return copy.deepcopy(self.__attrs)