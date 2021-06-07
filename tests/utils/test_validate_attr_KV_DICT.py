from nawah.classes import ATTR, InvalidAttrException
from nawah.utils import validate_attr

import pytest


@pytest.mark.asyncio
async def test_validate_attr_DICT_None():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_DICT',
			attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.ANY()),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DICT_int():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_DICT',
			attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.ANY()),
			attr_val=1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DICT_dict_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_DICT',
			attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT()),
			attr_val={
				'key': 'value',
				'key2': 2,
			},
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DICT_simple_dict():
	dict_attr_val = {
		'key1': 3,
		'key2': 2,
	}
	attr_val = await validate_attr(
		attr_name='test_validate_attr_DICT',
		attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.ANY()),
		attr_val=dict_attr_val,
		mode='create',
	)
	assert attr_val == dict_attr_val


@pytest.mark.asyncio
async def test_validate_attr_DICT_nested_dict_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_DICT',
			attr_type=ATTR.KV_DICT(
				key=ATTR.STR(), val=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT())
			),
			attr_val={
				'key1': 'value',
				'key2': 2,
			},
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DICT_nested_dict():
	dict_attr_val = {
		'key1': {'child_key': 1},
		'key2': {'child_key': 2},
	}
	attr_val = await validate_attr(
		attr_name='test_validate_attr_DICT',
		attr_type=ATTR.KV_DICT(
			key=ATTR.STR(), val=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT())
		),
		attr_val=dict_attr_val,
		mode='create',
	)
	assert attr_val == dict_attr_val


@pytest.mark.asyncio
async def test_validate_attr_DICT_nested_list_dict_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_DICT',
			attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.LIST(list=[ATTR.INT()])),
			attr_val={
				'key1': ['a'],
			},
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DICT_nested_list_dict():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_DICT',
		attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.LIST(list=[ATTR.INT()])),
		attr_val={'key1': ['4'], 'key2': [1, '2', 3]},
		mode='create',
	)
	assert attr_val == {
		'key1': [4],
		'key2': [1, 2, 3],
	}


@pytest.mark.asyncio
async def test_validate_attr_DICT_req_dict():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_DICT',
		attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT(), req=['key3']),
		attr_val={'key1': '4', 'key2': 1, 'key3': 0},
		mode='create',
	)
	assert attr_val == {'key1': 4, 'key2': 1, 'key3': 0}


@pytest.mark.asyncio
async def test_validate_attr_DICT_min_req_dict_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_DICT',
			attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT(), min=3, req=['key3']),
			attr_val={'key1': '4', 'key3': 0},
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DICT_min_req_max_dict_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_DICT',
			attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT(), min=3, max=4, req=['key3']),
			attr_val={'key1': '4', 'key2': 3, 'key3': 0, 'key4': 5, 'key5': 2},
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_DICT_min_req_max_dict():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_DICT',
		attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT(), min=3, max=4, req=['key3']),
		attr_val={'key1': '4', 'key2': 3, 'key3': 0, 'key4': 5},
		mode='create',
	)
	assert attr_val == {'key1': 4, 'key2': 3, 'key3': 0, 'key4': 5}


@pytest.mark.asyncio
async def test_validate_attr_DICT_None_allow_none():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_DICT',
		attr_type=ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT()),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


# [TODO] Add tests for nested default values


@pytest.mark.asyncio
async def test_validate_attr_DICT_default_None():
	attr_type = ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT())
	attr_type._default = 'test_validate_attr_DICT'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_DICT',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_DICT'


@pytest.mark.asyncio
async def test_validate_attr_DICT_default_int():
	attr_type = ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT())
	attr_type._default = 'test_validate_attr_DICT'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_DICT',
		attr_type=attr_type,
		attr_val=1,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_DICT'


@pytest.mark.asyncio
async def test_validate_attr_DICT_default_int_allow_none():
	attr_type = ATTR.KV_DICT(key=ATTR.STR(), val=ATTR.INT())
	attr_type._default = 'test_validate_attr_DICT'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_DICT',
		attr_type=attr_type,
		attr_val=1,
		mode='update',
	)
	assert attr_val == None
