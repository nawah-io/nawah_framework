from nawah.classes import ATTR, InvalidAttrException
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_IP_None():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_IP',
			attr_type=ATTR.IP(),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_IP_int():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_IP',
			attr_type=ATTR.IP(),
			attr_val=1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_IP_str_invalid():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_IP',
			attr_type=ATTR.IP(),
			attr_val='str',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_IP_ip():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_IP',
		attr_type=ATTR.IP(),
		attr_val='127.0.0.1',
		mode='create',
	)
	assert attr_val == '127.0.0.1'


@pytest.mark.asyncio
async def test_validate_attr_IP_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_IP',
		attr_type=ATTR.IP(),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_IP_default_None():
	attr_type = ATTR.IP()
	attr_type._default = 'test_validate_attr_IP'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_IP',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_IP'


@pytest.mark.asyncio
async def test_validate_attr_IP_default_int():
	attr_type = ATTR.IP()
	attr_type._default = 'test_validate_attr_IP'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_IP',
		attr_type=attr_type,
		attr_val=1,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_IP'


@pytest.mark.asyncio
async def test_validate_attr_IP_default_int_allow_none():
	attr_type = ATTR.IP()
	attr_type._default = 'test_validate_attr_IP'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_IP',
		attr_type=attr_type,
		attr_val=1,
		mode='update',
	)
	assert attr_val == None
