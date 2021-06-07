from nawah.config import Config
from nawah.classes import UnexpectedGatewayException, InvalidGatewayException

import logging, traceback

logger = logging.getLogger('nawah')


class Gateway:
	@staticmethod
	def send(*, gateway: str, **kwargs):
		if Config.test:
			logger.debug('Skipping \'Gateway.send\' action due to test mode.')
			return

		if gateway not in Config.gateways.keys():
			raise InvalidGatewayException(gateway=gateway)

		try:
			Config.gateways[gateway](**kwargs)
		except Exception as e:
			logger.error('Gateway call with following \'kwargs\' failed:')
			logger.error(kwargs)
			logger.error(traceback.format_exc())
			raise UnexpectedGatewayException(gateway=gateway)

		return
