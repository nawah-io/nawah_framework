from typing import Literal, Any

import logging

logger = logging.getLogger('nawah')


class InvalidPermissionsExcpetion(Exception):
	pass


class InvalidCallArgsException(Exception):
	pass


class InvalidAttrTypeException(Exception):
	def __init__(self, *, attr_type: Any):
		self.attr_type = attr_type

	def __str__(self):
		return f'Unknown or invalid Attr Type \'{self.attr_type}\'.'


class InvalidAttrTypeArgException(Exception):
	def __init__(self, *, arg_name: str, arg_type: Any, arg_val: Any):
		self.arg_name = arg_name
		self.arg_type = arg_type
		self.arg_val = arg_val

	def __str__(self):
		return f'Invalid Attr Type Arg for \'{self.arg_name}\' expecting type \'{self.arg_type}\' but got \'{self.arg_val}\'.'


class InvalidAttrTypeArgsException(Exception):
	def __init__(self, *, msg: str):
		self.msg = msg

	def __str__(self):
		return self.msg


class MethodException(Exception):
	pass


class InvalidQueryArgException(Exception):
	def __init__(
		self,
		*,
		arg_name: str,
		arg_oper: Literal[
			'$ne',
			'$eq',
			'$gt',
			'$gte',
			'$lt',
			'$lte',
			'$bet',
			'$all',
			'$in',
			'$nin',
			'$regex',
		],
		arg_type: Any,
		arg_val: Any,
	):
		self.arg_name = arg_name
		self.arg_oper = arg_oper
		self.arg_type = arg_type
		self.arg_val = arg_val

	def __str__(self):
		return f'Invalid value for Query Arg \'{self.arg_name}\' with Query Arg Oper \'{self.arg_oper}\' expecting type \'{self.arg_type}\' but got \'{self.arg_val}\'.'


class UnknownQueryArgException(Exception):
	def __init__(
		self,
		*,
		arg_name: str,
		arg_oper: Literal[
			'$ne',
			'$eq',
			'$gt',
			'$gte',
			'$lt',
			'$lte',
			'$bet',
			'$all',
			'$in',
			'$nin',
			'$regex',
		],
	):
		self.arg_name = arg_name
		self.arg_oper = arg_oper

	def __str__(self):
		return (
			f'Unknown Query Arg Oper \'{self.arg_oper}\' for Query Arg \'{self.arg_name}\'.'
		)


class MissingAttrException(Exception):
	def __init__(self, *, attr_name):
		self.attr_name = attr_name
		logger.debug(f'MissingAttrException: {str(self)}')

	def __str__(self):
		return f'Missing attr \'{self.attr_name}\''


class InvalidAttrException(Exception):
	def __init__(self, *, attr_name, attr_type, val_type):
		self.attr_name = attr_name
		self.attr_type = attr_type
		self.val_type = val_type
		logger.debug(f'InvalidAttrException: {str(self)}')

	def __str__(self):
		return f'Invalid attr \'{self.attr_name}\' of type \'{self.val_type}\' with required type \'{self.attr_type}\''


class ConvertAttrException(Exception):
	def __init__(self, *, attr_name, attr_type, val_type):
		self.attr_name = attr_name
		self.attr_type = attr_type
		self.val_type = val_type
		logger.debug(f'ConvertAttrException: {str(self)}')

	def __str__(self):
		return f'Can\'t convert attr \'{self.attr_name}\' of type \'{self.val_type}\' to type \'{self.attr_type._type}\''


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


class UnknownDeleteStrategyException(Exception):
	pass


class InvalidQueryException(Exception):
	pass


class InvalidGatewayException(Exception):
	def __init__(self, *, gateway):
		self.gateway = gateway

	def __str__(self):
		return f'Gateway \'{self.gateway}\' is invalid.'


class UnexpectedGatewayException(Exception):
	def __init__(self, *, gateway):
		self.gateway = gateway

	def __str__(self):
		return f'An unexpected gateway exception occurred when attempted to call \'{self.gateway}\'.'