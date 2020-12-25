from nawah.config import Config
from nawah.classes import (
	ATTR,
	ATTR_MOD,
	EXTN,
	CACHE,
	ANALYTIC,
	METHOD,
	NAWAH_MODULE,
)

from functools import wraps
from typing import Optional, Union, Dict, Any, List, Callable, TypeVar, cast, Type

NAWAH_MODULE_CLASS = TypeVar('NAWAH_MODULE_CLASS', bound=Callable[..., NAWAH_MODULE])


class nawah_module:
	def __init__(
		self,
		*,
		collection: Optional[Union[str, bool]] = None,
		proxy: Optional[str] = None,
		attrs: Optional[Dict[str, ATTR]] = None,
		diff: Optional[Union[bool, ATTR_MOD]] = None,
		defaults: Optional[Dict[str, Any]] = None,
		unique_attrs: Optional[List[str]] = None,
		extns: Optional[Dict[str, EXTN]] = None,
		privileges: Optional[List[str]] = None,
		methods: Optional[Dict[str, METHOD]] = None,
		cache: Optional[List[CACHE]] = None,
		analytics: Optional[List[ANALYTIC]] = None,
	) -> None:
		self.collection = collection
		self.proxy = proxy
		self.attrs = attrs
		self.diff = diff
		self.defaults = defaults
		self.unique_attrs = unique_attrs
		self.extns = extns
		self.privileges = privileges
		self.methods = methods
		self.cache = cache
		self.analytics = analytics

	def __call__(self, cls: Type[Any]) -> NAWAH_MODULE_CLASS:
		@wraps(cls)
		def wrapper() -> Any:
			return cls()

		return cast(NAWAH_MODULE_CLASS, wrapper)


# def nawah_module(
# 	*,
# 	collection: Optional[Union[str, bool]] = None,
# 	proxy: Optional[str] = None,
# 	attrs: Optional[Dict[str, ATTR]] = None,
# 	diff: Optional[Union[bool, ATTR_MOD]] = None,
# 	defaults: Optional[Dict[str, Any]] = None,
# 	unique_attrs: Optional[List[str]] = None,
# 	extns: Optional[Dict[str, EXTN]] = None,
# 	privileges: Optional[List[str]] = None,
# 	methods: Optional[Dict[str, METHOD]] = None,
# 	cache: Optional[List[CACHE]] = None,
# 	analytics: Optional[List[ANALYTIC]] = None,
# ) -> Callable[[Any], NAWAH_MODULE]:
# 	def nawah_module_decorator(cls):

# 		cls.collection = collection
# 		cls.proxy = proxy
# 		cls.attrs = attrs
# 		cls.diff = diff
# 		cls.defaults = defaults
# 		cls.unique_attrs = unique_attrs
# 		cls.extns = extns
# 		cls.privileges = privileges
# 		cls.methods = methods
# 		cls.cache = cache
# 		cls.analytics = analytics

# 		cls._instance = cls()

# 		pkgname = str(cls).split('.')[0].split('\'')[-1]
# 		clsname = str(cls).split('.')[-1].split('\'')[0]
# 		# [DOC] Deny loading Nawah-reserved named Nawah modules
# 		if clsname.lower() in ['conn', 'heart', 'watch']:
# 			logger.error(
# 				f'Module with Nawah-reserved name \'{clsname.lower()}\' was found. Exiting.'
# 			)
# 			exit(1)
# 		# [DOC] Load Nawah module and assign module_name attr
# 		module_name = re.sub(r'([A-Z])', r'_\1', clsname[0].lower() + clsname[1:]).lower()
# 		# [DOC] Deny duplicate Nawah modules names
# 		if module_name in Config.modules.keys():
# 			logger.error(f'Duplicate module name \'{module_name}\'. Exiting.')
# 			exit(1)
# 		# [DOC] Add module to loaded modules dict
# 		Config.modules[module_name] = cls._instance
# 		Config.modules_packages[pkgname].append(module_name)

# 		def wrapper():
# 			return cls._instance

# 		return wrapper
# 	return nawah_module_decorator