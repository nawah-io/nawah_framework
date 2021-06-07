from nawah.config import Config
from nawah.enums import DELETE_STRATEGY
from nawah.classes import NAWAH_ENV, ATTR, UnknownDeleteStrategyException

from bson import ObjectId
from typing import Dict, List, Any, Union

import logging

logger = logging.getLogger('nawah')


async def delete(
	*,
	env: NAWAH_ENV,
	collection_name: str,
	attrs: Dict[str, ATTR],
	docs: List[Union[str, ObjectId]],
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
		collection = env['conn'][Config.data_name][collection_name]
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
		collection = env['conn'][Config.data_name][collection_name]
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
