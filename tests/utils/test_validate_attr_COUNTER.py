from nawah.classes import ATTR, InvalidAttrTypeException
from nawah import utils

from bson import ObjectId
from tests.conftest import Module

import pytest


@pytest.mark.asyncio
async def test_validate_attr_COUNTER_invalid_type():
	with pytest.raises(InvalidAttrTypeException):
		ATTR.COUNTER(pattern='not-valid-pattern')


@pytest.mark.asyncio
async def test_validate_attr_COUNTER_valid_type():
	from nawah.config import Config

	ATTR.COUNTER(pattern='O-$__values:0$__values:1$__values:2-$__counters.order_counter')
	assert Config.docs[0].doc['var'] == '__counter:order_counter'


@pytest.mark.asyncio
async def test_validate_attr_COUNTER_values(
	preserve_state, mock_module, mock_call_results
):
	import nawah.config

	with preserve_state(nawah.config, 'Config'):
		modules = {
			'setting': mock_module(
				read=mock_call_results(
					status=200,
					count=1,
					doc={
						'_id': ObjectId(),
						'val': 5,
					},
				),
			)
		}
		nawah.config.Config.modules = modules

		attr_type = ATTR.COUNTER(
			pattern='COUNTER-$__values:0$__values:1$__values:0-$__counters.order_counter',
			values=[
				lambda skip_events, env, query, doc: 42,
				lambda skip_events, env, query, doc: 24,
			],
		)
		attr_val = await utils.validate_attr(
			attr_name='test_validate_attr_COUNTER',
			attr_type=attr_type,
			attr_val=None,
			mode='create',
		)
		assert attr_val == 'COUNTER-422442-6'
