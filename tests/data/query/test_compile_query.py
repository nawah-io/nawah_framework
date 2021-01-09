from nawah.classes import Query, ATTR
from nawah.data import _query
from nawah.data._classes import InvalidQueryException

import pytest


def test_compile_query_invalid_query():
	with pytest.raises(InvalidQueryException):
		_query._compile_query(
			collection_name='collection_name', attrs={}, query=[], watch_mode=False
		)


def test_compile_query_empty():
	skip, limit, sort, group, aggregate_query = _query._compile_query(
		collection_name='collection_name', attrs={}, query=Query([]), watch_mode=False
	)
	assert skip == None
	assert limit == None
	assert sort == {'_id': -1}
	assert group == None
	assert aggregate_query == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
		{'$group': {'_id': '$_id'}},
	]


def test_compile_query_skip():
	skip, limit, sort, group, aggregate_query = _query._compile_query(
		collection_name='collection_name',
		attrs={},
		query=Query([{'$skip': 1}]),
		watch_mode=False,
	)
	assert skip == 1
	assert limit == None
	assert sort == {'_id': -1}
	assert group == None
	assert aggregate_query == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
		{'$group': {'_id': '$_id'}},
	]


def test_compile_query_limit():
	skip, limit, sort, group, aggregate_query = _query._compile_query(
		collection_name='collection_name',
		attrs={},
		query=Query([{'$limit': 10}]),
		watch_mode=False,
	)
	assert skip == None
	assert limit == 10
	assert sort == {'_id': -1}
	assert group == None
	assert aggregate_query == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
		{'$group': {'_id': '$_id'}},
	]


def test_compile_query_sort():
	skip, limit, sort, group, aggregate_query = _query._compile_query(
		collection_name='collection_name',
		attrs={},
		query=Query([{'$sort': {'create_time': 1}}]),
		watch_mode=False,
	)
	assert skip == None
	assert limit == None
	assert sort == {'create_time': 1}
	assert group == None
	assert aggregate_query == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
		{'$group': {'_id': '$_id'}},
	]


def test_compile_query_group():
	skip, limit, sort, group, aggregate_query = _query._compile_query(
		collection_name='collection_name',
		attrs={},
		query=Query([{'$group': [{'by': 'price', 'count': 10}]}]),
		watch_mode=False,
	)
	assert skip == None
	assert limit == None
	assert sort == {'_id': -1}
	assert group == [{'by': 'price', 'count': 10}]
	assert aggregate_query == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
		{'$group': {'_id': '$_id'}},
	]


def test_compile_query_search():
	skip, limit, sort, group, aggregate_query = _query._compile_query(
		collection_name='collection_name',
		attrs={},
		query=Query([{'$search': 'search_term'}]),
		watch_mode=False,
	)
	assert skip == None
	assert limit == None
	assert sort == {'_id': -1}
	assert group == None
	assert aggregate_query == [
		{'$match': {'$text': {'$search': 'search_term'}}},
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
		{'$project': {'_id': '$_id', '__score': {'$meta': 'textScore'}}},
		{'$match': {'__score': {'$gt': 0.5}}},
		{'$group': {'_id': '$_id'}},
	]


def test_compile_query_geo_near():
	skip, limit, sort, group, aggregate_query = _query._compile_query(
		collection_name='collection_name',
		attrs={},
		query=Query(
			[{'$geo_near': {'val': [21.422507, 39.826181], 'attr': 'str', 'dist': 1000}}]
		),
		watch_mode=False,
	)
	assert skip == None
	assert limit == None
	assert sort == {'_id': -1}
	assert group == None
	assert aggregate_query == [
		{
			'$geoNear': {
				'near': {'type': 'Point', 'coordinates': [21.422507, 39.826181]},
				'distanceField': 'str.__distance',
				'maxDistance': 1000,
				'spherical': True,
			}
		},
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
		{'$group': {'_id': '$_id'}},
	]


def test_compile_query_attrs_not_in_attrs():
	skip, limit, sort, group, aggregate_query = _query._compile_query(
		collection_name='collection_name',
		attrs={},
		query=Query([{'$attrs': ['attr1', 'attr2']}]),
		watch_mode=False,
	)
	assert skip == None
	assert limit == None
	assert sort == {'_id': -1}
	assert group == None
	assert aggregate_query == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
		{'$group': {'_id': '$_id'}},
	]


def test_compile_query_attrs_mixed_in_attrs():
	skip, limit, sort, group, aggregate_query = _query._compile_query(
		collection_name='collection_name',
		attrs={'attr1': ATTR.ANY()},
		query=Query([{'$attrs': ['attr1', 'attr2']}]),
		watch_mode=False,
	)
	assert skip == None
	assert limit == None
	assert sort == {'_id': -1}
	assert group == None
	assert aggregate_query == [
		{'$match': {'__deleted': {'$exists': False}}},
		{'$match': {'__create_draft': {'$exists': False}}},
		{'$match': {'__update_draft': {'$exists': False}}},
		{'$group': {'_id': '$_id', 'attr1': {'$first': '$attr1'}}},
	]


def test_compile_query_no_steps(mocker):
	mock_compile_query_step = mocker.patch.object(_query, '_compile_query_step')
	_query._compile_query(
		collection_name='collection_name',
		attrs={},
		query=Query([]),
		watch_mode=False,
	)
	mock_compile_query_step.assert_not_called()


def test_compile_query_one_step(mocker):
	mock_compile_query_step = mocker.patch.object(_query, '_compile_query_step')
	_query._compile_query(
		collection_name='collection_name',
		attrs={},
		query=Query([{'attr': 'match_term'}]),
		watch_mode=False,
	)
	mock_compile_query_step.assert_called_once_with(
		aggregate_prefix=[
			{'$match': {'__deleted': {'$exists': False}}},
			{'$match': {'__create_draft': {'$exists': False}}},
			{'$match': {'__update_draft': {'$exists': False}}},
		],
		aggregate_suffix=[{'$group': {'_id': '$_id'}}],
		aggregate_match=[],
		collection_name='collection_name',
		attrs={},
		step={'attr': 'match_term'},
		watch_mode=False,
	)