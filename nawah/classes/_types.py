from nawah.enums import Event

from asyncio import Task
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp.web import WebSocketResponse
from typing import (
	List,
	TypedDict,
	Optional,
	Dict,
	Callable,
	Literal,
	Union,
	Any,
	AsyncGenerator,
	TYPE_CHECKING,
	Coroutine,
)

import datetime

if TYPE_CHECKING:
	from ._base_model import BaseModel
	from ._dictobj import DictObj

NAWAH_EVENTS = List[Event]

WATCH_TASK = TypedDict(
	'WATCH_TASK',
	{
		'watch': Coroutine[Any, Any, None],
		'task': Task,
		'stream': Any,
	},
	total=False,
)

NAWAH_ENV_QUOTA = TypedDict(
	'NAWAH_ENV_QUOTA',
	{
		'counter': int,
		'last_check': datetime.datetime,
	},
)

NAWAH_ENV = TypedDict(
	'NAWAH_ENV',
	{
		'id': int,
		'init': bool,
		'conn': AsyncIOMotorClient,
		'REMOTE_ADDR': str,
		'HTTP_USER_AGENT': str,
		'HTTP_ORIGIN': str,
		'client_app': str,
		'session': 'BaseModel',
		'last_call': datetime.datetime,
		'ws': WebSocketResponse,
		'watch_tasks': Dict[str, WATCH_TASK],
		'quota': NAWAH_ENV_QUOTA,
		'realm': str,
	},
	total=False,
)

NAWAH_QUERY_SPECIAL_GROUP = TypedDict(
	'NAWAH_QUERY_SPECIAL_GROUP', {'by': str, 'count': int}
)

NAWAH_QUERY_SPECIAL_GEO_NEAR = TypedDict(
	'NAWAH_QUERY_SPECIAL_GEO_NEAR', {'val': str, 'attr': str, 'dist': int}
)

NAWAH_QUERY_SPECIAL = TypedDict(
	'NAWAH_QUERY_SPECIAL',
	{
		'$search': Optional[str],
		'$sort': Optional[Dict[str, Literal[1, -1]]],
		'$skip': Optional[int],
		'$limit': Optional[int],
		'$extn': Optional[Union[Literal[False], List[str]]],
		'$attrs': Optional[List[str]],
		'$group': Optional[List[NAWAH_QUERY_SPECIAL_GEO_NEAR]],
		'$geo_near': Optional[NAWAH_QUERY_SPECIAL_GEO_NEAR],
	},
	total=False,
)

NAWAH_QUERY = List[  # type: ignore
	Union[
		'NAWAH_QUERY',  # type: ignore
		Union[
			Dict[
				str,
				Union[
					'NAWAH_QUERY',  # type: ignore
					Any,
					Union[
						Dict[Literal['$eq'], Any],
						Dict[Literal['$ne'], Any],
						Dict[Literal['$gt'], Union[int, str]],
						Dict[Literal['$gte'], Union[int, str]],
						Dict[Literal['$lt'], Union[int, str]],
						Dict[Literal['$lte'], Union[int, str]],
						Dict[Literal['$bet'], Union[List[int], List[str]]],
						Dict[Literal['$all'], List[Any]],
						Dict[Literal['$in'], List[Any]],
						Dict[Literal['$nin'], List[Any]],
						Dict[Literal['$regex'], str],
					],
				],
			],
			NAWAH_QUERY_SPECIAL,
		],
	]
]

NAWAH_DOC = Dict[
	str,
	Union[
		Dict[
			str,
			Union[
				Dict[Literal['$add'], int],
				Dict[Literal['$multiply'], int],
				Dict[Literal['$append'], Any],
				Dict[Literal['$set_index'], Dict[int, Any]],
				Dict[Literal['$set_index'], Dict[int, Any]],
				Dict[Literal['$del_val'], Any],
				Dict[Literal['$del_index'], int],
				Any,
			],
		],
		Any,
	],
]

IP_QUOTA = TypedDict(
	'IP_QUOTA',
	{
		'counter': int,
		'last_check': datetime.datetime,
	},
)