from nawah.classes import ATTR
from nawah.data import _query

from bson import ObjectId


def test_compile_query_step_one_step_match_attr_ID_val_invalid_id(caplog):
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {'attr': ATTR.ID()}
	step = {'attr': 'match_term'}
	watch_mode = False
	_query._compile_query_step(
		aggregate_prefix=aggregate_prefix,
		aggregate_suffix=aggregate_suffix,
		aggregate_match=aggregate_match,
		collection_name=collection_name,
		attrs=attrs,
		step=step,
		watch_mode=watch_mode,
	)
	for record in caplog.records:
		assert record.levelname == 'WARNING'
		assert record.message == 'Failed to convert attr to ObjectId: match_term'
	assert aggregate_prefix == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	assert aggregate_suffix == [{'$group': {'_id': '$_id'}}]
	assert aggregate_match == [{'attr': 'match_term'}]


def test_compile_query_step_one_step_match_attr_ID_val_str():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {'attr': ATTR.ID()}
	step = {'attr': '000000000000000000000000'}
	watch_mode = False
	_query._compile_query_step(
		aggregate_prefix=aggregate_prefix,
		aggregate_suffix=aggregate_suffix,
		aggregate_match=aggregate_match,
		collection_name=collection_name,
		attrs=attrs,
		step=step,
		watch_mode=watch_mode,
	)
	assert aggregate_prefix == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	assert aggregate_suffix == [{'$group': {'_id': '$_id'}}]
	assert aggregate_match == [{'attr': ObjectId('000000000000000000000000')}]


def test_compile_query_step_one_step_match_attr_ID_val_id():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {'attr': ATTR.ID()}
	step = {'attr': ObjectId('000000000000000000000000')}
	watch_mode = False
	_query._compile_query_step(
		aggregate_prefix=aggregate_prefix,
		aggregate_suffix=aggregate_suffix,
		aggregate_match=aggregate_match,
		collection_name=collection_name,
		attrs=attrs,
		step=step,
		watch_mode=watch_mode,
	)
	assert aggregate_prefix == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	assert aggregate_suffix == [{'$group': {'_id': '$_id'}}]
	assert aggregate_match == [{'attr': ObjectId('000000000000000000000000')}]


def test_compile_query_step_one_step_match_attr_ID_val_list_invalid_id(caplog):
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {'attr': ATTR.ID()}
	step = {'attr': {'$in': ['match_term']}}
	watch_mode = False
	_query._compile_query_step(
		aggregate_prefix=aggregate_prefix,
		aggregate_suffix=aggregate_suffix,
		aggregate_match=aggregate_match,
		collection_name=collection_name,
		attrs=attrs,
		step=step,
		watch_mode=watch_mode,
	)
	# [DOC] Allow caplog.records to exceed 1 in case of other emitter of wanrnings
	assert len(caplog.records) >= 1
	for record in caplog.records:
		assert record.levelname == 'WARNING'
		assert record.message == 'Failed to convert child_attr to ObjectId: match_term'
	assert aggregate_prefix == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	assert aggregate_suffix == [{'$group': {'_id': '$_id'}}]
	assert aggregate_match == [{'attr': {'$in': ['match_term']}}]


def test_compile_query_step_one_step_match_attr_ID_val_list_str(caplog):
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {'attr': ATTR.ID()}
	step = {'attr': {'$in': ['000000000000000000000000']}}
	watch_mode = False
	_query._compile_query_step(
		aggregate_prefix=aggregate_prefix,
		aggregate_suffix=aggregate_suffix,
		aggregate_match=aggregate_match,
		collection_name=collection_name,
		attrs=attrs,
		step=step,
		watch_mode=watch_mode,
	)
	for record in caplog.records:
		assert (
			record.message
			!= 'Failed to convert child_attr to ObjectId: 000000000000000000000000'
		)
	assert aggregate_prefix == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	assert aggregate_suffix == [{'$group': {'_id': '$_id'}}]
	assert aggregate_match == [{'attr': {'$in': [ObjectId('000000000000000000000000')]}}]


def test_compile_query_step_one_step_match_attr_ID_val_list_id(caplog):
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {'attr': ATTR.ID()}
	step = {'attr': {'$in': [ObjectId('000000000000000000000000')]}}
	watch_mode = False
	_query._compile_query_step(
		aggregate_prefix=aggregate_prefix,
		aggregate_suffix=aggregate_suffix,
		aggregate_match=aggregate_match,
		collection_name=collection_name,
		attrs=attrs,
		step=step,
		watch_mode=watch_mode,
	)
	for record in caplog.records:
		assert (
			record.message
			!= 'Failed to convert child_attr to ObjectId: 000000000000000000000000'
		)
	assert aggregate_prefix == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	assert aggregate_suffix == [{'$group': {'_id': '$_id'}}]
	assert aggregate_match == [{'attr': {'$in': [ObjectId('000000000000000000000000')]}}]