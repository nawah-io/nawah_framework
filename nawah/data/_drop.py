from nawah.config import Config
from nawah.classes import NAWAH_ENV

from typing import Literal


async def drop(env: NAWAH_ENV, collection_name: str) -> Literal[True]:
	collection = env['conn'][Config.data_name][collection_name]
	await collection.drop()
	return True
