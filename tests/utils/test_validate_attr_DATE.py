from nawah.classes import ATTR, InvalidAttrException
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_DATE_None():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_DATE',
			attr_type=ATTR.DATE(),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DATE_int():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_DATE',
			attr_type=ATTR.DATE(),
			attr_val=1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DATE_str_invalid():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_DATE',
			attr_type=ATTR.DATE(),
			attr_val='20200202',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DATE_date():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_DATE',
		attr_type=ATTR.DATE(),
		attr_val='2020-02-02',
		mode='create',
	)
	assert attr_val == '2020-02-02'


@pytest.mark.asyncio
async def test_validate_attr_DATE_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_DATE',
		attr_type=ATTR.DATE(),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_DATE_default_None():
	attr_type = ATTR.DATE()
	attr_type._default = 'test_validate_attr_DATE'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_DATE',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_DATE'


@pytest.mark.asyncio
async def test_validate_attr_DATE_default_int():
	attr_type = ATTR.DATE()
	attr_type._default = 'test_validate_attr_DATE'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_DATE',
		attr_type=attr_type,
		attr_val=1,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_DATE'


@pytest.mark.asyncio
async def test_validate_attr_DATE_default_int_allow_none():
	attr_type = ATTR.DATE()
	attr_type._default = 'test_validate_attr_DATE'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_DATE',
		attr_type=attr_type,
		attr_val=1,
		mode='update',
	)
	assert attr_val == None
