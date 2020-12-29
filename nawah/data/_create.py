from nawah.config import Config
from nawah.classes import NAWAH_ENV, NAWAH_DOC, ATTR, BaseModel

from typing import Dict, Any


async def create(
	*,
	env: NAWAH_ENV,
	collection_name: str,
	attrs: Dict[str, ATTR],
	doc: NAWAH_DOC,
) -> Dict[str, Any]:
	collection = env['conn'][Config.data_name][collection_name]
	results = await collection.insert_one(doc)
	_id = results.inserted_id
	return {'count': 1, 'docs': [BaseModel({'_id': _id})]}
