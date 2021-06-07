from nawah.classes import ATTR, InvalidAttrException
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_UNION_None():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_UNION',
			attr_type=ATTR.UNION(union=[ATTR.STR(), ATTR.INT()]),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_UNION_float():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_UNION',
			attr_type=ATTR.UNION(union=[ATTR.STR(), ATTR.INT()]),
			attr_val=1.1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_UNION_str():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_UNION',
		attr_type=ATTR.UNION(union=[ATTR.STR(), ATTR.INT()]),
		attr_val='str',
		mode='create',
	)
	assert attr_val == 'str'


@pytest.mark.asyncio
async def test_validate_attr_UNION_int():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_UNION',
		attr_type=ATTR.UNION(union=[ATTR.STR(), ATTR.INT()]),
		attr_val=1,
		mode='create',
	)
	assert attr_val == 1


@pytest.mark.asyncio
async def test_validate_attr_UNION_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_UNION',
		attr_type=ATTR.UNION(union=[ATTR.STR(), ATTR.INT()]),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_UNION_default_None():
	attr_type = ATTR.UNION(union=[ATTR.STR(), ATTR.INT()])
	attr_type._default = 'test_validate_attr_UNION'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_UNION',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_UNION'


@pytest.mark.asyncio
async def test_validate_attr_UNION_default_float():
	attr_type = ATTR.UNION(union=[ATTR.STR(), ATTR.INT()])
	attr_type._default = 'test_validate_attr_UNION'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_UNION',
		attr_type=attr_type,
		attr_val=1.1,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_UNION'


@pytest.mark.asyncio
async def test_validate_attr_UNION_default_float_allow_none():
	attr_type = ATTR.UNION(union=[ATTR.STR(), ATTR.INT()])
	attr_type._default = 'test_validate_attr_UNION'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_UNION',
		attr_type=attr_type,
		attr_val=1.1,
		mode='update',
	)
	assert attr_val == None
