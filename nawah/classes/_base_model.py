from ._dictobj import DictObj


class BaseModel(DictObj):
	def __repr__(self):
		return f'<Model:{str(self._id)}>'

	def __init__(self, attrs):
		for attr in attrs.keys():
			if type(attrs[attr]) == dict and '_id' in attrs[attr].keys():
				attrs[attr] = BaseModel(attrs[attr])
		super().__init__(attrs)