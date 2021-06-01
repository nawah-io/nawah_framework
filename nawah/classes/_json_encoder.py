from bson import ObjectId

import json, datetime

from ._base_model import BaseModel
from ._dictobj import DictObj


class JSONEncoder(json.JSONEncoder):
	def default(self, o):
		if isinstance(o, ObjectId):
			return str(o)
		elif isinstance(o, BaseModel) or isinstance(o, DictObj):
			return o._attrs()
		elif type(o) == datetime.datetime:
			return o.isoformat()
		elif type(o) == bytes:
			return True
		try:
			return json.JSONEncoder.default(self, o)
		except TypeError:
			return str(o)