from nawah.classes import Query
from nawah.data._query import _compile_query, _compile_query_step
from nawah.data._classes import InvalidQueryException

import pytest


def test_compile_query_invalid_query():
	with pytest.raises(InvalidQueryException):
		_compile_query(
			collection_name='collection_name', attrs={}, query=[], watch_mode=False
		)


def test_compile_query_empty():
	skip, limit, sort, group, aggregate_query = _compile_query(
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
	skip, limit, sort, group, aggregate_query = _compile_query(
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
	skip, limit, sort, group, aggregate_query = _compile_query(
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
	skip, limit, sort, group, aggregate_query = _compile_query(
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
	skip, limit, sort, group, aggregate_query = _compile_query(
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
	skip, limit, sort, group, aggregate_query = _compile_query(
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
	skip, limit, sort, group, aggregate_query = _compile_query(
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


def compile_query_step():
	pass
