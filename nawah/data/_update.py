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
				update_doc_pull_all: Dict[str, List[None]] = {}
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
