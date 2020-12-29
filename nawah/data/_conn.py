from nawah.config import Config
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any

import logging, os.path

logger = logging.getLogger('nawah')


def create_conn() -> AsyncIOMotorClient:
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
