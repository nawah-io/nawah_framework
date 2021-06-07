from nawah.classes import MethodException, Query

from . import MockUtilityModule, MockModule

import pytest


@pytest.mark.asyncio
async def test_read_utility_module(mocker):
	utility_module = MockUtilityModule()
	with pytest.raises(MethodException):
		await utility_module.read()


@pytest.mark.asyncio
async def test_read_module(mocker):
	module = MockModule()
	with pytest.raises(Exception):
		# [DOC] BaseModule methods don't call directly, but through BaseMethod which passes query arg as Query object, replicate the same behaviour
		await module.read(query=Query([]))