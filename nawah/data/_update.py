from nawah.config import Config
from nawah.classes import NAWAH_ENV, ATTR, NAWAH_DOC

from bson import ObjectId
from typing import Dict, List, Any, Union

import logging, copy

logger = logging.getLogger('nawah')


async def update(
	*,
	env: NAWAH_ENV,
	collection_name: str,
	attrs: Dict[str, ATTR],
	docs: List[Union[str, ObjectId]],
	doc: NAWAH_DOC,
) -> Dict[str, Any]:
	# [DOC] Recreate docs list by converting all docs items to ObjectId
	docs = [ObjectId(doc) for doc in docs]
	# [DOC] Perform update query on matching docs
	collection = env['conn'][Config.data_name][collection_name]
	results = None
	doc = copy.deepcopy(doc)

	# [TODO] Abstract $set pipeline with colon support for all stages

	# [DOC] Prepare empty update pipeline
	update_pipeline: List[Any] = []

	# [DOC] Iterate over attrs in doc to set update stage in pipeline
	for attr in doc.keys():
		# [DOC] Check for $add Doc Oper
		if type(doc[attr]) == dict and '$add' in doc[attr].keys():
			update_pipeline.append(
				{
					'$set': {
						attr: {
							'$add': [
								f'${list(doc[attr]["$add"].keys())[0]}',
								doc[attr]['$add'][list(doc[attr]["$add"].keys())[0]],
							]
						}
					}
				}
			)

		# [DOC] Check for $add Doc Oper
		elif type(doc[attr]) == dict and '$multiply' in doc[attr].keys():
			update_pipeline.append(
				{
					'$set': {
						attr: {
							'$multiply': [
								f'${list(doc[attr]["$multiply"].keys())[0]}',
								doc[attr]['$multiply'][list(doc[attr]["$multiply"].keys())[0]],
							]
						}
					}
				}
			)

		# [DOC] Check for $append Doc Oper
		elif type(doc[attr]) == dict and '$append' in doc[attr].keys():
			if '$unique' not in doc[attr].keys() or doc[attr]['$unique'] == False:
				update_pipeline.append(
					{'$set': {attr: {'$concatArrays': [f'${attr}', [doc[attr]['$append']]]}}}
				)
			else:
				update_pipeline.append(
					{
						'$set': {
							attr: {
								'$concatArrays': [
									f'${attr}',
									{
										'$cond': {
											'if': {'$in': [doc[attr]['$append'], f'${attr}']},
											'then': [],
											'else': [doc[attr]['$append']],
										}
									},
								]
							}
						}
					}
				)

		# [DOC] Check for $set_index Doc Oper
		elif type(doc[attr]) == dict and '$set_index' in doc[attr].keys():
			update_pipeline.append(
				{
					'$set': {
						attr: {
							'$reduce': {
								'input': f'${attr}',
								'initialValue': [],
								'in': {
									'$concatArrays': [
										'$$value',
										{
											'$cond': {
												'if': {
													'$eq': [
														['$$this'],
														[{'$arrayElemAt': [f'${attr}', list(doc[attr]['$set_index'].keys())[0]]}],
													]
												},
												'then': [doc[attr]['$set_index'][list(doc[attr]['$set_index'].keys())[0]]],
												'else': ['$$this'],
											}
										},
									]
								},
							}
						}
					}
				}
			)

		# [DOC] Check for $del_val Doc Oper
		elif type(doc[attr]) == dict and '$del_val' in doc[attr].keys():
			update_pipeline.append(
				{
					'$set': {
						attr: {
							'$reduce': {
								'input': f'${attr}',
								'initialValue': [],
								'in': {
									'$concatArrays': [
										'$$value',
										{
											'$cond': {
												'if': {
													'$eq': [
														['$$this'],
														[doc[attr]['$del_val']],
													]
												},
												'then': [],
												'else': ['$$this'],
											}
										},
									]
								},
							}
						}
					}
				}
			)

		# [DOC] Check for $del_index Doc Oper
		elif type(doc[attr]) == dict and '$del_index' in doc[attr].keys():
			update_pipeline.append(
				{
					'$set': {
						attr: {
							'$reduce': {
								'input': f'${attr}',
								'initialValue': [],
								'in': {
									'$concatArrays': [
										'$$value',
										{
											'$cond': {
												'if': {
													'$eq': [
														['$$this'],
														[{'$arrayElemAt': [f'${attr}', doc[attr]['$del_index']]}],
													]
												},
												'then': [],
												'else': ['$$this'],
											}
										},
									]
								},
							}
						}
					}
				}
			)

		else:
			if ':' not in attr:
				update_pipeline.append({'$set': {attr: doc[attr]}})
			else:
				update_pipeline_stage_root: Dict[str, Any] = {'$set': {}}
				update_pipeline_stage_current = update_pipeline_stage_root['$set']
				attr_path_current = []

				attr_path = attr.split('.')
				for i in range(len(attr_path)):
					attr_path_part = attr_path[i]
					if i == 0:
						# [DOC] First item has to have $
						attr_path_current.append('$' + attr_path_part.split(':')[0])
					else:
						attr_path_current.append(attr_path_part.split(':')[0])

					if ':' not in attr_path_part:
						part_pipeline: Dict[str, Any] = {
							'$arrayToObject': {
								'$concatArrays': [
									{
										'$objectToArray': '.'.join(attr_path_current[:-1]),
									},
									[
										{
											'k': attr_path_part,
											'v': None,
										}
									],
								]
							}
						}
						if 'v' in update_pipeline_stage_current.keys():
							update_pipeline_stage_current['v'] = part_pipeline
						elif 'then' in update_pipeline_stage_current.keys():
							update_pipeline_stage_current['then'] = part_pipeline
						else:
							update_pipeline_stage_current[attr_path_part] = part_pipeline

						update_pipeline_stage_current = part_pipeline['$arrayToObject']['$concatArrays'][
							1
						][0]
					else:
						part_pipeline: Dict[str, Any] = {
							'$map': {
								'input': '.'.join(attr_path_current),
								'as': f'this_{i}',
								'in': {
									'$cond': {
										'if': {
											'$eq': [
												{
													'$indexOfArray': [
														'.'.join(attr_path_current),
														f'$$this_{i}',
													]
												},
												int(attr_path_part.split(':')[1]),
											]
										},
										'then': None,
										'else': f'$$this_{i}',
									}
								},
							}
						}

						if i != 0:
							# [DOC] For all subsequent array objects, wrap in object-to-array-to-object pipeline
							part_pipeline = {
								'$arrayToObject': {
									'$concatArrays': [
										{
											'$objectToArray': '.'.join(attr_path_current[:-1]),
										},
										[
											{
												'k': attr_path_part.split(':')[0],
												'v': part_pipeline,
											}
										],
									]
								}
							}

						if 'v' in update_pipeline_stage_current.keys():
							update_pipeline_stage_current['v'] = part_pipeline
						elif 'then' in update_pipeline_stage_current.keys():
							update_pipeline_stage_current['then'] = part_pipeline
						else:
							update_pipeline_stage_current[attr_path_part.split(':')[0]] = part_pipeline

						if i == 0:
							update_pipeline_stage_current = part_pipeline['$map']['in']['$cond']
						else:
							update_pipeline_stage_current = part_pipeline['$arrayToObject']['$concatArrays'][
								1
							][0]['v']['$map']['in']['$cond']

						attr_path_current = [f'$$this_{i}']

				# [DOC] Set the end value property to value of doc[attr]
				if 'v' in update_pipeline_stage_current.keys():
					update_pipeline_stage_current['v'] = doc[attr]
				elif 'then' in update_pipeline_stage_current.keys():
					update_pipeline_stage_current['then'] = doc[attr]
				else:
					update_pipeline_stage_current[attr_path_part] = doc[attr]

				# [DOC] Add stage to pipeline
				update_pipeline.append(update_pipeline_stage_root)

	logger.debug(f'Final update pipeline: {update_pipeline}')

	# [DOC] If using Azure Mongo service update docs one by one
	if Config.data_azure_mongo:
		update_count = 0
		for _id in docs:
			results = await collection.update_one({'_id': _id}, update_pipeline)
			update_count += results.modified_count
	else:
		results = await collection.update_many({'_id': {'$in': docs}}, update_pipeline)
		update_count = results.modified_count

	return {'count': update_count, 'docs': [{'_id': doc} for doc in docs]}
