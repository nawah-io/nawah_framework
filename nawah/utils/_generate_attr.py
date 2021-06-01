from nawah.config import Config
from nawah.classes import ATTR

from bson import ObjectId
from typing import Any

import logging, random, datetime, re, math

logger = logging.getLogger('nawah')


def generate_attr(*, attr_type: ATTR) -> Any:
	attr_val: Any

	if attr_type._type == 'ANY':
		return '__any'

	elif attr_type._type == 'ACCESS':
		return {'anon': True, 'users': [], 'groups': []}

	elif attr_type._type == 'BOOL':
		attr_val = random.choice([True, False])
		return attr_val

	elif attr_type._type == 'COUNTER':
		counter_groups = re.findall(
			r'(\$__(?:values:[0-9]+|counters\.[a-z0-9_]+))', attr_type._args['pattern']
		)
		attr_val = attr_type._args['pattern']
		for group in counter_groups:
			for group in counter_groups:
				if group.startswith('$__values:'):
					value_callable = attr_type._args['values'][int(group.replace('$__values:', ''))]
					attr_val = attr_val.replace(
						group, str(value_callable(skip_events=[], env={}, query=[], doc={}))
					)
				elif group.startswith('$__counters.'):
					attr_val = attr_val.replace(group, str(42))
		return attr_val

	elif attr_type._type == 'DATE':
		if attr_type._args['ranges']:
			datetime_range = attr_type._args['ranges'][0]
			# [DOC] Be lazy! find a whether start, end of range is a datetime and base the value on it
			if datetime_range[0][0] in ['+', '-'] and datetime_range[1][0] in ['+', '-']:
				# [DOC] Both start, end are dynamic, process start
				datetime_range_delta = {}
				if datetime_range[0][-1] == 'd':
					datetime_range_delta = {'days': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'w':
					datetime_range_delta = {'weeks': int(datetime_range[0][:-1])}
				attr_val = (
					(datetime.datetime.utcnow() + datetime.timedelta(**datetime_range_delta))
					.isoformat()
					.split('T')[0]
				)
			else:
				if datetime_range[0][0] not in ['+', '-']:
					attr_val = datetime_range[0]
				else:
					attr_val = (
						(datetime.datetime.fromisoformat(datetime_range[1]) - datetime.timedelta(days=1))
						.isoformat()
						.split('T')[0]
					)
		else:
			attr_val = datetime.datetime.utcnow().isoformat().split('T')[0]
		return attr_val

	elif attr_type._type == 'DATETIME':
		if attr_type._args['ranges']:
			datetime_range = attr_type._args['ranges'][0]
			# [DOC] Be lazy! find a whether start, end of range is a datetime and base the value on it
			if datetime_range[0][0] in ['+', '-'] and datetime_range[1][0] in ['+', '-']:
				# [DOC] Both start, end are dynamic, process start
				datetime_range_delta = {}
				if datetime_range[0][-1] == 'd':
					datetime_range_delta = {'days': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 's':
					datetime_range_delta = {'seconds': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'm':
					datetime_range_delta = {'minutes': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'h':
					datetime_range_delta = {'hours': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'w':
					datetime_range_delta = {'weeks': int(datetime_range[0][:-1])}
				attr_val = (
					datetime.datetime.utcnow() + datetime.timedelta(**datetime_range_delta)
				).isoformat()
			else:
				if datetime_range[0][0] not in ['+', '-']:
					attr_val = datetime_range[0]
				else:
					attr_val = (
						datetime.datetime.fromisoformat(datetime_range[1]) - datetime.timedelta(days=1)
					).isoformat()
		else:
			attr_val = datetime.datetime.utcnow().isoformat()
		return attr_val

	elif attr_type._type == 'KV_DICT':
		attr_val = {}
		if attr_type._args['req']:
			attr_val = {
				generate_attr(attr_type=ATTR.LITERAL(literal=[req])): generate_attr(
					attr_type=attr_type._args['val']
				)
				for req in attr_type._args['req']
			}
		for _ in range(attr_type._args['min'] or 0):
			attr_val[generate_attr(attr_type=attr_type._args['key'])] = generate_attr(
				attr_type=attr_type._args['val']
			)
		if len(attr_val.keys()) < (attr_type._args['min'] or 0):
			attr_val = generate_attr(attr_type=attr_type)
		return attr_val

	elif attr_type._type == 'TYPED_DICT':
		attr_val = {
			child_attr: generate_attr(attr_type=attr_type._args['dict'][child_attr])
			for child_attr in attr_type._args['dict'].keys()
		}
		return attr_val

	elif attr_type._type == 'EMAIL':
		attr_val = f'some-{math.ceil(random.random() * 10000)}@mail.provider.com'
		if attr_type._args['allowed_domains']:
			if attr_type._args['strict']:
				domain = 'mail.provider.com'
			else:
				domain = 'provider.com'
			attr_val = attr_val.replace(
				domain, random.choice(attr_type._args['allowed_domains'])
			)
		return attr_val

	elif attr_type._type == 'FILE':
		attr_file_type = 'text/plain'
		attr_file_extension = 'txt'
		if attr_type._args['types']:
			for file_type in attr_type._args['types']:
				if '/' in file_type:
					attr_file_type = file_type
				if '*.' in file_type:
					attr_file_extension = file_type.replace('*.', '')
		file_name = f'__file-{math.ceil(random.random() * 10000)}.{attr_file_extension}'
		return {
			'name': file_name,
			'lastModified': 100000,
			'type': attr_file_type,
			'size': 6,
			'content': b'__file',
		}

	elif attr_type._type == 'FLOAT':
		if attr_type._args['ranges']:
			attr_val = random.choice(
				range(
					math.ceil(attr_type._args['ranges'][0][0]),
					math.floor(attr_type._args['ranges'][0][1]),
				)
			)
			if (
				attr_val != attr_type._args['ranges'][0][0]
				and (attr_val - 0.01) != attr_type._args['ranges'][0][0]
			):
				attr_val -= 0.01
			elif (attr_val + 0.01) < attr_type._args['ranges'][0][1]:
				attr_val += 0.01
			else:
				attr_val = float(attr_val)
		else:
			attr_val = random.random() * 10000
		return attr_val

	elif attr_type._type == 'GEO':
		return {
			'type': 'Point',
			'coordinates': [
				math.ceil(random.random() * 100000) / 1000,
				math.ceil(random.random() * 100000) / 1000,
			],
		}

	elif attr_type._type == 'ID':
		return ObjectId()

	elif attr_type._type == 'INT':
		if attr_type._args['ranges']:
			attr_val = random.choice(
				range(attr_type._args['ranges'][0][0], attr_type._args['ranges'][0][1])
			)
		else:
			attr_val = math.ceil(random.random() * 10000)
		return attr_val

	elif attr_type._type == 'IP':
		return '127.0.0.1'

	elif attr_type._type == 'LIST':
		return [
			generate_attr(attr_type=random.choice(attr_type._args['list']))
			for _ in range(attr_type._args['min'] or 0)
		]

	elif attr_type._type == 'LOCALE':
		return {
			locale: f'__locale-{math.ceil(random.random() * 10000)}' for locale in Config.locales
		}

	elif attr_type._type == 'LOCALES':
		return Config.locale

	elif attr_type._type == 'PHONE':
		attr_phone_code = '000'
		if attr_type._args['codes']:
			attr_phone_code = random.choice(attr_type._args['codes'])
		return f'+{attr_phone_code}{math.ceil(random.random() * 10000)}'

	elif attr_type._type == 'STR':
		if attr_type._args['pattern']:
			logger.warning('Generator for Attr Type STR can\'t handle patterns. Ignoring.')
		return f'__str-{math.ceil(random.random() * 10000)}'

	elif attr_type._type == 'TIME':
		if attr_type._args['ranges']:
			datetime_range = attr_type._args['ranges'][0]
			# [DOC] Be lazy! find a whether start, end of range is a datetime and base the value on it
			if datetime_range[0][0] in ['+', '-'] and datetime_range[1][0] in ['+', '-']:
				# [DOC] Both start, end are dynamic, process start
				datetime_range_delta = {}
				if datetime_range[0][-1] == 's':
					datetime_range_delta = {'seconds': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'm':
					datetime_range_delta = {'minutes': int(datetime_range[0][:-1])}
				elif datetime_range[0][-1] == 'h':
					datetime_range_delta = {'hours': int(datetime_range[0][:-1])}
				attr_val = (
					(datetime.datetime.utcnow() + datetime.timedelta(**datetime_range_delta))
					.isoformat()
					.split('T')[1]
				)
			else:
				if datetime_range[0][0] not in ['+', '-']:
					attr_val = datetime_range[0]
				else:
					# [REF]: https://stackoverflow.com/a/656394/2393762
					attr_val = (
						(
							datetime.datetime.combine(
								datetime.date.today(), datetime.time.fromisoformat(datetime_range[1])
							)
							- datetime.timedelta(minutes=1)
						)
						.isoformat()
						.split('T')[1]
					)
		else:
			attr_val = datetime.datetime.utcnow().isoformat().split('T')[1]
		return attr_val

	elif attr_type._type == 'URI_WEB':
		attr_val = f'https://sub.domain.com/page-{math.ceil(random.random() * 10000)}/'
		if attr_type._args['allowed_domains']:
			if attr_type._args['strict']:
				domain = 'sub.domain.com'
			else:
				domain = 'domain.com'
			attr_val = attr_val.replace(
				domain, random.choice(attr_type._args['allowed_domains'])
			)
		return attr_val

	elif attr_type._type == 'LITERAL':
		attr_val = random.choice(attr_type._args['literal'])
		return attr_val

	elif attr_type._type == 'UNION':
		attr_val = generate_attr(attr_type=random.choice(attr_type._args['union']))
		return attr_val

	raise Exception(f'Unknown generator attr \'{attr_type}\'')