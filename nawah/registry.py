from nawah.config import Config
from nawah.base_module import BaseModule
from nawah.classes import SYS_DOC

from typing import Dict, List, Any

import logging

logger = logging.getLogger('nawah')


class InvalidModuleException(Exception):
	def __init__(self, *, module):
		self.module = module
		logger.debug(f'InvalidModuleException: {str(self)}')

	def __str__(self):
		return f'Invalid module \'{self.module}\''


class InvalidLocaleException(Exception):
	def __init__(self, *, locale):
		self.locale = locale
		logger.debug(f'InvalidLocaleException: {str(self)}')

	def __str__(self):
		return f'Invalid locale \'{self.locale}\''


class InvalidLocaleTermException(Exception):
	def __init__(self, *, locale, term):
		self.locale = locale
		self.term = term
		logger.debug(f'InvalidLocaleTermException: {str(self)}')

	def __str__(self):
		return f'Invalid term \'{self.term}\' of locale \'{self.locale}\''


class InvalidVarException(Exception):
	def __init__(self, *, var):
		self.var = var
		logger.debug(f'InvalidVarException: {str(self)}')

	def __str__(self):
		return f'Invalid var \'{self.var}\''


class Registry:
	docs: List[SYS_DOC] = Config.docs
	jobs: List[Dict[str, Any]] = Config.jobs

	@staticmethod
	def module(module: str) -> BaseModule:
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
				from nawah.utils import extract_attr

				return extract_attr(scope=Config.l10n[locale], attr_path=term)
			else:
				return Config.l10n[locale][term]
		except (KeyError, TypeError):
			raise InvalidLocaleTermException(locale=locale, term=term)

	@staticmethod
	def var(var: str):
		try:
			if '.' in var:
				from nawah.utils import extract_attr

				return extract_attr(scope=Config.vars, attr_path=var)
			else:
				return Config.vars[var]
		except (KeyError, TypeError):
			raise InvalidVarException(var=var)