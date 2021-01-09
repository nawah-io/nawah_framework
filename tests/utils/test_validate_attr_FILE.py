from nawah.classes import ATTR
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_FILE_None():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_FILE',
			attr_type=ATTR.FILE(),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_FILE_int():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_FILE',
			attr_type=ATTR.FILE(),
			attr_val=1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_FILE_dict_invalid():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_FILE',
			attr_type=ATTR.FILE(),
			attr_val={'key': 'value'},
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_FILE_file():
	file_attr_val = {
		'name': '__filename',
		'type': 'mime/type',
		'lastModified': 0,
		'size': 6,
		'content': b'__file',
	}
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_FILE',
		attr_type=ATTR.FILE(),
		attr_val=file_attr_val,
		mode='create',
	)
	assert attr_val == file_attr_val


@pytest.mark.asyncio
async def test_validate_attr_FILE_file_list():
	file_attr_val = {
		'name': '__filename',
		'type': 'mime/type',
		'lastModified': 0,
		'size': 6,
		'content': b'__file',
	}
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_FILE',
		attr_type=ATTR.FILE(),
		attr_val=[file_attr_val],
		mode='create',
	)
	assert attr_val == file_attr_val


@pytest.mark.asyncio
async def test_validate_attr_FILE_None_allow_none():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_FILE',
		attr_type=ATTR.FILE(),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_FILE_default_None():
	attr_type = ATTR.FILE()
	attr_type._default = 'test_validate_attr_FILE'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_FILE',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_FILE'


@pytest.mark.asyncio
async def test_validate_attr_FILE_default_int():
	attr_type = ATTR.FILE()
	attr_type._default = 'test_validate_attr_FILE'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_FILE',
		attr_type=attr_type,
		attr_val=1,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_FILE'


@pytest.mark.asyncio
async def test_validate_attr_FILE_default_int_allow_none():
	attr_type = ATTR.FILE()
	attr_type._default = 'test_validate_attr_FILE'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_FILE',
		attr_type=attr_type,
		attr_val=1,
		mode='update',
	)
	assert attr_val == None
