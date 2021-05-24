from nawah.registry import Registry
from nawah.classes import NAWAH_QUERY, Query, NAWAH_DOC, PERM, ATTR_MOD
from nawah.utils import extract_attr

from typing import List, Dict, Union, Any, Iterable, TYPE_CHECKING

import copy, datetime, logging

if TYPE_CHECKING:
	from nawah.base_module import BaseModule

logger = logging.getLogger('nawah')


class InvalidPermissionsExcpetion(Exception):
	pass


def check_permissions(
	skip_events: List[str],
	env: Dict[str, Any],
	query: Union[NAWAH_QUERY, Query],
	doc: NAWAH_DOC,
	module: 'BaseModule',
	permissions: List[PERM],
):
	user = env['session'].user

	permissions = copy.deepcopy(permissions)

	for permission in permissions:
		logger.debug(f'checking permission: {permission} against: {user.privileges}')
		permission_pass = False
		if permission.privilege == '*':
			permission_pass = True

		if not permission_pass:
			if permission.privilege.find('.') == -1:
				permission_module = module.module_name
				permission_attr = permission.privilege
			elif permission.privilege.find('.') != -1:
				permission_module = permission.privilege.split('.')[0]
				permission_attr = permission.privilege.split('.')[1]

			if '*' in user.privileges.keys():
				user.privileges[permission_module] = copy.deepcopy(user.privileges['*'])
			if permission_module in user.privileges.keys():
				if (
					type(user.privileges[permission_module]) == list
					and '*' in user.privileges[permission_module]
				):
					user.privileges[permission_module] += copy.deepcopy(
						Registry.module(permission_module).privileges
					)
			if permission_module not in user.privileges.keys():
				user.privileges[permission_module] = []

			if permission_attr in user.privileges[permission_module]:
				permission_pass = True

		if permission_pass:
			query = _parse_permission_args(
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				permission_args=permission.query_mod,
			)
			doc = _parse_permission_args(
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				permission_args=permission.doc_mod,
			)
			return {'query': query, 'doc': doc}
	# [DOC] If all permission checks fail
	raise InvalidPermissionsExcpetion()


def _parse_permission_args(
	skip_events: List[str],
	env: Dict[str, Any],
	query: Union[NAWAH_QUERY, Query],
	doc: NAWAH_DOC,
	permission_args: Any,
):
	user = env['session'].user

	args_iter: Iterable

	if type(permission_args) == list:
		args_iter = range(len(permission_args))
	elif type(permission_args) == dict:
		args_iter = list(permission_args.keys())

	for j in args_iter:
		if type(permission_args[j]) == ATTR_MOD:
			# [DOC] If attr is of type ATTR_MOD, call condition callable
			if permission_args[j].condition(
				skip_events=skip_events, env=env, query=query, doc=doc, scope=doc
			):
				# [DOC] If condition return is True, update attr value
				if callable(permission_args[j].default):
					permission_args[j] = permission_args[j].default(
						skip_events=skip_events, env=env, query=query, doc=doc, scope=doc
					)
					if isinstance(permission_args[j], Exception):
						raise permission_args[j]
				else:
					permission_args[j] = permission_args[j].default
		elif type(permission_args[j]) == dict:
			# [DOC] Check opers
			for oper in [
				'$gt',
				'$lt',
				'$gte',
				'$lte',
				'$bet',
				'$ne',
				'$regex',
				'$all',
				'$in',
				'$nin',
			]:
				if oper in permission_args[j].keys():
					if oper == '$bet':
						permission_args[j]['$bet'] = _parse_permission_args(
							skip_events=skip_events,
							env=env,
							query=query,
							doc=doc,
							permission_args=permission_args[j]['$bet'],
						)
					else:
						permission_args[j][oper] = _parse_permission_args(
							skip_events=skip_events,
							env=env,
							query=query,
							doc=doc,
							permission_args={oper: permission_args[j][oper]},
						)[oper]
					# [DOC] Continue the iteration
					continue
			# [DOC] Child args, parse
			permission_args[j] = _parse_permission_args(
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				permission_args=permission_args[j],
			)
		elif type(permission_args[j]) == list:
			permission_args[j] = _parse_permission_args(
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				permission_args=permission_args[j],
			)
		elif type(permission_args[j]) == str:
			# [DOC] Check for variables
			if permission_args[j] == '$__user':
				permission_args[j] = user._id
			elif permission_args[j].startswith('$__user.'):
				try:
					permission_args[j] = extract_attr(
						scope=user,
						attr_path=permission_args[j].replace('$__user.', '$__'),
					)
				except Exception as e:
					# [TODO] Log exception
					# [DOC] For values that are expected to have a list value, return empty list
					if type(permission_args) == dict and j in ['$in', '$nin']:
						permission_args[j] = [None]
					else:
						permission_args[j] = None
			elif permission_args[j] == '$__access':
				permission_args[j] = {'$__user': user._id, '$__groups': user.groups}
			elif permission_args[j] == '$__datetime':
				permission_args[j] = datetime.datetime.utcnow().isoformat()
			elif permission_args[j] == '$__date':
				permission_args[j] = datetime.date.today().isoformat()
			elif permission_args[j] == '$__time':
				permission_args[j] = datetime.datetime.now().time().isoformat()

	return permission_args