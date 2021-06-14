from nawah.config import Config
from nawah.data import create_conn
from nawah.cli import launch
from nawah.utils import import_modules, generate_attr

import pytest, argparse

test_env = None


@pytest.fixture
def setup_test():
	async def _():
		global test_env

		if test_env:
			# [DOC] Re-creating data connection is needed as pytest asyncio event loop is scoped per test, making the connection created in a previous test using closed event loop
			Config._sys_conn = create_conn()
			Config._sys_env['conn'] = Config._sys_conn
			test_env['conn'] = Config._sys_conn
			return

		Config.test = True
		launch(args=argparse.Namespace(env=None, debug=True), custom_launch='test')

		await import_modules()
		await Config.config_data()

		test_env = Config._sys_env

	return _


@pytest.fixture
def env():
	def _():
		global test_env

		return test_env

	return _
