from nawah.base_module import BaseModule
from nawah.classes import ATTR, PERM, METHOD
from nawah.config import Config
from nawah.registry import Registry
from nawah.utils import extract_lambda_body


class Core(BaseModule):
	'''`Core` module provides access to ADMIN user to fetch `Nawah` instance.'''

	methods = {
		'retrieve_config': METHOD(
			permissions=[PERM(privilege='admin')],
			query_args={'config_attr': ATTR.STR()},
		),
		'retrieve_cache_sets': METHOD(
			permissions=[PERM(privilege='admin')],
			query_args={'module': ATTR.STR()},
		),
		'retrieve_cache_queries': METHOD(
			permissions=[PERM(privilege='admin')],
			query_args={'module': ATTR.STR(), 'cache_set': ATTR.INT()},
		),
		'retrieve_cache_results': METHOD(
			permissions=[PERM(privilege='admin')],
			query_args={
				'module': ATTR.STR(),
				'cache_set': ATTR.INT(),
				'query': ATTR.INT(),
			},
		),
	}

	async def retrieve_config(self, skip_events=[], env={}, query=[], doc={}):
		return self.status(
			status=200,
			msg='Config Attr value retrieved.',
			args={'value': getattr(Config, query['config_attr'][0])},
		)

	async def retrieve_cache_sets(self, skip_events=[], env={}, query=[], doc={}):
		return self.status(
			status=200,
			msg='Module Cache Sets retrieved.',
			args={
				'sets': [
					extract_lambda_body(cache_set.condition)
					for cache_set in Registry.module(query['module'][0]).cache
				]
			},
		)

	async def retrieve_cache_queries(self, skip_events=[], env={}, query=[], doc={}):
		return self.status(
			status=200,
			msg='Module Cache Sets queries retrieved.',
			args={
				'queries': list(
					Registry.module(query['module'][0]).cache[query['cache_set'][0]].queries.keys()
				)
			},
		)

	async def retrieve_cache_results(self, skip_events=[], env={}, query=[], doc={}):
		cache_set_query = list(
			Registry.module(query['module'][0]).cache[query['cache_set'][0]].queries.keys()
		)[query['query'][0]]
		return self.status(
			status=200,
			msg='Module Cache Sets results retrieved.',
			args={
				'results': Registry.module(query['module'][0])
				.cache[query['cache_set'][0]]
				.queries[cache_set_query]
				.results,
				'query_time': Registry.module(query['module'][0])
				.cache[query['cache_set'][0]]
				.queries[cache_set_query]
				.query_time.isoformat(),
			},
		)
