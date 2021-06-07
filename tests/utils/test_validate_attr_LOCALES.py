from nawah.classes import ATTR, InvalidAttrException
from nawah import utils, config

import pytest


@pytest.mark.asyncio
async def test_validate_attr_LOCALES_None(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		with pytest.raises(InvalidAttrException):
			await utils.validate_attr(
				attr_name='test_validate_attr_LOCALES',
				attr_type=ATTR.LOCALES(),
				attr_val=None,
				mode='create',
			)


@pytest.mark.asyncio
async def test_validate_attr_LOCALES_str_invalid(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		with pytest.raises(InvalidAttrException):
			await utils.validate_attr(
				attr_name='test_validate_attr_LOCALES',
				attr_type=ATTR.LOCALES(),
				attr_val='ar',
				mode='create',
			)


@pytest.mark.asyncio
async def test_validate_attr_LOCALES_locale(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALES',
			attr_type=ATTR.LOCALES(),
			attr_val='en_AE',
			mode='create',
		)
		assert attr_val == 'en_AE'


@pytest.mark.asyncio
async def test_validate_attr_LOCALES_None_allow_none(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALES',
			attr_type=ATTR.LOCALES(),
			attr_val=None,
			mode='update',
		)
		assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_LOCALES_default_None(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		attr_type = ATTR.LOCALES()
		attr_type._default = 'test_validate_attr_LOCALES'
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALES',
			attr_type=attr_type,
			attr_val=None,
			mode='create',
		)
		assert attr_val == 'test_validate_attr_LOCALES'


@pytest.mark.asyncio
async def test_validate_attr_LOCALES_default_int(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		attr_type = ATTR.LOCALES()
		attr_type._default = 'test_validate_attr_LOCALES'
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALES',
			attr_type=attr_type,
			attr_val=1,
			mode='create',
		)
		assert attr_val == 'test_validate_attr_LOCALES'


@pytest.mark.asyncio
async def test_validate_attr_LOCALES_default_int_allow_none(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		attr_type = ATTR.LOCALES()
		attr_type._default = 'test_validate_attr_LOCALES'
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALES',
			attr_type=attr_type,
			attr_val=1,
			mode='update',
		)
		assert attr_val == None
