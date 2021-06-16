from nawah import testing
from nawah.config import Config
from nawah.data import create_conn
from nawah.cli import launch
from nawah.utils import _import_modules, _config_data, generate_attr

import pytest, argparse

if testing.NAWAH_TESTING:
	import logging

	logger = logging.getLogger('nawah')
	logger.error('Running both unit and integration tests in one run is not supported.')
	exit(1)  # Running both unit and integration tests in one run is not supported.

testing.NAWAH_TESTING = 'app'

test_env = None


@pytest.fixture
def setup_test():
	async def _():
		global test_env

		if test_env:
			raise Exception('Fixture setup_test can only be run once.')

		Config.test = True
		launch(args=argparse.Namespace(env=None, debug=True), custom_launch='test')

		await _import_modules()
		await _config_data()

		test_env = Config._sys_env

	return _


@pytest.fixture
def env():
	def _():
		global test_env

		return test_env

	return _
