from nawah.classes import ATTR
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_DATE_None():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_DATE',
			attr_type=ATTR.DATE(),
			attr_val=None,
			allow_update=False,
		)


@pytest.mark.asyncio
async def test_validate_attr_DATE_int():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_DATE',
			attr_type=ATTR.DATE(),
			attr_val=1,
			allow_update=False,
		)


@pytest.mark.asyncio
async def test_validate_attr_DATE_str_invalid():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_DATE',
			attr_type=ATTR.DATE(),
			attr_val='20200202',
			allow_update=False,
		)


@pytest.mark.asyncio
async def test_validate_attr_DATE_date():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_DATE',
		attr_type=ATTR.DATE(),
		attr_val='2020-02-02',
		allow_update=False,
	)
	assert attr_val == '2020-02-02'


@pytest.mark.asyncio
async def test_validate_attr_DATE_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_DATE',
		attr_type=ATTR.DATE(),
		attr_val=None,
		allow_update=True,
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
		allow_update=False,
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
		allow_update=False,
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
		allow_update=True,
	)
	assert attr_val == None
