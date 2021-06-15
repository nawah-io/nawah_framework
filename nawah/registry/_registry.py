from nawah.config import Config
from nawah.utils import _extract_attr
from nawah.classes import (
	SYS_DOC,
	JOB,
	InvalidModuleException,
	InvalidLocaleException,
	InvalidLocaleTermException,
	InvalidVarException,
)

from typing import Dict, List, Any, TYPE_CHECKING

import logging

if TYPE_CHECKING:
	from nawah.base_module import BaseModule

logger = logging.getLogger('nawah')


class Registry:
	docs: List[SYS_DOC] = Config.docs
	jobs: Dict[str, JOB] = Config.jobs

	@staticmethod
	def module(module: str) -> 'BaseModule':
		try:
			return Config.modules[module]
		except KeyError:
			raise InvalidModuleException(module=module)

	@staticmethod
	def l10n(*, locale: str, term: str):
		if locale not in Config.l10n.keys():
			raise InvalidLocaleException(locale=locale)

		try:
			if '.' in term:
				return _extract_attr(scope=Config.l10n[locale], attr_path=term)
			else:
				return Config.l10n[locale][term]
		except (KeyError, TypeError):
			raise InvalidLocaleTermException(locale=locale, term=term)

	@staticmethod
	def var(var: str):
		try:
			if '.' in var:
				return _extract_attr(scope=Config.vars, attr_path=var)
			else:
				return Config.vars[var]
		except (KeyError, TypeError):
			raise InvalidVarException(var=var)
