from nawah.config import Config
from nawah.enums import Event, DELETE_STRATEGY, LOCALE_STRATEGY
from nawah.classes import (
	DictObj,
	BaseModel,
	Query,
	EXTN,
	ATTR,
	ATTR_MOD,
	NAWAH_DOC,
	NAWAH_ENV,
	NAWAH_QUERY,
)
from nawah.utils import extract_attr, set_attr

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from types import GeneratorType
from typing import Dict, Union, List, Tuple, Any, AsyncGenerator, Optional, cast

import os, logging, re, datetime, copy

logger = logging.getLogger('nawah')


class UnknownDeleteStrategyException(Exception):
	pass


class InvalidQueryException(Exception):
	pass


class Data:
	@classmethod
	def create_conn(cls) -> AsyncIOMotorClient:
		connection_config: Dict[str, Any] = {'ssl': Config.data_ssl}
		if Config.data_ca and Config.data_ca_name:
			__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
			connection_config['ssl_ca_certs'] = os.path.join(
				__location__, '..', 'certs', Config.data_ca_name
			)
		# [DOC] Check for multiple servers
		if type(Config.data_server) == list:
			for data_server in Config.data_server:
				conn = AsyncIOMotorClient(data_server, **connection_config, connect=True)
				try:
					logger.debug(f'Check if data_server: {data_server} isMaster.')
					results = conn.admin.command('ismaster')
					logger.debug(f'-Check results: {results}')
					if results['ismaster']:
						break
				except Exception as err:
					logger.debug(f'Not master. Error: {err}')
					pass
		elif type(Config.data_server) == str:
			# [DOC] If it's single server just connect directly
			conn = AsyncIOMotorClient(Config.data_server, **connection_config, connect=True)
		return conn

	@classmethod
	def _compile_query(
		cls, *, collection: str, attrs: Dict[str, ATTR], query: Query, watch_mode: bool
	) -> Tuple[
		Optional[int],
		Optional[int],
		Dict[str, int],
		Optional[List[Dict[str, Union[str, int]]]],
		List[Any],
	]:
		aggregate_prefix: List[Any] = [
			{'$match': {'$or': [{'__deleted': {'$exists': False}}, {'__deleted': False}]}}
		]
		aggregate_suffix: List[Any] = []
		aggregate_query: List[Any] = [{'$match': {'$and': []}}]
		aggregate_match = aggregate_query[0]['$match']['$and']
		skip: Optional[int] = None
		limit: Optional[int] = None
		sort: Dict[str, int] = {'_id': -1}
		group: Optional[List[Dict[str, Union[str, int]]]] = None
		logger.debug(f'attempting to process query: {query}')

		if not isinstance(query, Query):
			raise InvalidQueryException(f'Query of type \'{type(query)}\' is invalid.')
		query = copy.deepcopy(query)

		if '$skip' in query:
			skip = query['$skip']
			del query['$skip']
		if '$limit' in query:
			limit = query['$limit']
			del query['$limit']
		if '$sort' in query:
			sort = query['$sort']
			del query['$sort']
		if '$group' in query:
			group = query['$group']
			del query['$group']
		if '$search' in query:
			aggregate_prefix.insert(0, {'$match': {'$text': {'$search': query['$search']}}})
			project_query: Dict[str, Any] = {attr: '$' + attr for attr in attrs.keys()}
			project_query['_id'] = '$_id'
			project_query['__score'] = {'$meta': 'textScore'}
			aggregate_suffix.append({'$project': project_query})
			aggregate_suffix.append({'$match': {'__score': {'$gt': 0.5}}})
			del query['$search']
		if '$geo_near' in query:
			aggregate_prefix.insert(
				0,
				{
					'$geoNear': {
						'near': {
							'type': 'Point',
							'coordinates': query['$geo_near']['val'],
						},
						'distanceField': query['$geo_near']['attr'] + '.__distance',
						'maxDistance': query['$geo_near']['dist'],
						'spherical': True,
					}
				},
			)
			del query['$geo_near']

		for step in query:
			cls._compile_query_step(
				aggregate_prefix=aggregate_prefix,
				aggregate_suffix=aggregate_suffix,
				aggregate_match=aggregate_match,
				collection=collection,
				attrs=attrs,
				step=step,
				watch_mode=watch_mode,
			)

		if '$attrs' in query and type(query['$attrs']) == list:
			aggregate_suffix.append(
				{
					'$group': {
						'_id': '$_id',
						**{
							attr: {'$first': f'${attr}'} for attr in query['$attrs'] if attr in attrs.keys()
						},
					}
				}
			)
		else:
			aggregate_suffix.append(
				{
					'$group': {
						'_id': '$_id',
						**{attr: {'$first': f'${attr}'} for attr in attrs.keys()},
					}
				}
			)

		logger.debug(
			f'processed query, aggregate_prefix:{aggregate_prefix}, aggregate_suffix:{aggregate_suffix}, aggregate_match:{aggregate_match}'
		)
		if len(aggregate_match) == 1:
			aggregate_query = [{'$match': aggregate_match[0]}]
		elif len(aggregate_match) == 0:
			aggregate_query = []

		aggregate_query = aggregate_prefix + aggregate_query + aggregate_suffix
		return (skip, limit, sort, group, aggregate_query)

	@classmethod
	def _compile_query_step(
		cls,
		*,
		aggregate_prefix: List[Any],
		aggregate_suffix: List[Any],
		aggregate_match: List[Any],
		collection: str,
		attrs: Dict[str, ATTR],
		step: Union[Dict[str, Any], List[Any]],
		watch_mode: bool,
	) -> None:
		if type(step) == dict and len(step.keys()):  # type: ignore
			step = cast(Dict[str, Any], step)
			child_aggregate_query: Dict[str, Any] = {'$and': []}
			for attr in step.keys():
				if attr.startswith('__or'):
					child_child_aggregate_query: Dict[str, Any] = {'$or': []}
					cls._compile_query_step(
						aggregate_prefix=aggregate_prefix,
						aggregate_suffix=aggregate_suffix,
						aggregate_match=child_child_aggregate_query['$or'],
						collection=collection,
						attrs=attrs,
						step=step[attr],
						watch_mode=watch_mode,
					)
					if len(child_child_aggregate_query['$or']) == 1:
						child_aggregate_query['$and'].append(child_child_aggregate_query['$or'][0])
					elif len(child_child_aggregate_query['$or']) > 1:
						child_aggregate_query['$and'].append(child_child_aggregate_query['$or'])
				else:
					# [DOC] Add extn query when required
					if (
						attr.find('.') != -1
						and attr.split('.')[0] in attrs.keys()
						and attrs[attr.split('.')[0]]._extn
					):
						# [TODO] Check if this works with EXTN as ATTR_MOD
						step_attr = attr.split('.')[1]
						step_attrs: Dict[str, ATTR] = Config.modules[
							attrs[attr.split('.')[0]]._extn.module
						].attrs

						# [DOC] Don't attempt to extn attr that is already extended
						lookup_query = False
						for stage in aggregate_prefix:
							if '$lookup' in stage.keys() and stage['$lookup']['as'] == attr.split('.')[0]:
								lookup_query = True
								break
						if not lookup_query:
							extn_collection = Config.modules[
								attrs[attr.split('.')[0]]._extn.module
							].collection
							aggregate_prefix.append(
								{
									'$lookup': {
										'from': extn_collection,
										'localField': attr.split('.')[0],
										'foreignField': '_id',
										'as': attr.split('.')[0],
									}
								}
							)
							aggregate_prefix.append({'$unwind': f'${attr.split(".")[0]}'})
							group_query = {attr: {'$first': f'${attr}'} for attr in attrs.keys()}
							group_query[attr.split('.')[0]] = {'$first': f'${attr.split(".")[0]}._id'}
							group_query['_id'] = '$_id'
							aggregate_suffix.append({'$group': group_query})
					else:
						step_attr = attr
						step_attrs = attrs

					# [DOC] Convert strings and lists of strings to ObjectId when required
					if step_attr in step_attrs.keys() and step_attrs[step_attr]._type == 'ID':
						try:
							if type(step[attr]) == dict and '$in' in step[attr].keys():
								step[attr] = {'$in': [ObjectId(child_attr) for child_attr in step[attr]['$in']]}
							elif type(step[attr]) == str:
								step[attr] = ObjectId(step[attr])
						except:
							logger.warning(f'Failed to convert attr to id type: {step[attr]}')
					elif (
						step_attr in step_attrs.keys()
						and step_attrs[step_attr]._type == 'list'
						and step_attrs[step_attr]._args['list'][0]._type == 'ID'
					):
						try:
							if type(step[attr]) == list:
								step[attr] = [ObjectId(child_attr) for child_attr in step[attr]]
							elif type(step[attr]) == dict and '$in' in step[attr].keys():
								step[attr] = {'$in': [ObjectId(child_attr) for child_attr in step[attr]['$in']]}
							elif type(step[attr]) == str:
								step[attr] = ObjectId(step[attr])
						except:
							logger.warning(f'Failed to convert attr to id type: {step[attr]}')
					elif step_attr == '_id':
						try:
							if type(step[attr]) == str:
								step[attr] = ObjectId(step[attr])
							elif type(step[attr]) == list:
								step[attr] = [ObjectId(child_attr) for child_attr in step[attr]]
							elif type(step[attr]) == dict and '$in' in step[attr].keys():
								step[attr] = {'$in': [ObjectId(child_attr) for child_attr in step[attr]['$in']]}
						except:
							logger.warning(f'Failed to convert attr to id type: {step[attr]}')
					# [DOC] Check for access special attrs
					elif step_attr in step_attrs.keys() and step_attrs[step_attr]._type == 'ACCESS':
						access_query: List[Any] = [
							{
								'$project': {
									'__user': '$user',
									'__access.anon': f'${attr}.anon',
									'__access.users': {
										'$in': [
											ObjectId(step[attr]['$__user']),
											f'${attr}.users',
										]
									},
									'__access.groups': {
										'$or': [
											{'$in': [group, f'${attr}.groups']} for group in step[attr]['$__groups']
										]
									},
								}
							},
							{
								'$match': {
									'$or': [
										{'__user': ObjectId(step[attr]['$__user'])},
										{'__access.anon': True},
										{'__access.users': True},
										{'__access.groups': True},
									]
								}
							},
						]
						access_query[0]['$project'].update({attr: '$' + attr for attr in attrs.keys()})

						aggregate_prefix.append(access_query[0])
						step[attr] = access_query[1]
					# [DOC] Check for query oper
					if type(step[attr]) == dict:
						# [DOC] Check for $bet query oper
						if '$bet' in step[attr].keys():
							step[attr] = {
								'$gte': step[attr]['$bet'][0],
								'$lte': step[attr]['$bet'][1],
							}
						# [DOC] Check for $regex query oper
						elif '$regex' in step[attr].keys():
							step[attr] = {
								'$regex': re.compile(step[attr]['$regex'], re.RegexFlag.IGNORECASE)
							}

					if type(step[attr]) == dict and '$match' in step[attr].keys():
						child_aggregate_query['$and'].append(step[attr]['$match'])
					else:
						if watch_mode:
							child_aggregate_query['$and'].append({f'fullDocument.{attr}': step[attr]})
						else:
							child_aggregate_query['$and'].append({attr: step[attr]})
			if len(child_aggregate_query['$and']) == 1:
				aggregate_match.append(child_aggregate_query['$and'][0])
			elif len(child_aggregate_query['$and']) > 1:
				aggregate_match.append(child_aggregate_query)
		elif type(step) == list and len(step):
			step = cast(List[Any], step)
			child_aggregate_query = {'$or': []}
			for child_step in step:
				cls._compile_query_step(
					aggregate_prefix=aggregate_prefix,
					aggregate_suffix=aggregate_suffix,
					aggregate_match=child_aggregate_query['$or'],
					collection=collection,
					attrs=attrs,
					step=child_step,
					watch_mode=watch_mode,
				)
			if len(child_aggregate_query['$or']) == 1:
				aggregate_match.append(child_aggregate_query['$or'][0])
			elif len(child_aggregate_query['$or']) > 1:
				aggregate_match.append(child_aggregate_query)

	@classmethod
	async def _process_results_doc(
		cls,
		*,
		env: NAWAH_ENV,
		collection: str,
		attrs: Dict[str, ATTR],
		doc: NAWAH_DOC,
		extn_models: Dict[str, BaseModel] = {},
		skip_extn: bool = False,
	) -> Dict[str, Any]:
		# [DOC] Process doc attrs
		for attr in attrs.keys():
			if attrs[attr]._type == 'LOCALE':
				if (
					attr in doc.keys()
					and type(doc[attr]) == dict
					and Config.locale in doc[attr].keys()
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
				await Data._extend_attr(
					doc=doc, scope=doc, attr_name=attr, attr_type=attrs[attr], env=env
				)
		# [DOC] Attempt to extned the doc per extns
		return doc

	@classmethod
	async def _extend_attr(
		cls,
		*,
		doc: NAWAH_DOC,
		scope: Union[Dict[str, Any], List[Any]],
		attr_name: Union[str, int],
		attr_type: ATTR,
		env: NAWAH_ENV,
		extn_models: Dict[str, BaseModel] = None,
	):
		if not extn_models:
			extn_models = {}

		# [DOC] If scope is missing attr_name skip
		if type(scope) == dict and attr_name not in scope.keys():
			return

		# [DOC] Check attr_type for possible types that require deep checking for extending
		if attr_type._type == 'KV_DICT':
			if scope[attr_name] and type(scope[attr_name]) == dict:
				for child_attr in scope[attr_name].keys():
					# [DOC] attr_type is KV_DICT where Attr Type Arg val could be extended
					await cls._extend_attr(
						doc=doc,
						scope=scope[attr_name],
						attr_name=child_attr,
						attr_type=attr_type._args['val'],
						env=env,
						extn_models=extn_models,
					)
		if attr_type._type == 'TYPED_DICT':
			if scope[attr_name] and type(scope[attr_name]) == dict:
				for child_attr in attr_type._args['dict'].keys():
					# [DOC] attr_type is TYPED_DICT where each dict item could be extended
					await cls._extend_attr(
						doc=doc,
						scope=scope[attr_name],
						attr_name=child_attr,
						attr_type=attr_type._args['dict'][child_attr],
						env=env,
						extn_models=extn_models,
					)

		elif attr_type._type == 'LIST':
			if scope[attr_name] and type(scope[attr_name]) == list:
				for child_attr in attr_type._args['list']:
					# [DOC] attr_type is LIST where it could have KV_DICT, TYPED_DICT, ID Attrs Types that can be [deep-]extended
					if child_attr._type == 'KV_DICT':
						for child_scope in scope[attr_name]:
							if type(child_scope) == dict:
								for child_child_attr in child_scope.keys():
									await cls._extend_attr(
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
									await cls._extend_attr(
										doc=doc,
										scope=child_scope,
										attr_name=child_child_attr,
										attr_type=child_attr._args['dict'][child_child_attr],
										env=env,
										extn_models=extn_models,
									)
					elif child_attr._type == 'ID':
						for i in range(len(scope[attr_name])):
							await cls._extend_attr(
								doc=doc,
								scope=scope[attr_name],
								attr_name=i,
								attr_type=child_attr,
								env=env,
								extn_models=extn_models,
							)

		# [DOC] Attempt to extend the attr unto doc
		if type(attr_type._extn) == ATTR_MOD:
			attr_type._extn = cast(ATTR_MOD, attr_type._extn)
			# [DOC] Attr is having ATTR_MOD for _extn value, call the condition callable and attempt to resolve
			if attr_type._extn.condition(
				skip_events=[], env=env, query=[], doc=doc, scope=scope[attr_name]
			):
				extn_set = attr_type._extn.default(
					skip_events=[], env=env, query=[], doc=doc, scope=scope[attr_name]
				)
				if type(extn_set['__val']) == ObjectId:
					scope[attr_name] = await cls._extend_doc(
						env=env,
						doc=doc,
						attr=scope[attr_name],
						extn_id=extn_set['__val'],
						extn=extn_set['__extn'],
						extn_models=extn_models,
					)
				elif type(extn_set['__val']) == list:
					scope[attr_name] = [
						await cls._extend_doc(
							env=env,
							doc=doc,
							attr=scope[attr_name],
							extn_id=extn_id,
							extn=extn_set['__extn'],
							extn_models=extn_models,
						)
						for extn_id in extn_set['__val']
					]

		elif type(attr_type._extn) == EXTN:
			# [DOC] Attr is having EXTN for _extn value, attempt to extend attr based on scope type
			if type(scope[attr_name]) == ObjectId:
				scope[attr_name] = await cls._extend_doc(
					env=env,
					doc=doc,
					attr=scope[attr_name],
					extn_id=scope[attr_name],
					extn=attr_type._extn,
					extn_models=extn_models,
				)
			elif type(scope[attr_name]) == list:
				scope[attr_name] = [
					await cls._extend_doc(
						env=env,
						doc=doc,
						attr=scope[attr_name],
						extn_id=extn_id,
						extn=attr_type._extn,
						extn_models=extn_models,
					)
					for extn_id in scope[attr_name]
				]

	@classmethod
	async def _extend_doc(
		cls,
		*,
		env: NAWAH_ENV,
		doc: NAWAH_DOC,
		attr: Optional[NAWAH_DOC],
		extn_id: ObjectId,
		extn: EXTN,
		extn_models: Dict[str, BaseModel] = {},
	) -> BaseModel:
		# [DOC] Check if extn module is dynamic value
		if extn.module.startswith('$__'):
			extn_module = Config.modules[
				extract_attr(scope={'doc': doc, 'attr': attr}, attr_path=extn.module)
			]
		else:
			extn_module = Config.modules[extn.module]
		# [DOC] Check if extn attr set to fetch all or specific attrs
		if type(extn.attrs) == str and extn.attrs.startswith('$__'):
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
		elif type(extn.force) == str and extn.force.startswith('$__'):
			if not extract_attr(scope={'doc': doc, 'attr': attr}, attr_path=extn.attrs):
				skip_events.append(Event.EXTN)
		# [DOC] Read doc if not in extn_models
		if str(extn_id) not in extn_models.keys():
			extn_results = await extn_module.methods['read'](
				skip_events=skip_events + (extn.skip_events or []),
				env=env,
				query=[{'_id': extn_id}] + (extn.query or []),
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

	@classmethod
	async def read(
		cls,
		*,
		env: NAWAH_ENV,
		collection: str,
		attrs: Dict[str, ATTR],
		query: Query,
		skip_process: bool = False,
		skip_extn: bool = False,
	) -> Dict[str, Any]:
		skip, limit, sort, group, aggregate_query = cls._compile_query(
			collection=collection, attrs=attrs, query=query, watch_mode=False
		)

		logger.debug(f'aggregate_query: {aggregate_query}')
		logger.debug(f'skip, limit, sort, group: {skip}, {limit}, {sort}, {group}.')

		collection = env['conn'][Config.data_name][collection]
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
				group_query = collection.aggregate(group_query, allowDiskUse=Config.data_disk_use)
				groups[group_condition['by']] = [
					{
						'min': group['_id']['min'],
						'max': group['_id']['max'],
						'count': group['count'],
					}
					async for group in group_query
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
		extn_models = {}
		async for doc in docs:
			if not skip_process:
				doc = await cls._process_results_doc(
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

	@classmethod
	async def watch(
		cls,
		*,
		env: NAWAH_ENV,
		collection: str,
		attrs: Dict[str, ATTR],
		query: Query,
		skip_extn: bool = False,
	) -> AsyncGenerator[Dict[str, Any], Dict[str, Any]]:
		aggregate_query = cls._compile_query(
			collection=collection, attrs=attrs, query=query, watch_mode=True
		)[4]

		collection = env['conn'][Config.data_name][collection]

		logger.debug('Preparing generator at Data')
		async with collection.watch(
			pipeline=aggregate_query, full_document='updateLookup'
		) as stream:
			yield {'stream': stream}
			async for change in stream:
				logger.debug(f'Detected change at Data: {change}')

				oper = change['operationType']
				if oper in ['insert', 'replace', 'update']:
					if oper == 'insert':
						oper = 'create'
					elif oper == 'replace':
						oper = 'update'
					doc = await cls._process_results_doc(
						env=env,
						collection=collection,
						attrs=attrs,
						doc=change['fullDocument'],
						skip_extn=skip_extn,
					)
					model = BaseModel(doc)
				elif oper == 'delete':
					model = BaseModel({'_id': change['documentKey']['_id']})

				yield {'count': 1, 'oper': oper, 'docs': [model]}

		logger.debug('changeStream has been close. Generator ended at Data')

	@classmethod
	async def create(
		cls,
		*,
		env: NAWAH_ENV,
		collection: str,
		attrs: Dict[str, ATTR],
		doc: NAWAH_DOC,
	) -> Dict[str, Any]:
		collection = env['conn'][Config.data_name][collection]
		results = await collection.insert_one(doc)
		_id = results.inserted_id
		return {'count': 1, 'docs': [BaseModel({'_id': _id})]}

	@classmethod
	async def update(
		cls,
		*,
		env: NAWAH_ENV,
		collection: str,
		attrs: Dict[str, ATTR],
		docs: List[str],
		doc: NAWAH_DOC,
	) -> Dict[str, Any]:
		# [DOC] Recreate docs list by converting all docs items to ObjectId
		docs = [ObjectId(doc) for doc in docs]
		# [DOC] Perform update query on matching docs
		collection = env['conn'][Config.data_name][collection]
		results = None
		doc = copy.deepcopy(doc)
		update_doc = {'$set': doc}
		# [DOC] Check for increment oper
		del_attrs = []
		for attr in doc.keys():
			# [DOC] Check for $add update oper
			if type(doc[attr]) == dict and '$add' in doc[attr].keys():
				if '$inc' not in update_doc.keys():
					update_doc['$inc'] = {}
				update_doc['$inc'][attr] = doc[attr]['$add']
				del_attrs.append(attr)
			if type(doc[attr]) == dict and '$multiply' in doc[attr].keys():
				if '$mul' not in update_doc.keys():
					update_doc['$mul'] = {}
				update_doc['$mul'][attr] = doc[attr]['$multiply']
				del_attrs.append(attr)
			# [DOC] Check for $append update oper
			elif type(doc[attr]) == dict and '$append' in doc[attr].keys():
				# [DOC] Check for $unique flag
				if '$unique' in doc[attr].keys() and doc[attr]['$unique'] == True:
					if '$addToSet' not in update_doc.keys():
						update_doc['$addToSet'] = {}
					update_doc['$addToSet'][attr] = doc[attr]['$append']
					del_attrs.append(attr)
				else:
					if '$push' not in update_doc.keys():
						update_doc['$push'] = {}
					update_doc['$push'][attr] = doc[attr]['$append']
					del_attrs.append(attr)
			# [DOC] Check for $set_index update oper
			elif type(doc[attr]) == dict and '$set_index' in doc[attr].keys():
				update_doc['$set'][f'{attr}.{doc[attr]["$index"]}'] = doc[attr]
				del_attrs.append(attr)
			# [DOC] Check for $del_val update oper
			elif type(doc[attr]) == dict and '$del_val' in doc[attr].keys():
				if '$pullAll' not in update_doc.keys():
					update_doc['$pullAll'] = {}
				update_doc['$pullAll'][attr] = doc[attr]['$del_val']
				del_attrs.append(attr)
			# [DOC] Check for $del_index update oper
			elif type(doc[attr]) == dict and '$del_index' in doc[attr].keys():
				if '$unset' not in update_doc.keys():
					update_doc['$unset'] = {}
				update_doc['$unset'][f'{attr}.{doc[attr]["$del_index"]}'] = True
				del_attrs.append(attr)
		for del_attr in del_attrs:
			del doc[del_attr]
		if not update_doc['$set']:
			del update_doc['$set']
		logger.debug(f'Final update doc: {update_doc}')
		# [DOC] If using Azure Mongo service update docs one by one
		if Config.data_azure_mongo:
			update_count = 0
			for _id in docs:
				results = await collection.update_one({'_id': _id}, update_doc)
				if '$unset' in update_doc:
					logger.debug(f'Doc Oper $del_index is in-use, will update to remove `None` value')
					update_doc_pull_all = {}
					for attr in update_doc['$unset']:
						attr_parent = '.'.join(attr.split('.')[:-1])
						if attr_parent not in update_doc_pull_all.keys():
							update_doc_pull_all[attr_parent] = [None]
					logger.debug(f'Follow-up update doc: {update_doc_pull_all}')
					await collection.update_one({'_id': _id}, {'$pullAll': update_doc_pull_all})
				update_count += results.modified_count
		else:
			results = await collection.update_many({'_id': {'$in': docs}}, update_doc)
			update_count = results.modified_count
			if '$unset' in update_doc:
				logger.debug(f'Doc Oper $del_index is in-use, will update to remove `None` value')
				update_doc_pull_all = {}
				for attr in update_doc['$unset']:
					attr_parent = '.'.join(attr.split('.')[:-1])
					if attr_parent not in update_doc_pull_all.keys():
						update_doc_pull_all[attr_parent] = [None]
				logger.debug(f'Follow-up update doc: {update_doc_pull_all}')
				try:
					await collection.update_many(
						{'_id': {'$in': docs}}, {'$pullAll': update_doc_pull_all}
					)
				except Exception as err:
					if str(err) != 'Cannot apply $pull to a non-array value':
						logger.error(f'Error occurred while removing `None` values. Details: {err}')
		return {'count': update_count, 'docs': [{'_id': doc} for doc in docs]}

	@classmethod
	async def delete(
		cls,
		*,
		env: NAWAH_ENV,
		collection: str,
		attrs: Dict[str, ATTR],
		docs: List[str],
		strategy: DELETE_STRATEGY,
	) -> Dict[str, Any]:
		# [DOC] Check strategy to cherrypick update, delete calls and system_docs
		if strategy in [DELETE_STRATEGY.SOFT_SKIP_SYS, DELETE_STRATEGY.SOFT_SYS]:
			if strategy == DELETE_STRATEGY.SOFT_SKIP_SYS:
				del_docs = [
					ObjectId(doc) for doc in docs if ObjectId(doc) not in Config._sys_docs.keys()
				]
				if len(del_docs) != len(docs):
					logger.warning(
						'Skipped soft delete for system docs due to \'DELETE_SOFT_SKIP_SYS\' strategy.'
					)
			else:
				logger.warning('Detected \'DELETE_SOFT_SYS\' strategy for delete call.')
				del_docs = [ObjectId(doc) for doc in docs]
			# [DOC] Perform update call on matching docs
			collection = env['conn'][Config.data_name][collection]
			update_doc = {'$set': {'__deleted': True}}
			# [DOC] If using Azure Mongo service update docs one by one
			if Config.data_azure_mongo:
				update_count = 0
				for _id in docs:
					results = await collection.update_one({'_id': _id}, update_doc)
					update_count += results.modified_count
			else:
				results = await collection.update_many({'_id': {'$in': docs}}, update_doc)
				update_count = results.modified_count
			return {'count': update_count, 'docs': [{'_id': doc} for doc in docs]}
		elif strategy in [DELETE_STRATEGY.FORCE_SKIP_SYS, DELETE_STRATEGY.FORCE_SYS]:
			if strategy == DELETE_STRATEGY.FORCE_SKIP_SYS:
				del_docs = [
					ObjectId(doc) for doc in docs if ObjectId(doc) not in Config._sys_docs.keys()
				]
				if len(del_docs) != len(docs):
					logger.warning(
						'Skipped soft delete for system docs due to \'DELETE_FORCE_SKIP_SYS\' strategy.'
					)
			else:
				logger.warning('Detected \'DELETE_FORCE_SYS\' strategy for delete call.')
				del_docs = [ObjectId(doc) for doc in docs]
			# [DOC] Perform delete query on matching docs
			collection = env['conn'][Config.data_name][collection]
			if Config.data_azure_mongo:
				delete_count = 0
				for _id in del_docs:
					results = await collection.delete_one({'_id': _id})
					delete_count += results.deleted_count
			else:
				results = await collection.delete_many({'_id': {'$in': del_docs}})
				delete_count = results.deleted_count
			return {'count': delete_count, 'docs': [{'_id': doc} for doc in docs]}
		else:
			raise UnknownDeleteStrategyException(f'DELETE_STRATEGY \'{strategy}\' is unknown.')

	@classmethod
	async def drop(cls, env: NAWAH_ENV, collection: str) -> True:
		collection = env['conn'][Config.data_name][collection]
		await collection.drop()
		return True
