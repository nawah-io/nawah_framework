from nawah.classes import ATTR
from nawah import utils

import pytest


@pytest.mark.asyncio
async def test_validate_attr_ANY_None():
	with pytest.raises(utils.InvalidAttrException):
		await utils.validate_attr(
			attr_name='test_validate_attr_ANY',
			attr_type=ATTR.ANY(),
			attr_val=None,
			allow_update=False,
		)


@pytest.mark.asyncio
async def test_validate_attr_ANY_str():
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_ANY',
		attr_type=ATTR.ANY(),
		attr_val='test_validate_attr_ANY',
		allow_update=False,
	)
	assert attr_val == 'test_validate_attr_ANY'


@pytest.mark.asyncio
async def test_validate_attr_ANY_default_None():
	attr_type = ATTR.ANY()
	attr_type._default = 'test_validate_attr_ANY'
	attr_val = await utils.validate_attr(
		attr_name='test_validate_attr_ANY',
		attr_type=attr_type,
		attr_val=None,
		allow_update=False,
	)
	assert attr_val == 'test_validate_attr_ANY'
