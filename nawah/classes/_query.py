from typing import (
	Literal,
	Any,
	Dict,
	List,
	Union,
	TypedDict,
	cast,
	Optional,
	TYPE_CHECKING,
)

import copy

from ._attr import SPECIAL_ATTRS
from ._dictobj import DictObj
from ._exceptions import InvalidQueryArgException, UnknownQueryArgException

if TYPE_CHECKING:
	from ._types import NAWAH_QUERY, NAWAH_QUERY_SPECIAL


QUERY_INDEX_RECORD = TypedDict(
	'QUERY_INDEX_RECORD', {'oper': str, 'path': str, 'val': Any}
)


class Query(list):
	_query: 'NAWAH_QUERY'
	_special: 'NAWAH_QUERY_SPECIAL'
	_index: Dict[str, List[QUERY_INDEX_RECORD]]

	def __init__(self, query: Union['NAWAH_QUERY', 'Query']):
		self._query = query
		if type(self._query) == Query:
			query = cast(Query, query)
			self._query = query._query + [query._special]
		self._special = {}
		self._index: Dict[str, List[QUERY_INDEX_RECORD]] = {}
		self._create_index(self._query)
		super().__init__(self._query)

	def __repr__(self):
		return str(self._query + [self._special])

	def _create_index(self, query: 'NAWAH_QUERY', path=[]):
		if not path:
			self._index: Dict[str, List[QUERY_INDEX_RECORD]] = {}
		for i in range(len(query)):
			if type(query[i]) == dict:
				del_attrs = []
				for attr in query[i].keys():
					if attr in SPECIAL_ATTRS.__args__:  # type: ignore
						self._special[attr] = query[i][attr]  # type: ignore
						del_attrs.append(attr)
					elif attr.startswith('__or'):
						self._create_index(query[i][attr], path=path + [i, attr])  # type: ignore
					else:
						if (
							type(query[i][attr]) == dict  # type: ignore
							and len(query[i][attr].keys()) == 1  # type: ignore
							and list(query[i][attr].keys())[0][0] == '$'  # type: ignore
						):
							attr_oper = list(query[i][attr].keys())[0]  # type: ignore
						else:
							attr_oper = '$eq'
						if attr not in self._index.keys():
							self._index[attr] = []
						if isinstance(query[i][attr], DictObj):  # type: ignore
							query[i][attr] = query[i][attr]._id  # type: ignore
						Query.validate_arg(arg_name=attr, arg_oper=attr_oper, arg_val=query[i][attr])  # type: ignore
						self._index[attr].append(
							{
								'oper': attr_oper,
								'path': path + [i],
								'val': query[i][attr],  # type: ignore
							}
						)
				for attr in del_attrs:
					del query[i][attr]  # type: ignore
			elif type(query[i]) == list:
				self._create_index(query[i], path=path + [i])  # type: ignore
		if not path:
			self._query = self._sanitise_query()

	def _sanitise_query(self, query: 'NAWAH_QUERY' = None):
		if query == None:
			query = self._query
		query = cast('NAWAH_QUERY', query)
		query_shadow = []
		for step in query:
			if type(step) == dict:
				for attr in step.keys():
					if attr.startswith('__or'):
						step[attr] = self._sanitise_query(step[attr])  # type: ignore
						if len(step[attr]):  # type: ignore
							query_shadow.append(step)
							break
					elif attr[0] != '$':
						query_shadow.append(step)
						break
			elif type(step) == list:
				step = self._sanitise_query(step)  # type: ignore
				if len(step):
					query_shadow.append(step)
		return query_shadow

	def __deepcopy__(self, memo):
		return Query(copy.deepcopy(self._query + [self._special]))

	def append(self, obj: Any):
		self._query.append(obj)
		self._create_index(self._query)
		super().__init__(self._query)

	def __contains__(self, attr: str):  # type: ignore
		if attr in SPECIAL_ATTRS.__args__:  # type: ignore
			return attr in self._special.keys()
		else:
			if ':' in attr:
				attr_index, attr_oper = attr.split(':')
			else:
				attr_index = attr
				attr += ':$eq'
				attr_oper = '$eq'

			if attr_index in self._index.keys():
				for val in self._index[attr_index]:
					if val['oper'] == attr_oper or attr_oper == '*':
						return True
			return False

	def __getitem__(self, attr: Union[SPECIAL_ATTRS, str]):  # type: ignore
		if attr in SPECIAL_ATTRS.__args__:  # type: ignore
			return self._special[attr]  # type: ignore
		else:
			attrs = []
			vals = []
			paths: List[List[int]] = []
			indexes = []
			attr_filter: Optional[str] = None
			oper_filter: Optional[str] = None

			if attr.split(':')[0] != '*':
				attr_filter = attr.split(':')[0]

			if ':' not in attr:
				oper_filter = '$eq'
				attr += ':$eq'
			elif ':*' not in attr:
				oper_filter = attr.split(':')[1]

			for index_attr in self._index.keys():
				if attr_filter and index_attr != attr_filter:
					continue
				i = 0
				for val in self._index[index_attr]:
					if not oper_filter or (oper_filter and val['oper'] == oper_filter):
						attrs.append(index_attr)
						# [TODO] Simplify this condition by enforcing Query Args with $eq Query Oper are always stripped down to value
						if not oper_filter or (
							oper_filter == '$eq'
							and (type(val['val']) != dict or '$eq' not in val['val'].keys())
						):
							vals.append(val['val'])
						else:
							vals.append(val['val'][oper_filter])
						paths.append(val['path'])
						indexes.append(i)
						i += 1
			return QueryAttrList(self, attrs, paths, indexes, vals)

	def __setitem__(self, attr: str, val: Any):  # type: ignore
		if attr[0] != '$':
			raise Exception('Non-special attrs can only be updated by attr index.')
		self._special[attr] = val  # type: ignore

	def __delitem__(self, attr: str):  # type: ignore
		if attr[0] != '$':
			raise Exception('Non-special attrs can only be deleted by attr index.')
		del self._special[attr]  # type: ignore

	@classmethod
	def validate_arg(cls, *, arg_name, arg_oper, arg_val):
		if arg_oper in ['$ne', '$eq']:
			return
		elif arg_oper in ['$gt', '$gte', '$lt', '$lte']:
			if type(arg_val[arg_oper]) not in [str, int, float]:
				raise InvalidQueryArgException(
					arg_name=arg_name,
					arg_oper=arg_oper,
					arg_type=[str, int, float],
					arg_val=arg_val[arg_oper],
				)
		elif arg_oper == '$bet':
			if (
				type(arg_val[arg_oper]) != list
				or len(arg_val[arg_oper]) != 2
				or type(arg_val[arg_oper][0]) not in [str, int, float]
				or type(arg_val[arg_oper][1]) not in [str, int, float]
			):
				raise InvalidQueryArgException(
					arg_name=arg_name,
					arg_oper=arg_oper,
					arg_type=list,
					arg_val=arg_val[arg_oper],
				)
		elif arg_oper in ['$all', '$in', '$nin']:
			if type(arg_val[arg_oper]) != list or not len(arg_val[arg_oper]):
				raise InvalidQueryArgException(
					arg_name=arg_name,
					arg_oper=arg_oper,
					arg_type=list,
					arg_val=arg_val[arg_oper],
				)
		elif arg_oper == '$regex':
			if type(arg_val[arg_oper]) != str:
				raise InvalidQueryArgException(
					arg_name=arg_name,
					arg_oper=arg_oper,
					arg_type=str,
					arg_val=arg_val[arg_oper],
				)
		else:
			raise UnknownQueryArgException(arg_name=arg_name, arg_oper=arg_oper)


class QueryAttrList(list):
	def __init__(
		self,
		query: Query,
		attrs: List[str],
		paths: List[List[int]],
		indexes: List[int],
		vals: List[Any],
	):
		self._query = query
		self._attrs = attrs
		self._paths = paths
		self._indexes = indexes
		self._vals = vals
		super().__init__(vals)

	def __setitem__(self, item: Union[Literal['*'], int], val: Any):  # type: ignore
		if item == '*':
			for i in range(len(self._vals)):
				self.__setitem__(i, val)
		else:
			instance_attr = self._query._query
			for path_part in self._paths[item]:
				instance_attr = instance_attr[path_part]  # type: ignore
			instance_attr[self._attrs[item].split(':')[0]] = val  # type: ignore
			self._query._create_index(self._query._query)

	def __delitem__(self, item: Union[Literal['*'], int]):  # type: ignore
		if item == '*':
			for i in range(len(self._vals)):
				self.__delitem__(i)
		else:
			instance_attr = self._query._query
			for path_part in self._paths[item]:
				instance_attr = instance_attr[path_part]  # type: ignore
			del instance_attr[self._attrs[item].split(':')[0]]  # type: ignore
			self._query._create_index(self._query._query)

	def replace_attr(self, item: Union[Literal['*'], int], new_attr: str):
		if item == '*':
			for i in range(len(self._vals)):
				self.replace_attr(i, new_attr)
		else:
			instance_attr = self._query._query
			for path_part in self._paths[item]:
				instance_attr = instance_attr[path_part]  # type: ignore
			# [DOC] Set new attr
			instance_attr[new_attr] = instance_attr[self._attrs[item].split(':')[0]]  # type: ignore
			# [DOC] Delete old attr
			del instance_attr[self._attrs[item].split(':')[0]]  # type: ignore
			# [DOC] Update index
			self._query._create_index(self._query._query)