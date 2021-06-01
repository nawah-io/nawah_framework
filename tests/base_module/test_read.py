from nawah.classes import MethodException, Query

from . import TestUtilityModule, TestModule

import pytest


@pytest.mark.asyncio
async def test_read_utility_module(mocker):
	test_utility_module = TestUtilityModule()
	with pytest.raises(MethodException):
		await test_utility_module.read()


@pytest.mark.asyncio
async def test_read_module(mocker):
	test_module = TestModule()
	with pytest.raises(Exception):
		# [DOC] BaseModule methods don't call directly, but through BaseMethod which passes query arg as Query object, replicate the same behaviour
		await test_module.read(query=Query([]))