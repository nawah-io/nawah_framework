from nawah.config import Config
from nawah.enums import Event, NAWAH_VALUES, LOCALE_STRATEGY
from nawah.utils import extract_attr
from nawah.classes import (
	ATTR,
	NAWAH_ENV,
	NAWAH_QUERY,
	Query,
	NAWAH_DOC,
	ATTR_MOD,
	BaseModel,
	DictObj,
	ATTRS_TYPES_ARGS,
	InvalidAttrTypeException,
	NAWAH_EVENTS,
)

from bson import binary, ObjectId
from typing import Dict, Optional, List, Union, Any, cast, Literal, Tuple, TYPE_CHECKING

import logging, copy, re, asyncio, datetime

if TYPE_CHECKING:
	from nawah.base_module import BaseModule

logger = logging.getLogger('nawah')


async def process_file_obj(
	*, doc: Union[NAWAH_DOC, dict, list], modules: Dict[str, 'BaseModule'], env: NAWAH_ENV
):
	if type(doc) == dict:
		doc_iter = doc.keys()  # type: ignore
	elif type(doc) == list:
		doc_iter = range(len(doc))
	for j in doc_iter:
		if type(doc[j]) == dict:  # type: ignore
			if '__file' in doc[j].keys():  # type: ignore
				file_id = doc[j]['__file']  # type: ignore
				logger.debug(
					f'Detected file in doc. Retrieving file from File module with _id: \'{file_id}\'.'
				)
				try:
					file_results = await modules['file'].read(
						skip_events=[Event.PERM], env=env, query=[{'_id': file_id}]
					)
					doc[j] = file_results.args.docs[0].file  # type: ignore
					file_results = await modules['file'].delete(
						skip_events=[Event.PERM, Event.SOFT],
						env=env,
						query=[{'_id': file_id}],
					)
					if file_results.status != 200 or file_results.args.count != 1:
						logger.warning(
							f'Filed to delete doc _id \'{file_id}\' from File module after retrieving.'
						)
				except Exception as e:
					logger.error(f'Failed to retrieve doc _id \'{file_id}\', with error:')
					logger.error(e)
					doc[j] = None  # type: ignore
			else:
				await process_file_obj(doc=doc[j], modules=modules, env=env)  # type: ignore
		elif type(doc[j]) == list:  # type: ignore
			await process_file_obj(doc=doc[j], modules=modules, env=env)  # type: ignore


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
		return f'Invalid attr \'{self.attr_name}\' of type \'{self.val_type}\' with required type \'{self.attr_type._type}\''


class ConvertAttrException(Exception):
	def __init__(self, *, attr_name, attr_type, val_type):
		self.attr_name = attr_name
		self.attr_type = attr_type
		self.val_type = val_type
		logger.debug(f'ConvertAttrException: {str(self)}')

	def __str__(self):
		return f'Can\'t convert attr \'{self.attr_name}\' of type \'{self.val_type}\' to type \'{self.attr_type._type}\''


async def validate_doc(
	*,
	mode: Literal['create', 'create_draft', 'update'],
	doc: NAWAH_DOC,
	attrs: Dict[str, ATTR],
	skip_events: NAWAH_EVENTS = None,
	env: NAWAH_ENV = None,
	query: Union[NAWAH_QUERY, Query] = None,
):
	attrs_map = {attr.split('.')[0]: attr for attr in doc.keys()}

	for attr in attrs.keys():
		if attr not in attrs_map.keys():
			if mode == 'create':
				doc[attr] = None
			else:
				continue
		elif mode != 'create' and doc[attrs_map[attr]] == None:
			continue
		elif mode != 'create' and doc[attrs_map[attr]] != None:
			attr = attrs_map[attr]

		try:
			env = cast(NAWAH_ENV, env)
			if mode != 'create' and '.' in attr:
				doc[attr] = await validate_dot_notated(
					attr=attr,
					doc=doc,
					attrs=attrs,
					skip_events=skip_events,
					env=env,
					query=query,
				)
			else:
				doc[attr] = await validate_attr(
					attr_name=attr,
					attr_type=attrs[attr],
					attr_val=doc[attr],
					mode=mode,
					skip_events=skip_events,
					env=env,
					query=query,
					doc=doc,
				)
		except Exception as e:
			if type(e) in [InvalidAttrException, ConvertAttrException]:
				if doc[attr] == None:
					raise MissingAttrException(attr_name=attr)
				else:
					raise e
			else:
				raise e


async def validate_dot_notated(
	attr: str,
	doc: NAWAH_DOC,
	attrs: Dict[str, ATTR],
	skip_events: Optional[NAWAH_EVENTS],
	env: Optional[NAWAH_ENV],
	query: Optional[Union[NAWAH_QUERY, Query]],
):
	attr_path = attr.split('.')
	attr_path_len = len(attr_path)
	attr_type: Union[Dict[str, ATTR], ATTR] = attrs

	try:
		for i in range(attr_path_len):
			# [DOC] Iterate over attr_path to reach last valid Attr Type
			if type(attr_type) == dict:
				attr_type = cast(dict, attr_type)
				attr_type = attr_type[attr_path[i]]
			elif type(attr_type) == ATTR:
				attr_type = cast(ATTR, attr_type)
				if attr_type._type == 'ANY':
					return doc[attr]
				elif attr_type._type == 'LOCALE':
					if attr_path[i] not in Config.locales:
						raise Exception()
					attr_type = ATTR.STR()
				elif attr_type._type == 'TYPED_DICT':
					attr_type = attr_type._args['dict'][attr_path[i]]
				elif attr_type._type == 'KV_DICT':
					attr_type = attr_type._args['val']
				# [DOC] However, if list or union, start a new validate_dot_notated call as it is required to check all the provided types
				elif attr_type._type in ['LIST', 'UNION']:
					if attr_type._type == 'LIST':
						attr_type_iter = attr_type._args['list']
					else:
						attr_type_iter = attr_type._args['union']
					for child_attr_type in attr_type_iter:
						attr_val = await validate_dot_notated(
							attr='.'.join(attr_path[i:]),
							doc={'.'.join(attr_path[i:]): doc[attr]},
							attrs={attr_path[i]: child_attr_type},
							skip_events=skip_events,
							env=env,
							query=query,
						)
						if attr_val != None:
							return attr_val
					raise Exception()
				else:
					raise Exception()
			else:
				raise Exception()

		attr_type = cast(ATTR, attr_type)
		# [DOC] Validate val against final Attr Type
		# [DOC] mode is statically set to update as dot-notation attrs are only allowed in update calls
		env = cast(NAWAH_ENV, env)
		attr_val = await validate_attr(
			mode='update',
			attr_name=attr,
			attr_type=attr_type,
			attr_val=doc[attr],
			skip_events=skip_events,
			env=env,
			query=query,
			doc=doc,
		)
		return attr_val
	except:
		raise InvalidAttrException(
			attr_name=attr, attr_type=attrs[attr_path[0]], val_type=type(doc[attr])
		)


async def validate_default(
	*,
	mode: Literal['create', 'create_draft', 'update'],
	attr_type: ATTR,
	attr_val: Any,
	skip_events: NAWAH_EVENTS,
	env: NAWAH_ENV,
	query: Union[NAWAH_QUERY, Query],
	doc: NAWAH_DOC,
	scope: NAWAH_DOC,
):
	if mode == 'create' and type(attr_type._default) == ATTR_MOD:
		attr_type._default = cast(ATTR_MOD, attr_type._default)
		if attr_type._default.condition(
			skip_events=skip_events, env=env, query=query, doc=doc, scope=scope
		):
			if callable(attr_type._default.default):
				attr_val = attr_type._default.default(
					skip_events=skip_events, env=env, query=query, doc=doc, scope=scope
				)
			else:
				attr_val = attr_type._default.default
			return copy.deepcopy(attr_val)

	elif attr_type._type == 'COUNTER':
		counter_groups = re.findall(
			r'(\$__(?:values:[0-9]+|counters\.[a-z0-9_]+))', attr_type._args['pattern']
		)
		counter_val = attr_type._args['pattern']
		for group in counter_groups:
			for group in counter_groups:
				if group.startswith('$__values:'):
					value_callable = attr_type._args['values'][int(group.replace('$__values:', ''))]
					counter_val = counter_val.replace(
						group, str(value_callable(skip_events=skip_events, env=env, query=query, doc=doc))
					)
				elif group.startswith('$__counters.'):
					env = cast(NAWAH_ENV, env)
					counter_name = group.replace('$__counters.', '')
					setting_read_results = await Config.modules['setting'].read(
						skip_events=[Event.PERM],
						env=env,
						query=[
							{
								'var': '__counter:' + counter_name,
								'type': 'global',
							}
						],
					)
					setting = setting_read_results.args.docs[0]
					setting_update_results = asyncio.create_task(
						Config.modules['setting'].update(
							skip_events=[Event.PERM],
							env=env,
							query=[{'_id': setting._id, 'type': 'global'}],
							doc={'val': {'$add': 1}},
						)
					)
					# [DOC] Condition "not task.cancelled()" is added to avoid exceptions with the task getting cancelled during its run as such it might be running in test mode, or at time of shutting down Nawah
					setting_update_results.add_done_callback(
						setting_update_callback_wrapper(counter_name)
					)
					counter_val = counter_val.replace(group, str(setting.val + 1))
		return counter_val

	elif attr_val == None:
		if mode != 'create':
			return attr_val
		elif attr_type._default != NAWAH_VALUES.NONE_VALUE:
			return copy.deepcopy(attr_type._default)

	raise Exception('No default set to validate.')


def setting_update_callback_wrapper(counter_name):
	def setting_update_callback(task):
		if not task.cancelled() and task.result().status != 200:
			logger.error(f'Failed to update Setting doc for counter \'{counter_name}\'')

	return setting_update_callback


async def validate_attr(
	*,
	mode: Literal['create', 'create_draft', 'update'],
	attr_name: str,
	attr_type: ATTR,
	attr_val: Any,
	skip_events: NAWAH_EVENTS = None,
	env: NAWAH_ENV = None,
	query: Union[NAWAH_QUERY, Query] = None,
	doc: NAWAH_DOC = None,
	scope: NAWAH_DOC = None,
):
	try:
		skip_events = cast(NAWAH_EVENTS, skip_events)
		env = cast(NAWAH_ENV, env)
		query = cast(Union[NAWAH_QUERY, Query], query)
		doc = cast(NAWAH_DOC, doc)
		return await validate_default(
			mode=mode,
			attr_type=attr_type,
			attr_val=attr_val,
			skip_events=skip_events,
			env=env,
			query=query,
			doc=doc,
			scope=scope if scope else doc,
		)
	except:
		pass

	attr_oper: Literal[
		None, '$add', '$multiply', '$append', '$set_index', '$del_val', '$del_index'
	] = None
	attr_oper_args = {}
	if mode == 'update' and type(attr_val) == dict:
		if '$add' in attr_val.keys():
			attr_oper = '$add'
			if '$field' in attr_val.keys() and attr_val['$field']:
				attr_oper_args['$field'] = attr_val['$field']
			else:
				attr_oper_args['$field'] = None
			attr_val = attr_val['$add']
		elif '$multiply' in attr_val.keys():
			attr_oper = '$multiply'
			if '$field' in attr_val.keys() and attr_val['$field']:
				attr_oper_args['$field'] = attr_val['$field']
			else:
				attr_oper_args['$field'] = None
			attr_val = attr_val['$multiply']
		elif '$append' in attr_val.keys():
			attr_oper = '$append'
			if '$unique' in attr_val.keys() and attr_val['$unique'] == True:
				attr_oper_args['$unique'] = True
			else:
				attr_oper_args['$unique'] = False
			attr_val = [attr_val['$append']]
		elif '$set_index' in attr_val.keys():
			attr_oper = '$set_index'
			attr_oper_args['$index'] = attr_val['$set_index']
			attr_val = [attr_val['$set_index']]
		elif '$del_val' in attr_val.keys():
			attr_oper = '$del_val'
			attr_val = attr_val['$del_val']
			if attr_type._type != 'LIST' or type(attr_val) != list:
				raise InvalidAttrException(
					attr_name=attr_name, attr_type=attr_type, val_type=type(attr_val)
				)
			return return_valid_attr(
				attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
			)
		elif '$del_index' in attr_val.keys():
			attr_oper = '$del_index'
			attr_oper_args['$index'] = attr_val['$del_index']
			attr_val = attr_val['$del_index']
			if (attr_type._type == 'LIST' and type(attr_val) == int) or (
				attr_type._type == 'KV_DICT' and type(attr_val) == str
			):
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)
			else:
				raise InvalidAttrException(
					attr_name=attr_name, attr_type=attr_type, val_type=type(attr_val)
				)

	# [DOC] Deepcopy attr_val to eliminate changes in in original object
	attr_val = copy.deepcopy(attr_val)

	try:
		if attr_type._type == 'ANY':
			if attr_val != None:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'ACCESS':
			if (
				type(attr_val) == dict
				and set(attr_val.keys()) == {'anon', 'users', 'groups'}
				and type(attr_val['anon']) == bool
				and type(attr_val['users']) == list
				and type(attr_val['groups']) == list
			):
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'BOOL':
			if type(attr_val) == bool:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'DATE':
			if re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}$', attr_val):
				if attr_type._args['ranges']:
					for date_range in attr_type._args['ranges']:
						date_range = copy.deepcopy(date_range)
						for i in [0, 1]:
							if date_range[i][0] in ['+', '-']:
								date_range_delta = {}
								if date_range[i][-1] == 'd':
									date_range_delta = {'days': int(date_range[i][:-1])}
								elif date_range[i][-1] == 'w':
									date_range_delta = {'weeks': int(date_range[i][:-1])}
								date_range[i] = (
									(datetime.datetime.utcnow() + datetime.timedelta(**date_range_delta))
									.isoformat()
									.split('T')[0]
								)
						if attr_val >= date_range[0] and attr_val < date_range[1]:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'DATETIME':
			if re.match(
				r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{6})?)?$',
				attr_val,
			):
				if attr_type._args['ranges']:
					for datetime_range in attr_type._args['ranges']:
						datetime_range = copy.deepcopy(datetime_range)
						for i in [0, 1]:
							if datetime_range[i][0] in ['+', '-']:
								datetime_range_delta = {}
								if datetime_range[i][-1] == 'd':
									datetime_range_delta = {'days': int(datetime_range[i][:-1])}
								elif datetime_range[i][-1] == 's':
									datetime_range_delta = {'seconds': int(datetime_range[i][:-1])}
								elif datetime_range[i][-1] == 'm':
									datetime_range_delta = {'minutes': int(datetime_range[i][:-1])}
								elif datetime_range[i][-1] == 'h':
									datetime_range_delta = {'hours': int(datetime_range[i][:-1])}
								elif datetime_range[i][-1] == 'w':
									datetime_range_delta = {'weeks': int(datetime_range[i][:-1])}
								datetime_range[i] = (
									datetime.datetime.utcnow() + datetime.timedelta(**datetime_range_delta)
								).isoformat()
						if attr_val >= datetime_range[0] and attr_val < datetime_range[1]:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'DYNAMIC_ATTR':
			if type(attr_val) == dict:
				try:
					if (not attr_type._args['types']) or (
						attr_type._args['types'] and attr_val['type'] in attr_type._args['types']
					):
						_, attr_val = generate_dynamic_attr(dynamic_attr=attr_val)
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
				except Exception as e:
					logger.debug(
						'Exception occurred while validating type \'DYNAMIC_ATTR\'. Exception details:'
					)
					logger.debug(e)

		elif attr_type._type == 'DYNAMIC_VAL':
			# [DOC] Populate setting_query
			setting_query = {}
			if attr_type._args['dynamic_attr'].startswith('$__settings.global/'):
				setting_query['type'] = 'global'
				setting_query['var'] = attr_type._args['dynamic_attr'].split('/')[1]
			elif attr_type._args['dynamic_attr'].startswith('$__settings.user/'):
				setting_query['type'] = 'user'
				_, setting_query['user'], setting_query['var'] = attr_type._args[
					'dynamic_attr'
				].split('/')
			# [DOC] Check if variables are present in setting_query['var']
			for setting_query_var in re.findall(
				r'(\$__doc\.([a-zA-Z0-9_]+))', setting_query['var']
			):
				doc = cast(Dict[str, Any], doc)
				setting_query['var'] = setting_query['var'].replace(
					setting_query_var[0], str(extract_attr(scope=doc, attr_path=setting_query_var[1]))
				)
			# [DOC] Read setting val
			env = cast(NAWAH_ENV, env)
			setting_results = await Config.modules['setting'].read(
				skip_events=[Event.PERM], env=env, query=[setting_query]
			)
			setting = setting_results.args.docs[0]
			dynamic_attr = generate_dynamic_attr(dynamic_attr=setting.val)[0]
			attr_val = await validate_attr(
				mode='create', attr_name=attr_name, attr_type=dynamic_attr, attr_val=attr_val
			)
			return return_valid_attr(
				attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
			)

		elif attr_type._type == 'KV_DICT':
			if type(attr_val) == dict:
				if attr_type._args['min']:
					if len(attr_val.keys()) < attr_type._args['min']:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				if attr_type._args['max']:
					if len(attr_val.keys()) > attr_type._args['max']:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				if attr_type._args['req']:
					for req_key in attr_type._args['req']:
						if req_key not in attr_val.keys():
							raise InvalidAttrException(
								attr_name=attr_name,
								attr_type=attr_type,
								val_type=type(attr_val),
							)
				shadow_attr_val = {}
				for child_attr_val in attr_val.keys():
					shadow_attr_val[
						await validate_attr(
							mode=mode,
							attr_name=f'{attr_name}.{child_attr_val}',
							attr_type=attr_type._args['key'],
							attr_val=child_attr_val,
							skip_events=skip_events,
							env=env,
							query=query,
							doc=doc,
							scope=attr_val,
						)
					] = await validate_attr(
						mode=mode,
						attr_name=f'{attr_name}.{child_attr_val}',
						attr_type=attr_type._args['val'],
						attr_val=attr_val[child_attr_val],
						skip_events=skip_events,
						env=env,
						query=query,
						doc=doc,
						scope=attr_val,
					)
				return return_valid_attr(
					attr_val=shadow_attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'TYPED_DICT':
			if type(attr_val) == dict:
				for child_attr_type in attr_type._args['dict'].keys():
					if child_attr_type not in attr_val.keys():
						attr_val[child_attr_type] = None
					try:
						attr_val[child_attr_type] = await validate_attr(
							mode=mode,
							attr_name=f'{attr_name}.{child_attr_type}',
							attr_type=attr_type._args['dict'][child_attr_type],
							attr_val=attr_val[child_attr_type],
							skip_events=skip_events,
							env=env,
							query=query,
							doc=doc,
							scope=attr_val,
						)
					except Exception as e:
						logger.debug(
							'Exception occurred while validating type \'TYPED_DICT\'. Exception details:'
						)
						logger.debug(e)
						raise e

				# [DOC] Match keys _after_ checking child attrs in order to allow validate_default to run on all child attrs
				if set(attr_val.keys()) != set(attr_type._args['dict'].keys()):
					raise InvalidAttrException(
						attr_name=attr_name,
						attr_type=attr_type,
						val_type=type(attr_val),
					)

				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'EMAIL':
			if type(attr_val) == str and re.match(r'^[^@]+@[^@]+\.[^@]+$', attr_val):
				if attr_type._args['allowed_domains']:
					for domain in attr_type._args['allowed_domains']:
						if attr_type._args['strict']:
							domain = f'@{domain}'
						if attr_val.endswith(domain):
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				elif attr_type._args['disallowed_domains']:
					for domain in attr_type._args['disallowed_domains']:
						if attr_type._args['strict']:
							domain = f'@{domain}'
						if attr_val.endswith(domain):
							break
					else:
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'FILE':
			if type(attr_val) == list and len(attr_val):
				try:
					attr_val = await validate_attr(
						mode=mode,
						attr_name=attr_name,
						attr_type=attr_type,
						attr_val=attr_val[0],
						skip_events=skip_events,
						env=env,
						query=query,
						doc=doc,
						scope=attr_val,
					)
				except Exception as e:
					logger.debug(
						'Exception occurred while validating type \'FILE\'. Exception details:'
					)
					logger.debug(e)
					raise InvalidAttrException(
						attr_name=attr_name,
						attr_type=attr_type,
						val_type=type(attr_val),
					)
			file_type_check = (
				type(attr_val) == dict
				and set(attr_val.keys()) == {'name', 'lastModified', 'type', 'size', 'content'}
				and type(attr_val['name']) == str
				and type(attr_val['type']) == str
				and type(attr_val['lastModified']) == int
				and type(attr_val['size']) == int
				and type(attr_val['content']) in [binary.Binary, bytes]
			)
			if not file_type_check:
				raise InvalidAttrException(
					attr_name=attr_name, attr_type=attr_type, val_type=type(attr_val)
				)
			if attr_type._args['types']:
				for file_type in attr_type._args['types']:
					if attr_val['type'].split('/')[0] == file_type.split('/')[0]:
						if (
							file_type.split('/')[1] == '*'
							or attr_val['type'].split('/')[1] == file_type.split('/')[1]
						):
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
			else:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'FLOAT':
			if type(attr_val) == str and re.match(r'^[0-9]+(\.[0-9]+)?$', attr_val):
				attr_val = float(attr_val)
			elif type(attr_val) == int:
				attr_val = float(attr_val)

			if type(attr_val) == float:
				if attr_type._args['ranges']:
					for _range in attr_type._args['ranges']:
						if attr_val >= _range[0] and attr_val < _range[1]:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'GEO':
			if (
				type(attr_val) == dict
				and set(attr_val.keys()) == {'type', 'coordinates'}
				and attr_val['type'] in ['Point']
				and type(attr_val['coordinates']) == list
				and len(attr_val['coordinates']) == 2
				and type(attr_val['coordinates'][0]) in [int, float]
				and type(attr_val['coordinates'][1]) in [int, float]
			):
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'ID':
			if type(attr_val) == BaseModel or type(attr_val) == DictObj:
				return return_valid_attr(
					attr_val=attr_val._id, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)
			elif type(attr_val) == ObjectId:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)
			elif type(attr_val) == str:
				try:
					return return_valid_attr(
						attr_val=ObjectId(attr_val), attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)
				except Exception as e:
					logger.debug('Exception occurred while validating type \'ID\'. Exception details:')
					logger.debug(e)
					raise ConvertAttrException(
						attr_name=attr_name,
						attr_type=attr_type,
						val_type=type(attr_val),
					)

		elif attr_type._type == 'INT':
			if type(attr_val) == str and re.match(r'^[0-9]+$', attr_val):
				attr_val = int(attr_val)

			if type(attr_val) == int:
				if attr_type._args['ranges']:
					for _range in attr_type._args['ranges']:
						if attr_val in range(*_range):
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'IP':
			if re.match(
				r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
				attr_val,
			):
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'LIST':
			if type(attr_val) == list:
				if attr_type._args['min']:
					if len(attr_val) < attr_type._args['min']:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				if attr_type._args['max']:
					if len(attr_val) > attr_type._args['max']:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				for i in range(len(attr_val)):
					child_attr_val = attr_val[i]
					child_attr_check = False
					for child_attr_type in attr_type._args['list']:
						try:
							attr_val[i] = await validate_attr(
								mode=mode,
								attr_name=attr_name,
								attr_type=child_attr_type,
								attr_val=child_attr_val,
								skip_events=skip_events,
								env=env,
								query=query,
								doc=doc,
								scope=attr_val,
							)
							child_attr_check = True
							break
						except Exception as e:
							logger.debug(
								'Exception occurred while validating type \'LIST\'. Exception details:'
							)
							logger.debug(e)
					if not child_attr_check:
						raise InvalidAttrException(
							attr_name=attr_name,
							attr_type=attr_type,
							val_type=type(attr_val),
						)
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'LOCALE':
			attr_val = await validate_attr(
				mode=mode,
				attr_name=attr_name,
				attr_type=ATTR.KV_DICT(
					key=ATTR.LITERAL(literal=[locale for locale in Config.locales]),
					val=ATTR.STR(),
					min=1,
					req=[Config.locale],
				),
				attr_val=attr_val,
				skip_events=skip_events,
				env=env,
				query=query,
				doc=doc,
				scope=attr_val,
			)
			if Config.locale_strategy == LOCALE_STRATEGY.NONE_VALUE:
				attr_val = {
					locale: attr_val[locale] if locale in attr_val.keys() else None
					for locale in Config.locales
				}
			elif callable(Config.locale_strategy):
				attr_val = {
					locale: attr_val[locale]
					if locale in attr_val.keys()
					else Config.locale_strategy(attr_val=attr_val, locale=locale)
					for locale in Config.locales
				}
			else:
				attr_val = {
					locale: attr_val[locale] if locale in attr_val.keys() else attr_val[Config.locale]
					for locale in Config.locales
				}
			return return_valid_attr(
				attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
			)

		elif attr_type._type == 'LOCALES':
			if attr_val in Config.locales:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'PHONE':
			if attr_type._args['codes']:
				for phone_code in attr_type._args['codes']:
					if re.match(fr'^\+{phone_code}[0-9]+$', attr_val):
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
			else:
				if re.match(r'^\+[0-9]+$', attr_val):
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'STR':
			if type(attr_val) == str:
				if attr_type._args['pattern']:
					if re.match(f'^{attr_type._args["pattern"]}$', attr_val):
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'TIME':
			if re.match(r'^[0-9]{2}:[0-9]{2}(:[0-9]{2}(\.[0-9]{6})?)?$', attr_val):
				if attr_type._args['ranges']:
					for time_range in attr_type._args['ranges']:
						time_range = copy.deepcopy(time_range)
						for i in [0, 1]:
							if time_range[i][0] in ['+', '-']:
								time_range_delta = {}
								if time_range[i][-1] == 's':
									time_range_delta = {'seconds': int(time_range[i][:-1])}
								elif time_range[i][-1] == 'm':
									time_range_delta = {'minutes': int(time_range[i][:-1])}
								elif time_range[i][-1] == 'h':
									time_range_delta = {'hours': int(time_range[i][:-1])}
								time_range[i] = (
									(datetime.datetime.utcnow() + datetime.timedelta(**time_range_delta))
									.isoformat()
									.split('T')[1]
								)
						if attr_val >= time_range[0] and attr_val < time_range[1]:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'URI_WEB':
			if re.match(r'^https?:\/\/(?:[\w\-\_]+\.)(?:\.?[\w]{2,})+([\?\/].*)?$', attr_val):
				if attr_type._args['allowed_domains']:
					attr_val_domain = attr_val.split('/')[2]
					for domain in attr_type._args['allowed_domains']:
						if attr_type._args['strict'] and attr_val_domain == domain:
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
						elif not attr_type._args['strict'] and attr_val_domain.endswith(domain):
							return return_valid_attr(
								attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
							)
				elif attr_type._args['disallowed_domains']:
					attr_val_domain = attr_val.split('/')[2]
					for domain in attr_type._args['disallowed_domains']:
						if attr_type._args['strict'] and attr_val_domain == domain:
							break
						elif not attr_type._args['strict'] and attr_val_domain.endswith(domain):
							break
					else:
						return return_valid_attr(
							attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
						)
				else:
					return return_valid_attr(
						attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
					)

		elif attr_type._type == 'LITERAL':
			if attr_val in attr_type._args['literal']:
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'UNION':
			for child_attr in attr_type._args['union']:
				try:
					attr_val = await validate_attr(
						mode=mode,
						attr_name=attr_name,
						attr_type=child_attr,
						attr_val=attr_val,
						skip_events=skip_events,
						env=env,
						query=query,
						doc=doc,
						scope=attr_val,
					)
				except Exception as e:
					logger.debug(
						'Exception occurred while validating type \'UNION\'. Exception details:'
					)
					logger.debug(e)
					continue
				return return_valid_attr(
					attr_val=attr_val, attr_oper=attr_oper, attr_oper_args=attr_oper_args
				)

		elif attr_type._type == 'TYPE':
			return return_valid_attr(
				attr_val=Config.types[attr_type._args['type']](
					attr_name=attr_name, attr_type=attr_type, attr_val=attr_val
				),
				attr_oper=attr_oper,
				attr_oper_args=attr_oper_args,
			)

	except:
		pass

	if mode != 'create':
		return None
	elif attr_type._default != NAWAH_VALUES.NONE_VALUE:
		return attr_type._default
	else:
		raise InvalidAttrException(
			attr_name=attr_name, attr_type=attr_type, val_type=type(attr_val)
		)


def return_valid_attr(
	*,
	attr_val: Any,
	attr_oper: Literal[
		None, '$add', '$multiply', '$append', '$set_index', '$del_val', '$del_index'
	],
	attr_oper_args: Dict[str, Any],
) -> Any:
	if not attr_oper:
		return attr_val
	elif attr_oper in ['$add', '$multiply']:
		return {attr_oper: attr_val, '$field': attr_oper_args['$field']}
	elif attr_oper == '$del_val':
		return {attr_oper: attr_val}
	elif attr_oper == '$append':
		return {'$append': attr_val[0], '$unique': attr_oper_args['$unique']}
	elif attr_oper == '$set_index':
		return {'$set_index': attr_val[0], '$index': attr_oper_args['$index']}
	elif attr_oper == '$del_index':
		return {'$del_index': attr_oper_args['$index']}


def generate_dynamic_attr(
	*, dynamic_attr: Dict[str, Any]
) -> Tuple[ATTR, Dict[str, Any]]:
	# [DOC] Fail-safe checks
	if dynamic_attr['type'] not in ATTRS_TYPES_ARGS.keys():
		raise InvalidAttrTypeException(attr_type=dynamic_attr['type'])
	if 'args' not in dynamic_attr.keys():
		dynamic_attr['args'] = {}

	# [DOC] Process args of type ATTR
	if dynamic_attr['type'] == 'LIST':
		shadow_arg_list: List[Optional[Dict[str, Any]]] = []
		for i in range(len(dynamic_attr['args']['list'])):
			shadow_arg_list.append(None)
			dynamic_attr['args']['list'][i], shadow_arg_list[i] = generate_dynamic_attr(
				dynamic_attr=dynamic_attr['args']['list'][i]
			)
	elif dynamic_attr['type'] == 'TYPED_DICT':
		shadow_arg_dict = {}
		for dict_attr in dynamic_attr['args']['dict'].keys():
			(
				dynamic_attr['args']['dict'][dict_attr],
				shadow_arg_dict[dict_attr],
			) = generate_dynamic_attr(
				dynamic_attr=dynamic_attr['args']['dict'][dict_attr]
			)
	elif dynamic_attr['type'] == 'KV_DICT':
		dynamic_attr['args']['key'], _ = generate_dynamic_attr(
			dynamic_attr=dynamic_attr['args']['key']
		)
		dynamic_attr['args']['val'], _ = generate_dynamic_attr(
			dynamic_attr=dynamic_attr['args']['val']
		)
	if dynamic_attr['type'] == 'UNION':
		shadow_arg_union: List[Optional[Dict[str, Any]]] = []
		for i in range(len(dynamic_attr['args']['union'])):
			shadow_arg_list.append(None)
			dynamic_attr['args']['union'][i], shadow_arg_union[i] = generate_dynamic_attr(
				dynamic_attr=dynamic_attr['args']['union'][i]
			)
	# [DOC] Generate dynamic ATTR using ATTR controller
	dynamic_attr_type = getattr(ATTR, dynamic_attr['type'])(**dynamic_attr['args'])
	# [DOC] Reset values for args of type ATTR
	if dynamic_attr['type'] == 'LIST':
		dynamic_attr['args']['list'] = shadow_arg_list
	elif dynamic_attr['type'] == 'TYPED_DICT':
		dynamic_attr['args']['dict'] = shadow_arg_dict
	elif dynamic_attr['type'] == 'UNION':
		dynamic_attr['args']['dict'] = shadow_arg_union
	# [DOC] Set defaults for optional args
	if 'allow_none' not in dynamic_attr.keys():
		dynamic_attr['allow_none'] = False
	if 'default' not in dynamic_attr.keys():
		dynamic_attr['default'] = None

	return (dynamic_attr_type, dynamic_attr)