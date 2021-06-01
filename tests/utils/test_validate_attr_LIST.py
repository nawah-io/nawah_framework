from nawah.classes import ATTR
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_LIST_None():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LIST',
			attr_type=ATTR.LIST(list=[ATTR.STR()]),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LIST_int():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LIST',
			attr_type=ATTR.LIST(list=[ATTR.STR()]),
			attr_val=1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LIST_dict_invalid():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LIST',
			attr_type=ATTR.LIST(list=[ATTR.STR()]),
			attr_val={
				'key': 'value',
				'key2': 'value',
			},
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LIST_simple_list():
	list_attr_val = ['str', 'str', 'str']
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LIST',
		attr_type=ATTR.LIST(list=[ATTR.STR()]),
		attr_val=list_attr_val,
		mode='create',
	)
	assert attr_val == list_attr_val


@pytest.mark.asyncio
async def test_validate_attr_LIST_nested_list_invalid():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LIST',
			attr_type=ATTR.LIST(list=[ATTR.LIST(list=[ATTR.STR()])]),
			attr_val=['str', 'str', ['str']],
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LIST_nested_list():
	list_attr_val = [['str'], ['str', 'str'], ['str']]
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LIST',
		attr_type=ATTR.LIST(list=[ATTR.LIST(list=[ATTR.STR()])]),
		attr_val=list_attr_val,
		mode='create',
	)
	assert attr_val == list_attr_val


@pytest.mark.asyncio
async def test_validate_attr_LIST_nested_dict_invalid():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LIST',
			attr_type=ATTR.LIST(list=[ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT())]),
			attr_val=[{'key': 1}, {'key': 'val'}],
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LIST_nested_dict():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LIST',
		attr_type=ATTR.LIST(list=[ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT())]),
		attr_val=[{'key': 1}, {'key': '2'}],
		mode='create',
	)
	assert attr_val == [{'key': 1}, {'key': 2}]


@pytest.mark.asyncio
async def test_validate_attr_LIST_muti_list_invalid():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LIST',
			attr_type=ATTR.LIST(list=[ATTR.EMAIL(), ATTR.URI_WEB()]),
			attr_val=['info@nawah.masaar.com', 'http://sub.example.com', '1'],
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LIST_multi_list_invalid_count():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_LIST',
			attr_type=ATTR.LIST(list=[ATTR.EMAIL(), ATTR.URI_WEB()], min=1, max=2),
			attr_val=[
				'info@nawah.masaar.com',
				'http://sub.example.com',
				'https://sub.domain.com',
			],
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_LIST_typed_dict():
	list_attr_val = [
		'info@nawah.masaar.com',
		'http://sub.example.com',
		'https://sub.domain.com',
	]
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LIST',
		attr_type=ATTR.LIST(list=[ATTR.EMAIL(), ATTR.URI_WEB()], min=1, max=3),
		attr_val=list_attr_val,
		mode='create',
	)
	assert attr_val == list_attr_val


@pytest.mark.asyncio
async def test_validate_attr_LIST_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LIST',
		attr_type=ATTR.LIST(list=[ATTR.STR()]),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


# [TODO] Add tests for nested default values


@pytest.mark.asyncio
async def test_validate_attr_LIST_default_None():
	attr_type = ATTR.LIST(list=[ATTR.STR()])
	attr_type._default = 'test_validate_attr_LIST'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LIST',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_LIST'


@pytest.mark.asyncio
async def test_validate_attr_LIST_default_int():
	attr_type = ATTR.LIST(list=[ATTR.STR()])
	attr_type._default = 'test_validate_attr_LIST'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LIST',
		attr_type=attr_type,
		attr_val=[1],
		mode='create',
	)
	assert attr_val == 'test_validate_attr_LIST'


@pytest.mark.asyncio
async def test_validate_attr_LIST_default_int_allow_none():
	attr_type = ATTR.LIST(list=[ATTR.STR()])
	attr_type._default = 'test_validate_attr_LIST'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_LIST',
		attr_type=attr_type,
		attr_val=[1],
		mode='update',
	)
	assert attr_val == [None]
