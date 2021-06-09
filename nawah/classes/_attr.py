from nawah.enums import NAWAH_VALUES

from bson import ObjectId
from typing import (
	Dict,
	Union,
	Type,
	List,
	Sequence,
	Any,
	Literal,
	Callable,
	Optional,
	ForwardRef,
	TYPE_CHECKING,
	Protocol,
)

import datetime, logging, re, inspect

from ._package import SYS_DOC
from ._exceptions import (
	InvalidAttrTypeException,
	InvalidAttrTypeArgException,
	InvalidAttrTypeArgsException,
)

if TYPE_CHECKING:
	from ._module import EXTN
	from ._types import NAWAH_EVENTS, NAWAH_ENV, NAWAH_QUERY, NAWAH_DOC, NAWAH_DOC
	from ._query import Query

logger = logging.getLogger('nawah')

ATTRS_TYPES_ARGS: Dict[str, Dict[str, Union[Type, str]]] = {
	'ANY': {},
	'ACCESS': {},
	'COUNTER': {'pattern': str},
	'ID': {},
	'STR': {'pattern': str},
	'INT': {'ranges': List[List[int]]},
	'FLOAT': {'ranges': List[List[float]]},
	'BOOL': {},
	'LOCALE': {},
	'LOCALES': {},
	'EMAIL': {
		'allowed_domains': List[str],
		'disallowed_domains': List[str],
		'strict_matching': bool,
	},
	'PHONE': {'codes': List[str]},
	'IP': {},
	'URI_WEB': {
		'allowed_domains': List[str],
		'disallowed_domains': List[str],
		'strict_matching': bool,
	},
	'DATETIME': {'ranges': List[List[datetime.datetime]]},
	'DATE': {'ranges': List[List[datetime.date]]},
	'DYNAMIC_ATTR': {'types': List[str]},
	'DYNAMIC_VAL': {'dynamic_attr': str},
	'TIME': {'ranges': List[List[datetime.time]]},
	'FILE': {
		'types': List[str],
		'max_ratio': List[int],
		'min_ratio': List[int],
		'max_dims': List[int],
		'min_dims': List[int],
		'max_size': int,
	},
	'GEO': {},
	'LIST': {'list': List['ATTR'], 'min': int, 'max': int},
	'KV_DICT': {
		'key': 'ATTR',
		'val': 'ATTR',
		'min': int,
		'max': int,
		'req': List[str],
	},
	'TYPED_DICT': {'dict': Dict[str, 'ATTR']},
	'LITERAL': {'literal': List[Union[str, int, float, bool]]},
	'UNION': {'union': List['ATTR']},
	'TYPE': {'type': str},
}

SPECIAL_ATTRS = Literal[
	'$search', '$sort', '$skip', '$limit', '$extn', '$attrs', '$group', '$geo_near'
]


class ATTR_TYPE_CALLABLE_TYPE(Protocol):
	def __call__(
		*,
		self,
		mode: Literal['create', 'create_draft', 'update'],
		attr_name: str,
		attr_type: 'ATTR',
		attr_val: Any,
		skip_events: 'NAWAH_EVENTS',
		env: 'NAWAH_ENV',
		query: Union['NAWAH_QUERY', 'Query'],
		doc: 'NAWAH_DOC',
		scope: Optional['NAWAH_DOC'],
	) -> Any:
		...


ATTRS_TYPES_TYPE = Literal[
	'ANY',
	'ACCESS',
	'COUNTER',
	'ID',
	'STR',
	'INT',
	'FLOAT',
	'BOOL',
	'LOCALE',
	'LOCALES',
	'EMAIL',
	'PHONE',
	'IP',
	'URI_WEB',
	'DATETIME',
	'DATE',
	'DYNAMIC_ATTR',
	'DYNAMIC_VAL',
	'TIME',
	'FILE',
	'GEO',
	'LIST',
	'KV_DICT',
	'TYPED_DICT',
	'LITERAL',
	'UNION',
	'TYPE',
]


class ATTR:
	_nawah_attr: bool = True
	_type: ATTRS_TYPES_TYPE
	_desc: Optional[str]
	_args: Dict[str, Any]
	_valid: bool = False
	_extn: Optional[Union['EXTN', 'ATTR']] = None

	__default = NAWAH_VALUES.NONE_VALUE

	@property
	def _default(self):
		if self.__default == '$__datetime':
			return datetime.datetime.utcnow().isoformat()
		elif self.__default == '$__date':
			return datetime.date.today().isoformat()
		elif self.__default == '$__time':
			return datetime.datetime.now().time().isoformat()
		else:
			return self.__default

	@_default.setter
	def _default(self, value):
		self.__default = value

	def __repr__(self):
		return f'<ATTR:{self._type},{self._args}>'

	def __init__(self, *, attr_type: ATTRS_TYPES_TYPE, desc: str = None, **kwargs: Any):
		self._type = attr_type
		self._desc = desc
		self._args = kwargs
		ATTR.validate_type(attr_type=self, skip_type=True)

	@classmethod
	def ANY(cls, *, desc: str = None):
		return ATTR(attr_type='ANY', desc=desc)

	@classmethod
	def ACCESS(cls, *, desc: str = None):
		return ATTR(attr_type='ACCESS', desc=desc)

	@classmethod
	def COUNTER(cls, *, desc: str = None, pattern: str, values: List[Callable] = None):
		return ATTR(attr_type='COUNTER', desc=desc, pattern=pattern, values=values)

	@classmethod
	def ID(cls, *, desc: str = None):
		return ATTR(attr_type='ID', desc=desc)

	@classmethod
	def STR(cls, *, desc: str = None, pattern: str = None):
		return ATTR(attr_type='STR', desc=desc, pattern=pattern)

	@classmethod
	def INT(cls, *, desc: str = None, ranges: List[List[int]] = None):
		return ATTR(attr_type='INT', desc=desc, ranges=ranges)

	@classmethod
	def FLOAT(cls, *, desc: str = None, ranges: List[List[int]] = None):
		return ATTR(attr_type='FLOAT', desc=desc, ranges=ranges)

	@classmethod
	def BOOL(cls, *, desc: str = None):
		return ATTR(attr_type='BOOL', desc=desc)

	@classmethod
	def LOCALE(cls, *, desc: str = None):
		return ATTR(attr_type='LOCALE', desc=desc)

	@classmethod
	def LOCALES(cls, *, desc: str = None):
		return ATTR(attr_type='LOCALES', desc=desc)

	@classmethod
	def EMAIL(
		cls,
		*,
		desc: str = None,
		allowed_domains: List[str] = None,
		disallowed_domains: List[str] = None,
		strict: bool = False,
	):
		return ATTR(
			attr_type='EMAIL',
			desc=desc,
			allowed_domains=allowed_domains,
			disallowed_domains=disallowed_domains,
			strict=strict,
		)

	@classmethod
	def PHONE(cls, *, desc: str = None, codes: List[str] = None):
		return ATTR(attr_type='PHONE', desc=desc, codes=codes)

	@classmethod
	def IP(cls, *, desc: str = None):
		return ATTR(attr_type='IP', desc=desc)

	@classmethod
	def URI_WEB(
		cls,
		*,
		desc: str = None,
		allowed_domains: List[str] = None,
		disallowed_domains: List[str] = None,
		strict: bool = False,
	):
		return ATTR(
			attr_type='URI_WEB',
			desc=desc,
			allowed_domains=allowed_domains,
			disallowed_domains=disallowed_domains,
			strict=strict,
		)

	@classmethod
	def DATETIME(cls, *, desc: str = None, ranges: List[List[str]] = None):
		return ATTR(attr_type='DATETIME', desc=desc, ranges=ranges)

	@classmethod
	def DATE(cls, *, desc: str = None, ranges: List[List[str]] = None):
		return ATTR(attr_type='DATE', desc=desc, ranges=ranges)

	@classmethod
	def DYNAMIC_ATTR(cls, *, desc: str = None, types: List[str] = None):
		return ATTR(attr_type='DYNAMIC_ATTR', desc=desc, types=types)

	@classmethod
	def DYNAMIC_VAL(cls, *, desc: str = None, dynamic_attr: str):
		return ATTR(attr_type='DYNAMIC_VAL', desc=desc, dynamic_attr=dynamic_attr)

	@classmethod
	def TIME(cls, *, desc: str = None, ranges: List[List[str]] = None):
		return ATTR(attr_type='TIME', desc=desc, ranges=ranges)

	@classmethod
	def FILE(
		cls,
		*,
		desc: str = None,
		types: List[str] = None,
		max_ratio: List[int] = None,
		min_ratio: List[int] = None,
		max_dims: List[int] = None,
		min_dims: List[int] = None,
		max_size: int = None,
	):
		return ATTR(
			attr_type='FILE',
			desc=desc,
			types=types,
			max_ratio=max_ratio,
			min_ratio=min_ratio,
			max_dims=max_dims,
			min_dims=min_dims,
			max_size=max_size,
		)

	@classmethod
	def GEO(cls, *, desc: str = None):
		return ATTR(attr_type='GEO', desc=desc)

	@classmethod
	def LIST(
		cls,
		*,
		desc: str = None,
		list: List['ATTR'],
		min: int = None,
		max: int = None,
	):
		return ATTR(attr_type='LIST', desc=desc, list=list, min=min, max=max)

	@classmethod
	def KV_DICT(
		cls,
		*,
		desc: str = None,
		key: 'ATTR',
		val: 'ATTR',
		min: int = None,
		max: int = None,
		req: List[str] = None,
	):
		return ATTR(
			attr_type='KV_DICT', desc=desc, key=key, val=val, min=min, max=max, req=req
		)

	@classmethod
	def TYPED_DICT(cls, *, desc: str = None, dict: Dict[str, 'ATTR']):
		return ATTR(attr_type='TYPED_DICT', desc=desc, dict=dict)

	@classmethod
	def LITERAL(cls, *, desc: str = None, literal: Sequence[Union[str, int, float, bool]]):
		return ATTR(attr_type='LITERAL', desc=desc, literal=literal)

	@classmethod
	def UNION(cls, *, desc: str = None, union: List['ATTR']):
		return ATTR(attr_type='UNION', desc=desc, union=union)

	@classmethod
	def TYPE(cls, *, desc: str = None, type: Union[str, ATTR_TYPE_CALLABLE_TYPE]):
		return ATTR(attr_type='TYPE', desc=desc, type=type)

	@classmethod
	def validate_type(cls, *, attr_type: 'ATTR', skip_type: bool = False):
		from nawah.config import Config

		# [DOC] Skip validating Attr Type if it is already validated, unless we want to validate TYPE, which could require deep (nested) validation
		if skip_type and attr_type._valid:
			return

		if attr_type._type not in ATTRS_TYPES_ARGS.keys():
			raise InvalidAttrTypeException(attr_type=attr_type)
		elif not skip_type and attr_type._type == 'TYPE':
			# [DOC] Complex condition is unreadblae in single condition set, break into multiple conditions as try..except block
			try:
				if type(attr_type._args['type']) == str:
					if attr_type._args['type'] not in Config.types.keys():
						raise Exception()
					if not inspect.iscoroutinefunction(Config.types[attr_type._args['type']]):
						raise Exception()
					# [DOC] Assign new Attr Type Arg for shorthand calling the TYPE function
					attr_type._args['func'] = Config.types[attr_type._args['type']]
				else:
					if not inspect.iscoroutinefunction(attr_type._args['type']):
						raise Exception()
					# [DOC] Assign new Attr Type Arg for shorthand calling the TYPE function
					attr_type._args['func'] = attr_type._args['type']
			except:
				raise InvalidAttrTypeException(attr_type=attr_type)
		elif attr_type._type != 'TYPE':
			for arg in ATTRS_TYPES_ARGS[attr_type._type].keys():
				if (
					arg in ['list', 'dict', 'literal', 'union', 'type']
					and arg not in attr_type._args.keys()
				):
					raise InvalidAttrTypeArgException(
						arg_name=arg,
						arg_type=ATTRS_TYPES_ARGS[attr_type._type][arg],
						arg_val=attr_type._args[arg],
					)
				elif arg in attr_type._args.keys() and attr_type._args[arg] != None:
					cls.validate_arg(
						arg_name=arg,
						arg_type=ATTRS_TYPES_ARGS[attr_type._type][arg],
						arg_val=attr_type._args[arg],
						skip_type=skip_type,
					)
				else:
					attr_type._args[arg] = None
			if attr_type._type == 'COUNTER':
				if (
					'$__values.' in attr_type._args['pattern']
					or '$__counters:' in attr_type._args['pattern']
				):
					logger.error(
						'Attr Type COUNTER is using wrong format for \'$__values\', or \'$__counters\'.'
					)
					raise InvalidAttrTypeException(attr_type=attr_type)
				counter_groups = re.findall(
					r'(\$__(?:values:[0-9]+|counters\.[a-z0-9_]+))',
					attr_type._args['pattern'],
				)
				if len(counter_groups) == 0:
					logger.error(
						'Attr Type COUNTER is not having any \'$__values\', or \'$__counters\'.'
					)
					raise InvalidAttrTypeException(attr_type=attr_type)
				if '$__counters.' not in attr_type._args['pattern']:
					logger.warning('Attr Type COUNTER is defined with not \'$__counters\'.')
				for group in counter_groups:
					if group.startswith('$__counters.'):
						Config.docs.append(
							SYS_DOC(
								module='setting',
								key='var',
								doc={
									'user': ObjectId('f00000000000000000000010'),
									'var': '__counter:' + group.replace('$__counters.', ''),
									'val_type': {'type': 'INT', 'args': {}, 'allow_none': False, 'default': None},
									'val': 0,
									'type': 'global',
								},
							)
						)
			attr_type._valid = True

	@classmethod
	def validate_arg(cls, *, arg_name: str, arg_type: Any, arg_val: Any, skip_type: bool):
		if arg_type == str:
			if type(arg_val) != str:
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			return
		elif arg_type == int:
			if type(arg_val) != int:
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			return
		elif arg_type == float:
			if type(arg_val) not in [float, int]:
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			return
		elif arg_type == bool:
			if type(arg_val) != bool:
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			return
		elif type(arg_type) == ForwardRef or (type(arg_type) == str and arg_type == 'ATTR'):
			if type(arg_val) != ATTR:
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			if arg_name == 'key':
				if arg_val._type not in ['STR', 'LITERAL']:
					raise InvalidAttrTypeArgException(
						arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
					)
			return
		elif arg_name == 'literal':
			if type(arg_val) != list:
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			for arg_val_child in arg_val:
				if type(arg_val_child) not in arg_type.__args__[0].__args__:
					raise InvalidAttrTypeArgException(
						arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
					)
			return
		elif arg_name == 'union':
			if type(arg_val) != list:
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			for arg_val_child in arg_val:
				if type(arg_val_child) != ATTR:
					raise InvalidAttrTypeArgException(
						arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
					)
				ATTR.validate_type(attr_type=arg_val_child, skip_type=skip_type)
			return
		elif arg_type == datetime.date:
			if not re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$', arg_val) and not re.match(
				r'^[\-\+][0-9]+[dsmhw]$', arg_val
			):
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			return
		elif arg_type == datetime.datetime:
			if (
				not re.match(
					r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{6})?)?$',
					arg_val,
				)
				and not re.match(r'^[\-\+][0-9]+[dsmhw]$', arg_val)
			):
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			return
		elif arg_type == datetime.time:
			if not re.match(
				r'^[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{6})?)?$', arg_val
			) and not re.match(r'^[\-\+][0-9]+[dsmhw]$', arg_val):
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			return
		elif arg_type._name == 'List':
			if type(arg_val) != list:
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			for arg_val_child in arg_val:
				cls.validate_arg(
					arg_name=arg_name,
					arg_type=arg_type.__args__[0],
					arg_val=arg_val_child,
					skip_type=skip_type,
				)

				# [DOC] In Addition to validating as list arg, check for ATTR and validate
				if type(arg_val_child) == ATTR:
					ATTR.validate_type(attr_type=arg_val_child, skip_type=skip_type)

			return
		elif arg_type._name == 'Dict':
			if type(arg_val) != dict:
				raise InvalidAttrTypeArgException(
					arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
				)
			for arg_val_child in arg_val.keys():
				if type(arg_val[arg_val_child]) != ATTR:
					raise InvalidAttrTypeArgException(
						arg_name=arg_name, arg_type=arg_type, arg_val=arg_val[arg_val_child]
					)
				ATTR.validate_type(attr_type=arg_val[arg_val_child], skip_type=skip_type)
			return

		raise InvalidAttrTypeArgException(
			arg_name=arg_name, arg_type=arg_type, arg_val=arg_val
		)
