from nawah.classes import ATTR
from nawah.data import _query


def test_compile_query_step_empty_step_dict():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = {}
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
	assert aggregate_match == []


def test_compile_query_step_empty_step_list():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = []
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
	assert aggregate_match == []


def test_compile_query_step_empty_step_list_dict():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = [{}]
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
	assert aggregate_match == []


def test_compile_query_step_empty_step_list_multi_dict():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = [{}, {}]
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
	assert aggregate_match == []


def test_compile_query_step_empty_step_dict_or_empty():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = {'__or': {}}
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
	assert aggregate_match == []


def test_compile_query_step_empty_step_dict_or_dict():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = {'__or': {'test': 'match'}}
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
	assert aggregate_match == [{'test': 'match'}]


def test_compile_query_step_empty_step_dict_or_dict_multi_attrs():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = {'__or': {'attr1': 'match_term', 'attr2': 'match_term2'}}
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
	assert aggregate_match == [
		{'$and': [{'attr1': 'match_term'}, {'attr2': 'match_term2'}]}
	]


def test_compile_query_step_empty_step_dict_or_list_dict():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = {'__or': [{'attr1': 'match_term', 'attr2': 'match_term2'}]}
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
	assert aggregate_match == [
		{'$and': [{'attr1': 'match_term'}, {'attr2': 'match_term2'}]}
	]


def test_compile_query_step_empty_step_dict_or_list_multi_dict():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = {'__or': [{'attr1': 'match_term'}, {'attr2': 'match_term2'}]}
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
	assert aggregate_match == [
		{'$or': [{'attr1': 'match_term'}, {'attr2': 'match_term2'}]}
	]


def test_compile_query_step_empty_step_dict_or_list_dict_multi_attrs():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
	step = {
		'__or': [{'attr1': 'match_term'}, {'attr2': 'match_term2', 'attr3': 'match_term3'}]
	}
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
	assert aggregate_match == [
		{
			'$or': [
				{'attr1': 'match_term'},
				{'$and': [{'attr2': 'match_term2'}, {'attr3': 'match_term3'}]},
			]
		}
	]


def test_compile_query_step_one_step_match_not_attr():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {}
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
	assert aggregate_prefix == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	assert aggregate_suffix == [{'$group': {'_id': '$_id'}}]
	assert aggregate_match == [{'attr': 'match_term'}]


def test_compile_query_step_one_step_match_attr():
	aggregate_prefix = [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	aggregate_suffix = [{'$group': {'_id': '$_id'}}]
	aggregate_match = []
	collection_name = 'collection_name'
	attrs = {'attr': ATTR.ANY()}
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
	assert aggregate_prefix == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
	]
	assert aggregate_suffix == [{'$group': {'_id': '$_id'}}]
	assert aggregate_match == [{'attr': 'match_term'}]