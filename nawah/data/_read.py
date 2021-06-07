from nawah.config import Config
from nawah.enums import LOCALE_STRATEGY, Event
from nawah.utils import extract_attr
from nawah.classes import (
	NAWAH_ENV,
	ATTR,
	Query,
	BaseModel,
	NAWAH_DOC,
	EXTN,
	InvalidAttrException,
)
from ._query import _compile_query

from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from typing import Dict, Any, Union, List, Optional, cast

import logging, copy

logger = logging.getLogger('nawah')


async def read(
	*,
	env: NAWAH_ENV,
	collection_name: str,
	attrs: Dict[str, ATTR],
	query: Query,
	skip_process: bool = False,
	skip_extn: bool = False,
) -> Dict[str, Any]:
	skip, limit, sort, group, aggregate_query = _compile_query(
		collection_name=collection_name, attrs=attrs, query=query, watch_mode=False
	)

	logger.debug(f'aggregate_query: {aggregate_query}')
	logger.debug(f'skip, limit, sort, group: {skip}, {limit}, {sort}, {group}.')

	collection: AsyncIOMotorCollection = env['conn'][Config.data_name][collection_name]
	docs_total_results = collection.aggregate(
		aggregate_query + [{'$count': '__docs_total'}],
		allowDiskUse=Config.data_disk_use,
	)
	try:
		async for doc in docs_total_results:
			docs_total = doc['__docs_total']
		docs_total
	except:
		return {'total': 0, 'count': 0, 'docs': [], 'groups': []}

	groups = {}
	if group:
		for group_condition in group:
			group_query = aggregate_query + [
				{
					'$bucketAuto': {
						'groupBy': '$' + group_condition['by'],
						'buckets': group_condition['count'],
					}
				}
			]
			check_group = False
			for i in range(len(group_query)):
				if (
					list(group_query[i].keys())[0] == '$match'
					and list(group_query[i]['$match'].keys())[0] == group_condition['by']
				):
					check_group = True
					break
			if check_group:
				del group_query[i]
			group_query_results = collection.aggregate(
				group_query, allowDiskUse=Config.data_disk_use
			)
			groups[group_condition['by']] = [
				{
					'min': group['_id']['min'],
					'max': group['_id']['max'],
					'count': group['count'],
				}
				async for group in group_query_results
			]

	if sort != None:
		aggregate_query.append({'$sort': sort})
	if skip != None:
		aggregate_query.append({'$skip': skip})
	if limit != None:
		aggregate_query.append({'$limit': limit})

	logger.debug(f'final query: {collection}, {aggregate_query}.')

	docs_count_results = collection.aggregate(
		aggregate_query + [{'$count': '__docs_count'}],
		allowDiskUse=Config.data_disk_use,
	)
	try:
		async for doc in docs_count_results:
			docs_count = doc['__docs_count']
		docs_count
	except:
		return {
			'total': docs_total,
			'count': 0,
			'docs': [],
			'groups': {} if not group else groups,
		}
	docs = collection.aggregate(aggregate_query, allowDiskUse=Config.data_disk_use)
	models = []
	extn_models: Dict[str, Optional[BaseModel]] = {}
	async for doc in docs:
		if not skip_process:
			doc = await _process_results_doc(
				env=env,
				collection=collection,
				attrs=attrs,
				doc=doc,
				extn_models=extn_models,
				skip_extn=skip_extn,
			)
		if doc:
			models.append(BaseModel(doc))
	return {
		'total': docs_total,
		'count': docs_count,
		'docs': models,
		'groups': {} if not group else groups,
	}


async def _process_results_doc(
	*,
	env: NAWAH_ENV,
	collection: str,
	attrs: Dict[str, ATTR],
	doc: NAWAH_DOC,
	extn_models: Dict[str, Optional[BaseModel]] = {},
	skip_extn: bool = False,
) -> Dict[str, Any]:
	# [DOC] Process doc attrs
	for attr in attrs.keys():
		if attrs[attr]._type == 'LOCALE':
			if (
				attr in doc.keys() and type(doc[attr]) == dict and Config.locale in doc[attr].keys()
			):
				if Config.locale_strategy == LOCALE_STRATEGY.NONE_VALUE:
					doc[attr] = {
						locale: doc[attr][locale] if locale in doc[attr].keys() else None
						for locale in Config.locales
					}
				elif callable(Config.locale_strategy):
					doc[attr] = {
						locale: doc[attr][locale]
						if locale in doc[attr].keys()
						else Config.locale_strategy(attr_val=doc[attr][Config.locale], locale=locale)
						for locale in Config.locales
					}
				else:
					doc[attr] = {
						locale: doc[attr][locale]
						if locale in doc[attr].keys()
						else doc[attr][Config.locale]
						for locale in Config.locales
					}
		if not skip_extn:
			await _extend_attr(
				doc=doc, scope=doc, attr_name=attr, attr_type=attrs[attr], env=env
			)
	# [DOC] Attempt to extned the doc per extns
	return doc


async def _extend_attr(
	*,
	doc: NAWAH_DOC,
	scope: Union[Dict[str, Any], List[Any]],
	attr_name: Union[str, int],
	attr_type: ATTR,
	env: NAWAH_ENV,
	extn_models: Dict[str, Optional[BaseModel]] = None,
):
	if not extn_models:
		extn_models = {}

	# [DOC] If scope is missing attr_name skip
	if type(scope) == dict and attr_name not in scope.keys():  # type: ignore
		return

	# [DOC] Check attr_type for possible types that require deep checking for extending
	if attr_type._type == 'KV_DICT':
		attr_name = cast(str, attr_name)
		scope = cast(Dict[str, Any], scope)
		if scope[attr_name] and type(scope[attr_name]) == dict:
			for child_attr in scope[attr_name].keys():
				# [DOC] attr_type is KV_DICT where Attr Type Arg val could be extended
				await _extend_attr(
					doc=doc,
					scope=scope[attr_name],
					attr_name=child_attr,
					attr_type=attr_type._args['val'],
					env=env,
					extn_models=extn_models,
				)
	if attr_type._type == 'TYPED_DICT':
		attr_name = cast(str, attr_name)
		scope = cast(Dict[str, Any], scope)
		if scope[attr_name] and type(scope[attr_name]) == dict:
			for child_attr in attr_type._args['dict'].keys():
				# [DOC] attr_type is TYPED_DICT where each dict item could be extended
				await _extend_attr(
					doc=doc,
					scope=scope[attr_name],
					attr_name=child_attr,
					attr_type=attr_type._args['dict'][child_attr],
					env=env,
					extn_models=extn_models,
				)

	elif attr_type._type == 'LIST':
		attr_name = cast(str, attr_name)
		scope = cast(Dict[str, Any], scope)
		if scope[attr_name] and type(scope[attr_name]) == list:
			for child_attr in attr_type._args['list']:
				# [DOC] attr_type is LIST where it could have KV_DICT, TYPED_DICT, ID Attrs Types that can be [deep-]extended
				if child_attr._type == 'KV_DICT':
					for child_scope in scope[attr_name]:
						if type(child_scope) == dict:
							for child_child_attr in child_scope.keys():
								await _extend_attr(
									doc=doc,
									scope=child_scope,
									attr_name=child_child_attr,
									attr_type=child_attr._args['val'],
									env=env,
									extn_models=extn_models,
								)
				elif child_attr._type == 'TYPED_DICT':
					for child_scope in scope[attr_name]:
						if type(child_scope) == dict:
							for child_child_attr in child_attr._args['dict'].keys():
								await _extend_attr(
									doc=doc,
									scope=child_scope,
									attr_name=child_child_attr,
									attr_type=child_attr._args['dict'][child_child_attr],
									env=env,
									extn_models=extn_models,
								)
				elif child_attr._type == 'ID':
					for i in range(len(scope[attr_name])):
						await _extend_attr(
							doc=doc,
							scope=scope[attr_name],
							attr_name=i,
							attr_type=child_attr,
							env=env,
							extn_models=extn_models,
						)

	# [DOC] Attempt to extend the attr unto doc
	if type(attr_type._extn) == ATTR:
		attr_name = cast(str, attr_name)
		scope = cast(Dict[str, Any], scope)
		attr_type._extn = cast(ATTR, attr_type._extn)
		# [DOC] Attr is having Attr Type TYPE (checked by BaseModule.initialise) for _extn value, resolve using the callable
		try:
			extn_set = await attr_type._extn._args['func'](
				mode='create',
				attr_name=attr_name,
				attr_type=attr_type._extn,
				attr_val=scope[attr_name],
				skip_events=[],
				env=env,
				query=[],
				doc=doc,
				scope=scope,
			)

			if type(extn_set['__val']) == ObjectId:
				scope[attr_name] = await _extend_doc(
					env=env,
					doc=doc,
					attr=scope[attr_name],
					extn_id=extn_set['__val'],
					extn=extn_set['__extn'],
					extn_models=extn_models,
				)
			elif type(extn_set['__val']) == list:
				scope[attr_name] = [
					await _extend_doc(
						env=env,
						doc=doc,
						attr=scope[attr_name],
						extn_id=extn_id,
						extn=extn_set['__extn'],
						extn_models=extn_models,
					)
					for extn_id in extn_set['__val']
				]
		except InvalidAttrException as e:
			logger.debug(
				f'Skipping extending attr \'{attr_name}\' due to \'InvalidAttrException\' by Attr Type TYPE.'
			)

	elif type(attr_type._extn) == EXTN:
		attr_name = cast(str, attr_name)
		scope = cast(Dict[str, Any], scope)
		attr_type._extn = cast(EXTN, attr_type._extn)
		# [DOC] Attr is having EXTN for _extn value, attempt to extend attr based on scope type
		if type(scope[attr_name]) == ObjectId:
			scope[attr_name] = await _extend_doc(
				env=env,
				doc=doc,
				attr=scope[attr_name],
				extn_id=scope[attr_name],
				extn=attr_type._extn,
				extn_models=extn_models,
			)
		elif type(scope[attr_name]) == list:
			scope[attr_name] = [
				await _extend_doc(
					env=env,
					doc=doc,
					attr=scope[attr_name],
					extn_id=extn_id,
					extn=attr_type._extn,
					extn_models=extn_models,
				)
				for extn_id in scope[attr_name]
			]


async def _extend_doc(
	*,
	env: NAWAH_ENV,
	doc: NAWAH_DOC,
	attr: Optional[NAWAH_DOC],
	extn_id: ObjectId,
	extn: EXTN,
	extn_models: Dict[str, Optional[BaseModel]] = {},
) -> Optional[BaseModel]:
	# [DOC] Check if extn module is dynamic value
	if extn.module.startswith('$__'):
		extn_module = Config.modules[
			extract_attr(scope={'doc': doc, 'attr': attr}, attr_path=extn.module)
		]
	else:
		extn_module = Config.modules[extn.module]
	# [DOC] Check if extn attr set to fetch all or specific attrs
	if type(extn.attrs) == str and extn.attrs.startswith('$__'):  # type: ignore
		extn.attrs = cast(str, extn.attrs)
		extn_attrs = extract_attr(scope={'doc': doc, 'attr': attr}, attr_path=extn.attrs)
		if extn_attrs[0] == '*':
			extn_attrs = {attr: extn_module.attrs[attr] for attr in extn_module.attrs.keys()}
	elif extn.attrs[0] == '*':
		extn_attrs = {attr: extn_module.attrs[attr] for attr in extn_module.attrs.keys()}
	else:
		extn_attrs = {attr: extn_module.attrs[attr] for attr in extn.attrs}
	# [DOC] Implicitly add _id key to extn attrs so that we don't delete it in process
	extn_attrs['_id'] = 'id'
	# [DOC] Set skip events
	skip_events = [Event.PERM]
	# [DOC] Check if extn instruction is explicitly requires second-dimension extn.
	if extn.force == False:
		skip_events.append(Event.EXTN)
	elif type(extn.force) == str and extn.force.startswith('$__'):  # type: ignore
		extn.force = cast(str, extn.force)
		if not extract_attr(scope={'doc': doc, 'attr': attr}, attr_path=extn.force):
			skip_events.append(Event.EXTN)
	# [DOC] Read doc if not in extn_models
	if str(extn_id) not in extn_models.keys():
		extn_results = await extn_module.methods['read'](
			skip_events=skip_events + (extn.skip_events or []),
			env=env,
			query=[{'_id': extn_id}] + (extn.query or []),  # type: ignore
		)
		if extn_results['args']['count']:
			extn_models[str(extn_id)] = extn_results['args']['docs'][0]
		else:
			extn_models[str(extn_id)] = None
	# [DOC] Set attr to extn_models doc
	extn_doc = copy.deepcopy(extn_models[str(extn_id)])
	# [DOC] delete all unneeded keys from the resulted doc
	if extn_doc:
		extn_doc = BaseModel(
			{attr: extn_doc[attr] for attr in extn_attrs.keys() if attr in extn_doc}
		)
	return extn_doc
