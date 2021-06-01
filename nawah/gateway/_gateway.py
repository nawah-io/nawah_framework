from nawah.config import Config

import logging, traceback

logger = logging.getLogger('nawah')


class InvalidGatewayException(Exception):
	def __init__(self, *, gateway):
		self.gateway = gateway

	def __str__(self):
		return f'Gateway \'{self.gateway}\' is invalid.'


class UnexpectedGatewayException(Exception):
	def __init__(self, *, gateway):
		self.gateway = gateway

	def __str__(self):
		return f'An unexpected gateway exception occurred when attempted to call \'{self.gateway}\'.'


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
