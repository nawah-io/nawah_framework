from nawah.classes import ATTR
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_INT_None():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_INT',
			attr_type=ATTR.INT(),
			attr_val=None,
			allow_update=False,
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_str():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_INT',
			attr_type=ATTR.INT(),
			attr_val='str',
			allow_update=False,
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_float():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_INT',
			attr_type=ATTR.INT(),
			attr_val=1.1,
			allow_update=False,
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_int():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(),
		attr_val=1,
		allow_update=False,
	)
	assert attr_val == 1


@pytest.mark.asyncio
async def test_validate_attr_INT_float_as_str():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_INT',
			attr_type=ATTR.INT(),
			attr_val='1.1',
			allow_update=False,
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_int_as_str():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(),
		attr_val='1',
		allow_update=False,
	)
	assert attr_val == 1


@pytest.mark.asyncio
async def test_validate_attr_INT_range_int_invalid():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_INT',
			attr_type=ATTR.INT(ranges=[[0, 10]]),
			attr_val=10,
			allow_update=False,
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_range_int():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(ranges=[[0, 10]]),
		attr_val=0,
		allow_update=False,
	)
	assert attr_val == 0


@pytest.mark.asyncio
async def test_validate_attr_INT_range_int_as_str():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(ranges=[[0, 10]]),
		attr_val='0',
		allow_update=False,
	)
	assert attr_val == 0


@pytest.mark.asyncio
async def test_validate_attr_INT_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(),
		attr_val=None,
		allow_update=True,
	)
	assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_INT_default_None():
	attr_type = ATTR.INT()
	attr_type._default = 'test_validate_attr_INT'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=attr_type,
		attr_val=None,
		allow_update=False,
	)
	assert attr_val == 'test_validate_attr_INT'


@pytest.mark.asyncio
async def test_validate_attr_INT_default_str():
	attr_type = ATTR.INT()
	attr_type._default = 'test_validate_attr_INT'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=attr_type,
		attr_val='str',
		allow_update=False,
	)
	assert attr_val == 'test_validate_attr_INT'


@pytest.mark.asyncio
async def test_validate_attr_INT_default_int_allow_none():
	attr_type = ATTR.INT()
	attr_type._default = 'test_validate_attr_INT'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=attr_type,
		attr_val='str',
		allow_update=True,
	)
	assert attr_val == None
