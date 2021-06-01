from nawah.base_module import BaseModule
from nawah.enums import Event
from nawah.classes import ATTR, PERM, METHOD
from nawah.config import Config
from nawah.registry import Registry
from nawah.utils import extract_attr, validate_attr

from bson import ObjectId

import base64


class File(BaseModule):
	'''`File` module provides functionality for `File Upload Workflow`.'''

	collection = 'files'
	attrs = {
		'user': ATTR.ID(desc='`_id` of `User` doc file belongs to.'),
		'file': ATTR.FILE(desc='File object.'),
		'create_time': ATTR.DATETIME(
			desc='Python `datetime` ISO format of the doc creation.'
		),
	}
	methods = {
		'read': METHOD(permissions=[PERM(privilege='__sys')]),
		'create': METHOD(
			permissions=[PERM(privilege='create')],
			post_method=True,
		),
		'delete': METHOD(permissions=[PERM(privilege='__sys')]),
	}

	async def on_read(self, results, skip_events, env, query, doc, payload):
		for i in range(len(results['docs'])):
			results['docs'][i]['file']['lastModified'] = int(
				results['docs'][i]['file']['lastModified']
			)
		return (results, skip_events, env, query, doc, payload)

	async def pre_create(self, skip_events, env, query, doc, payload):
		if Config.file_upload_limit != -1 and len(doc['file']) > Config.file_upload_limit:
			raise self.exception(
				status=400,
				msg=f'File size is beyond allowed limit.',
				args={
					'code': 'INVALID_SIZE',
					'attr': doc['__attr'].decode('utf-8'),
					'name': doc['name'].decode('utf-8'),
				},
			)
		if (module := doc['__module'].decode('utf-8')) not in Config.modules.keys():
			raise self.exception(
				status=400,
				msg=f'Invalid module \'{module}\'',
				args={'code': 'INVALID_MODULE'},
			)

		try:
			attr_type = extract_attr(
				scope=Registry.module(module).attrs,
				attr_path='$__' + (attr := doc['__attr'].decode('utf-8')),
			)
			doc = {
				'file': {
					'name': doc['name'].decode('utf-8'),
					'type': doc['type'].decode('utf-8'),
					'size': len(doc['file']),
					'lastModified': int(doc['lastModified'].decode('utf-8')),
					'content': doc['file'],
				},
			}
			try:
				attr_val = doc['file']
				if attr_type._type == 'LIST':
					attr_val = [doc['file']]
				await validate_attr(
					mode='create', attr_name=attr, attr_type=attr_type, attr_val=attr_val
				)
			except:
				raise self.exception(
					status=400,
					msg=f'Invalid file for \'{attr}\' of module \'{module}\'',
					args={'code': 'INVALID_FILE'},
				)

		except:
			raise self.exception(
				status=400,
				msg=f'Invalid attr \'{attr}\' of module \'{module}\'',
				args={'code': 'INVALID_ATTR'},
			)

		return (skip_events, env, query, doc, payload)
