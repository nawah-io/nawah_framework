from nawah.classes import ATTR, InvalidAttrException
from nawah.enums import LOCALE_STRATEGY
from nawah import utils, config

import pytest


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_None(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		with pytest.raises(InvalidAttrException):
			await utils.validate_attr(
				attr_name='test_validate_attr_LOCALE',
				attr_type=ATTR.LOCALE(),
				attr_val=None,
				mode='create',
			)


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_dict_invalid(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		with pytest.raises(InvalidAttrException):
			await utils.validate_attr(
				attr_name='test_validate_attr_LOCALE',
				attr_type=ATTR.LOCALE(),
				attr_val={
					'ar': 'str',
				},
				mode='create',
			)


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_locale_all(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		locale_attr_val = {
			'ar_AE': 'str',
			'en_AE': 'str',
			'de_DE': 'str',
		}
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALE',
			attr_type=ATTR.LOCALE(),
			attr_val=locale_attr_val,
			mode='create',
		)
		assert attr_val == locale_attr_val


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_locale_min_strategy_duplicate(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		locale_attr_val = {
			'ar_AE': 'str',
			'en_AE': 'str',
			'de_DE': 'str',
		}
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALE',
			attr_type=ATTR.LOCALE(),
			attr_val={
				'ar_AE': 'str',
			},
			mode='create',
		)
		assert attr_val == locale_attr_val


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_locale_min_strategy_none(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		config.Config.locale_strategy = LOCALE_STRATEGY.NONE_VALUE
		locale_attr_val = {
			'ar_AE': 'str',
			'en_AE': None,
			'de_DE': None,
		}
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALE',
			attr_type=ATTR.LOCALE(),
			attr_val={
				'ar_AE': 'str',
			},
			mode='create',
		)
		assert attr_val == locale_attr_val


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_locale_min_strategy_callable(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		config.Config.locale_strategy = (
			lambda attr_val, locale: f'DEFAULT:{locale}:{attr_val[config.Config.locale]}'
		)
		locale_attr_val = {
			'ar_AE': 'str',
			'en_AE': 'DEFAULT:en_AE:str',
			'de_DE': 'DEFAULT:de_DE:str',
		}
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALE',
			attr_type=ATTR.LOCALE(),
			attr_val={
				'ar_AE': 'str',
			},
			mode='create',
		)
		assert attr_val == locale_attr_val


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_locale_extra(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		with pytest.raises(InvalidAttrException):
			await utils.validate_attr(
				attr_name='test_validate_attr_LOCALE',
				attr_type=ATTR.LOCALE(),
				attr_val={
					'ar_AE': 'str',
					'invalid': 'str',
				},
				mode='create',
			)


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_None_allow_none(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALE',
			attr_type=ATTR.LOCALE(),
			attr_val=None,
			mode='update',
		)
		assert attr_val == None


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_default_None(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		attr_type = ATTR.LOCALE()
		attr_type._default = 'test_validate_attr_LOCALE'
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALE',
			attr_type=attr_type,
			attr_val=None,
			mode='create',
		)
		assert attr_val == 'test_validate_attr_LOCALE'


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_default_int(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		attr_type = ATTR.LOCALE()
		attr_type._default = 'test_validate_attr_LOCALE'
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALE',
			attr_type=attr_type,
			attr_val=1,
			mode='create',
		)
		assert attr_val == 'test_validate_attr_LOCALE'


@pytest.mark.asyncio
async def test_validate_attr_LOCALE_default_int_allow_none(preserve_state):
	with preserve_state(config, 'Config'):
		config.Config.locales = ['ar_AE', 'en_AE', 'de_DE']
		config.Config.locale = 'ar_AE'
		attr_type = ATTR.LOCALE()
		attr_type._default = 'test_validate_attr_LOCALE'
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_LOCALE',
			attr_type=attr_type,
			attr_val=1,
			mode='update',
		)
		assert attr_val == None
