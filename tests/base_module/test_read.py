from nawah.classes import MethodException

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
	with pytest.raises(MethodException):
		await test_module.read()