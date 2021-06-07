from nawah.classes import ATTR, InvalidAttrException
from nawah.utils import validate_attr

import pytest


@pytest.mark.asyncio
async def test_validate_attr_ANY_None():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_ANY',
			attr_type=ATTR.ANY(),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_ANY_str():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_ANY',
		attr_type=ATTR.ANY(),
		attr_val='test_validate_attr_ANY',
		mode='create',
	)
	assert attr_val == 'test_validate_attr_ANY'


@pytest.mark.asyncio
async def test_validate_attr_ANY_default_None():
	attr_type = ATTR.ANY()
	attr_type._default = 'test_validate_attr_ANY'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_ANY',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_ANY'
