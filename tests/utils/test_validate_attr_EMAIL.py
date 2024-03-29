from nawah.classes import ATTR, InvalidAttrException
from nawah.utils import validate_attr

import pytest


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_None():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_EMAIL',
			attr_type=ATTR.EMAIL(),
			attr_val=None,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_int():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_EMAIL',
			attr_type=ATTR.EMAIL(),
			attr_val=1,
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_str_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_EMAIL',
			attr_type=ATTR.EMAIL(),
			attr_val='str',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_email():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_EMAIL',
		attr_type=ATTR.EMAIL(),
		attr_val='info@nawah.foobar.baz',
		mode='create',
	)
	assert attr_val == 'info@nawah.foobar.baz'


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_allowed_domains_email_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_EMAIL',
			attr_type=ATTR.EMAIL(allowed_domains=['foo.com', 'bar.net']),
			attr_val='info@nawah.foobar.baz',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_allowed_domains_strict_email_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_EMAIL',
			attr_type=ATTR.EMAIL(allowed_domains=['foo.com', 'bar.net'], strict=True),
			attr_val='info@sub.foo.com',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_allowed_domains_email():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_EMAIL',
		attr_type=ATTR.EMAIL(allowed_domains=['foo.com', 'bar.net']),
		attr_val='info@sub.foo.com',
		mode='create',
	)
	assert attr_val == 'info@sub.foo.com'


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_allowed_domains_strict_email():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_EMAIL',
		attr_type=ATTR.EMAIL(allowed_domains=['foo.com', 'bar.net'], strict=True),
		attr_val='info@foo.com',
		mode='create',
	)
	assert attr_val == 'info@foo.com'


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_disallowed_domains_email_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_EMAIL',
			attr_type=ATTR.EMAIL(disallowed_domains=['foo.com', 'bar.net']),
			attr_val='info@nawah.foo.com',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_disallowed_domains_strict_email_invalid():
	with pytest.raises(InvalidAttrException):
		await validate_attr(
			attr_name='test_validate_attr_EMAIL',
			attr_type=ATTR.EMAIL(disallowed_domains=['foo.com', 'bar.net'], strict=True),
			attr_val='info@foo.com',
			mode='create',
		)


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_disallowed_domains_email():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_EMAIL',
		attr_type=ATTR.EMAIL(disallowed_domains=['foo.com', 'bar.net']),
		attr_val='info@sub.foobar.com',
		mode='create',
	)
	assert attr_val == 'info@sub.foobar.com'


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_disallowed_domains_strict_email():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_EMAIL',
		attr_type=ATTR.EMAIL(disallowed_domains=['foo.com', 'bar.net'], strict=True),
		attr_val='info@sub.foo.com',
		mode='create',
	)
	assert attr_val == 'info@sub.foo.com'


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_None_allow_none():
	attr_val = await validate_attr(
		attr_name='test_validate_attr_EMAIL',
		attr_type=ATTR.EMAIL(),
		attr_val=None,
		mode='update',
	)
	assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_default_None():
	attr_type = ATTR.EMAIL()
	attr_type._default = 'test_validate_attr_EMAIL'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_EMAIL',
		attr_type=attr_type,
		attr_val=None,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_EMAIL'


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_default_int():
	attr_type = ATTR.EMAIL()
	attr_type._default = 'test_validate_attr_EMAIL'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_EMAIL',
		attr_type=attr_type,
		attr_val=1,
		mode='create',
	)
	assert attr_val == 'test_validate_attr_EMAIL'


@pytest.mark.asyncio
async def test_validate_attr_EMAIL_default_int_allow_none():
	attr_type = ATTR.EMAIL()
	attr_type._default = 'test_validate_attr_EMAIL'
	attr_val = await validate_attr(
		attr_name='test_validate_attr_EMAIL',
		attr_type=attr_type,
		attr_val=1,
		mode='update',
	)
	assert attr_val == None
