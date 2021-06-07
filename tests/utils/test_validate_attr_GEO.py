from nawah.classes import ATTR, InvalidAttrException
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_GEO_None():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_GEO',
			attr_type=ATTR.GEO(),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_GEO_int():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_GEO',
			attr_type=ATTR.GEO(),
			attr_val=1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_GEO_dict_invalid():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_GEO',
			attr_type=ATTR.GEO(),
			attr_val={'key': 'value'},
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_GEO_geo():
	geo_attr_val = {'type': 'Point', 'coordinates': [21.422507, 39.826181]}
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_GEO',
		attr_type=ATTR.GEO(),
		attr_val=geo_attr_val,
		mode='create',
	)
	assert attr_val == geo_attr_val


@pytest.mark.asyncio
async def test_validate_attr_GEO_geo_as_str():
	with pytest.raises(InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_GEO',
			attr_type=ATTR.GEO(),
			attr_val={'type': 'Point', 'coordinates': ['21.422507', '39.826181']},
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_GEO_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_GEO',
		attr_type=ATTR.GEO(),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_GEO_default_None():
	attr_type = ATTR.GEO()
	attr_type._default = 'test_validate_attr_GEO'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_GEO',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_GEO'


@pytest.mark.asyncio
async def test_validate_attr_GEO_default_int():
	attr_type = ATTR.GEO()
	attr_type._default = 'test_validate_attr_GEO'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_GEO',
		attr_type=attr_type,
		attr_val=1,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_GEO'


@pytest.mark.asyncio
async def test_validate_attr_GEO_default_int_allow_none():
	attr_type = ATTR.GEO()
	attr_type._default = 'test_validate_attr_GEO'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_GEO',
		attr_type=attr_type,
		attr_val=1,
		mode='update',
	)
	assert attr_val == None
