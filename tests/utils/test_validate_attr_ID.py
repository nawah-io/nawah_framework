from nawah.classes import ATTR, InvalidAttrException
from nawah.utils import validate_attr

from bson import ObjectId
import pytest


@pytest.mark.asyncio
async def test_validate_attr_ID_None():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_ID',
			attr_type=ATTR.ID(),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_ID_int():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_ID',
			attr_type=ATTR.ID(),
			attr_val=1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_ID_str():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_ID',
		attr_type=ATTR.ID(),
		attr_val='000000000000000000000000',
		mode='create',
	)
	assert attr_val == ObjectId('000000000000000000000000')


@pytest.mark.asyncio
async def test_validate_attr_ID_objectid():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_ID',
		attr_type=ATTR.ID(),
		attr_val=ObjectId('000000000000000000000000'),
		mode='create',
	)
	assert attr_val == ObjectId('000000000000000000000000')


@pytest.mark.asyncio
async def test_validate_attr_ID_None_allow_none():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_ID',
		attr_type=ATTR.ID(),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_ID_default_None():
	attr_type = ATTR.ID()
	attr_type._default = 'test_validate_attr_ID'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_ID',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_ID'


@pytest.mark.asyncio
async def test_validate_attr_ID_default_int():
	attr_type = ATTR.ID()
	attr_type._default = 'test_validate_attr_ID'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_ID',
		attr_type=attr_type,
		attr_val=1,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_ID'


@pytest.mark.asyncio
async def test_validate_attr_ID_default_int_allow_none():
	attr_type = ATTR.ID()
	attr_type._default = 'test_validate_attr_ID'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_ID',
		attr_type=attr_type,
		attr_val=1,
		mode='update',
	)
	assert attr_val == None
