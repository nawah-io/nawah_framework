from nawah.classes import ATTR, InvalidAttrException
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_LITERAL_None():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LITERAL',
			attr_type=ATTR.LITERAL(literal=['str', 0, 1.1]),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LITERAL_str_invalid():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LITERAL',
			attr_type=ATTR.LITERAL(literal=['str', 0, 1.1]),
			attr_val='0',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LITERAL_int_invalid():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LITERAL',
			attr_type=ATTR.LITERAL(literal=['str', 0, 1.1]),
			attr_val=1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LITERAL_str():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LITERAL',
		attr_type=ATTR.LITERAL(literal=['str', 0, 1.1]),
		attr_val='str',
		mode='create',
	)
	assert attr_val == 'str'


@pytest.mark.asyncio
async def test_validate_attr_LITERAL_int():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LITERAL',
		attr_type=ATTR.LITERAL(literal=['str', 0, 1.1]),
		attr_val=0,
		mode='create',
	)
	assert attr_val == 0


@pytest.mark.asyncio
async def test_validate_attr_LITERAL_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LITERAL',
		attr_type=ATTR.LITERAL(literal=['str', 0, 1.1]),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_LITERAL_default_None():
	attr_type = ATTR.LITERAL(literal=['str', 0, 1.1])
	attr_type._default = 'test_validate_attr_LITERAL'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LITERAL',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_LITERAL'


@pytest.mark.asyncio
async def test_validate_attr_LITERAL_default_int():
	attr_type = ATTR.LITERAL(literal=['str', 0, 1.1])
	attr_type._default = 'test_validate_attr_LITERAL'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LITERAL',
		attr_type=attr_type,
		attr_val=1,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_LITERAL'


@pytest.mark.asyncio
async def test_validate_attr_LITERAL_default_int_allow_none():
	attr_type = ATTR.LITERAL(literal=['str', 0, 1.1])
	attr_type._default = 'test_validate_attr_LITERAL'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LITERAL',
		attr_type=attr_type,
		attr_val=1,
		mode='update',
	)
	assert attr_val == None
