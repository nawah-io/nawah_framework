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
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_str():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_INT',
			attr_type=ATTR.INT(),
			attr_val='str',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_float():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_INT',
			attr_type=ATTR.INT(),
			attr_val=1.1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_int():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(),
		attr_val=1,
		mode='create',
	)
	assert attr_val == 1


@pytest.mark.asyncio
async def test_validate_attr_INT_float_as_str():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_INT',
			attr_type=ATTR.INT(),
			attr_val='1.1',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_int_as_str():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(),
		attr_val='1',
		mode='create',
	)
	assert attr_val == 1


@pytest.mark.asyncio
async def test_validate_attr_INT_range_int_invalid():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_INT',
			attr_type=ATTR.INT(ranges=[[0, 10]]),
			attr_val=10,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_INT_range_int():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(ranges=[[0, 10]]),
		attr_val=0,
		mode='create',
	)
	assert attr_val == 0


@pytest.mark.asyncio
async def test_validate_attr_INT_range_int_as_str():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(ranges=[[0, 10]]),
		attr_val='0',
		mode='create',
	)
	assert attr_val == 0


@pytest.mark.asyncio
async def test_validate_attr_INT_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_INT',
		attr_type=ATTR.INT(),
		attr_val=None,
		mode='update',
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
		mode='create',
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
		mode='create',
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
		mode='update',
	)
	assert attr_val == None
