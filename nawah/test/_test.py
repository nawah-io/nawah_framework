from nawah.config import Config
from nawah.enums import Event
from nawah.classes import (
	ATTR,
	JSONEncoder,
	Query,
	NAWAH_QUERY,
	NAWAH_DOC,
	NAWAH_ENV,
	DictObj,
)
from nawah.utils import extract_attr, validate_attr, generate_attr

from bson import ObjectId
from typing import List, Dict, Union, Tuple, Literal, Any, TypedDict, cast, Iterable

import logging, traceback, datetime, os, json, copy

logger = logging.getLogger('test')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [TEST] [%(levelname)s]  %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.DEBUG)


RESULTS_STATS = TypedDict(
	'RESULTS_STATS', {'passed': int, 'failed': int, 'skipped': int, 'total': int}
)
RESULTS = TypedDict(
	'RESULTS',
	{
		'test': List['STEP'],
		'status': Literal['PASSED', 'PARTIAL', 'FAILED', True, False],
		'success_rate': int,
		'stats': RESULTS_STATS,
		'steps': List[Dict[str, Any]],
	},
)


class InvalidTestStepException(Exception):
	def __init__(self, *, msg: str):
		self.msg = msg

	def __str__(self):
		return self.msg


class TEST(list):
	pass


class STEP:
	_step: Literal['AUTH', 'SIGNOUT', 'CALL', 'TEST', 'ASSIGN_VAR', 'SET_REALM']
	_args: Dict[str, Any]

	def __init__(
		self,
		*,
		step: Literal['AUTH', 'SIGNOUT', 'CALL', 'TEST', 'ASSIGN_VAR', 'SET_REALM'],
		**kwargs: Any,
	):
		self._step = step
		self._args = kwargs

	@classmethod
	def AUTH(cls, *, var: str, val: str, hash: str):
		return STEP(step='AUTH', var=var, val=val, hash=hash)

	@classmethod
	def SIGNOUT(cls):
		return STEP(step='SIGNOUT')

	@classmethod
	def CALL(
		cls,
		*,
		module: str,
		method: str,
		skip_events: List[str] = None,
		query: NAWAH_QUERY = None,
		doc: NAWAH_DOC = None,
		acceptance: Dict[str, Any] = {'status': 200},
	):
		if not skip_events:
			skip_events = []
		if not query:
			query = []
		if not doc:
			doc = {}
		return STEP(
			step='CALL',
			module=module,
			method=method,
			skip_events=skip_events,
			query=query,
			doc=doc,
			acceptance=acceptance,
		)

	@classmethod
	def TEST(cls, *, test: str, steps: Union[List[int], range] = None):
		return STEP(step='TEST', test=test, steps=steps)

	@classmethod
	def ASSIGN_VAR(cls, *, vars: dict):
		return STEP(step='ASSIGN_VAR', vars=vars)

	@classmethod
	def SET_REALM(cls, *, realm: str):
		return STEP(step='SET_REALM')

	@classmethod
	async def validate_step(cls, *, step: 'STEP'):
		logger.debug(f'Attempting to validate test step: {step}')
		if step._step == 'AUTH':
			logger.debug(f'Validating test step \'AUTH\' with args: {step._args}')
			if step._args['var'] not in Config.user_attrs.keys():
				raise InvalidTestStepException(
					msg=f'Test step arg \'var\' is invalid. Found \'{step._args["var"]}\', but expecting one of: {list(Config.user_attrs.keys())}.'
				)
			if step._args['val'].startswith('$__'):
				logger.debug(
					'Detected test step \'AUTH\' with Test Variable \'val\' arg. Skipping validating test arg \'val\'.'
				)
			else:
				try:
					await validate_attr(
						mode='create',
						attr_name='val',
						attr_type=Config.user_attrs[step._args['var']],
						attr_val=step._args['val'],
					)
				except InvalidTestStepException:
					raise InvalidTestStepException(
						msg=f'Test step arg \'val\' of type \'{type(step._args["val"])}\' is invalid with required type \'{Config.user_attrs[step._args["var"]]._type}\'.'
					)
		elif step._step == 'SIGNOUT':
			logger.debug('Skipping validating test step \'SIGNOUT\'.')
		elif step._step == 'CALL':
			logger.debug(f'Validating test step \'CALL\' with args: {step._args}')
			if step._args['module'] not in Config.modules.keys():
				raise InvalidTestStepException(
					msg=f'Test step arg \'module\' is invalid. Unknown Nawah module \'{step._args["module"]}\'.'
				)
			if step._args['method'] not in Config.modules[step._args['module']].methods.keys():
				raise InvalidTestStepException(
					msg=f'Test step arg \'method\' is invalid. Unknown method \'{step._args["method"]}\'.'
				)
		elif step._step == 'TEST':
			logger.debug(f'Validating test step \'TEST\' with args: {step._args}')
			if step._args['test'] not in Config.tests.keys():
				raise InvalidTestStepException(
					msg=f'Test step arg \'test\' is invalid. Unknown test \'{step._args["test"]}\'.'
				)
			if step._args['steps'] != None and (
				type(step._args['steps']) not in [list, range]
				or sum(step for step in step._args['steps'] if type(step) != int)
			):
				raise InvalidTestStepException(
					msg='Test step arg \'steps\' is invalid. Either value is not of type \'list\', nor \'range\' or at least on item in the list is not of type \'int\'.'
				)
		elif step._step == 'ASSIGN_VAR':
			logger.debug('Skipping validating test step \'ASSIGN_VAR\'.')
		else:
			raise InvalidTestStepException(
				msg=f'Unknown test step \'{step._step}\' with args: {step._args}.'
			)


class CALC:
	_opers: Dict[str, str] = {
		'+': '__add__',
		'-': '__sub__',
		'*': '__mul__',
		'/': '__truediv__',
		'**': '__pow__',
	}
	_oper: Literal['+', '-', '*', '/', '**']
	_attrs: List[Any]

	def __init__(self, *, oper: Literal['+', '-', '*', '/', '**'], attrs: List[Any]):
		self._oper = oper
		self._attrs = attrs

	def execute(self, *, results: RESULTS, step: Dict[str, Any]):
		calc_results: int = None
		for i in range(len(self._attrs)):
			# [DOC] Attempt to extract attr, execute oper
			self._attrs[i] = Test.process_value(value=self._attrs[i], results=results, step=step)
			if type(self._attrs[i]) in [CALC, CAST, JOIN]:
				self._attrs[i] = self._attrs[i].execute(results=results, step=step)
			# [DOC] Calculate results per _oper
			if i == 0:
				calc_results = self._attrs[i]
			else:
				calc_results = getattr(
					(calc_results if calc_results else 0), self._opers[self._oper]
				)(self._attrs[i])
		return calc_results


class CAST:
	_type: Literal['int', 'float', 'str']
	_attr: Any

	def __init__(self, *, type: Literal['int', 'float', 'str'], attr: Any):
		self._type = type
		self._attr = attr

	def execute(self, *, results: RESULTS, step: Dict[str, Any]):
		# [DOC] Attempt to extract attr, execute oper
		self._attr = Test.process_value(value=self._attr, results=results, step=step)
		if type(self._attr) in [CALC, CAST, JOIN]:
			self._attr = self._attr.execute(results=results, step=step)
		# [DOC] Cast per _type
		if self._type == 'int':
			return int(self._attr)
		elif self._type == 'float':
			return float(self._attr)
		elif self._type == 'str':
			return str(self._attr)


class JOIN:
	_separator: str
	_attrs: List[Any]

	def __init__(self, *, separator: str, attrs: List[Any]):
		self._separator = separator
		self._attrs = attrs

	def execute(self, *, results: RESULTS, step: Dict[str, Any]):
		for i in range(len(self._attrs)):
			# [DOC] Attempt to extract attr, execute oper
			self._attrs[i] = Test.process_value(value=self._attrs[i], results=results, step=step)
			if type(self._attrs[i]) in [CALC, CAST, JOIN]:
				self._attrs[i] = self._attrs[i].execute(results=results, step=step)
		# [DOC] Join using _separator
		return self._separator.join(self._attrs)


class Test:
	session: DictObj
	env: NAWAH_ENV
	vars: Dict[str, Any] = {}

	@classmethod
	async def run_test(cls, *, test_name: str, steps: List[STEP] = None) -> RESULTS:
		if test_name not in Config.tests.keys():
			logger.error('Specified test is not defined in loaded config.')
			logger.debug(f'Loaded tests: {list(Config.tests.keys())}')
			exit(1)

		test: List[STEP] = Config.tests[test_name]
		results: RESULTS = {
			'test': Config.tests[test_name],
			'status': 'PASSED',
			'success_rate': 100,
			'stats': {'passed': 0, 'failed': 0, 'skipped': 0, 'total': 0},
			'steps': [],
		}

		step_failed = False
		for i in range(len(test)):
			results['stats']['total'] += 1
			step = copy.deepcopy(test[i])

			if type(step) != STEP:
				logger.error('Detected non-test-step item.')
				logger.error(f'Item: {step}')
				logger.error('Exiting.')
				exit(1)

			if steps and i not in steps:
				results['stats']['total'] -= 1
				results['stats']['skipped'] += 1
				continue

			if step_failed and not Config.test_force:
				results['stats']['skipped'] += 1
				continue

			if step._step == 'AUTH':
				try:
					# [DOC] Check for possible values requiring processing
					for attr in ['var', 'val', 'hash']:
						step._args[attr] = cls.process_value(
							value=step._args[attr], results=results, step={}
						)

					await STEP.validate_step(step=step)
					step = STEP.CALL(
						module='session',
						method='auth',
						doc={
							step._args['var']: step._args['val'],
							'hash': step._args['hash'],
						},
					)
				except InvalidTestStepException as e:
					logger.error(f'Can\'t process test step \'AUTH\' with error: {e} Exiting.')
					exit(1)
			elif step._step == 'SIGNOUT':
				step = STEP.CALL(module='session', method='signout', query=[{'_id': '$__session'}])
			else:
				try:
					await STEP.validate_step(step=step)
				except InvalidTestStepException as e:
					logger.error(f'{e} Exiting.')
					exit(1)

			if step._step == 'CALL':
				call_results = await cls.run_call(results=results, **step._args)
				if 'session' in call_results.keys():
					logger.debug('Updating session after detecting \'session\' in call results.')
					if str(call_results['session']._id) == 'f00000000000000000000012':
						cls.session = DictObj(
							{
								**Config.compile_anon_session(),
								'user': DictObj(Config.compile_anon_user()),
							}
						)
					else:
						cls.session = call_results['session']
				results['steps'].append(call_results)

			elif step._step == 'TEST':
				test_results = await cls.run_test(
					test_name=step._args['test'], steps=step._args['steps']
				)
				if test_results['status'] == 'PASSED':
					test_results['status'] = True
				else:
					test_results['status'] = False
				results['steps'].append(test_results)  # type: ignore

			elif step._step == 'ASSIGN_VAR':
				vars: Dict[str, Any] = {}
				test_step = {'step': 'assign_var', 'vars': vars, 'status': True}
				for var in step._args['vars'].keys():
					cls.vars[var] = vars[var] = cls.process_value(
						value=step._args['vars'][var], results=results, step=test_step
					)
				results['steps'].append(test_step)

			elif step._step == 'SET_REALM':
				try:
					step._args['realm'] = cls.process_value(
						value=step._args['realm'], results=results, step=call_results
					)
					logger.debug(f'Updating realm to \'{step._args["realm"]}\'.')
					cls.env['realm'] = step._args['realm']
					results['steps'].append(
						{
							'step': 'set_realm',
							'realm': step._args['realm'],
							'status': True,
						}
					)
				except Exception as e:
					logger.error(e)
					results['steps'].append(
						{
							'step': 'set_realm',
							'realm': step._args['realm'],
							'status': False,
						}
					)

			if not results['steps'][-1]['status']:
				results['stats']['failed'] += 1
				if not Config.test_force:
					step_failed = True
			else:
				results['stats']['passed'] += 1

		if len(results['steps']) == 0:
			logger.error('No steps tested. Exiting.')
			exit(1)

		results['success_rate'] = int(
			(results['stats']['passed'] / results['stats']['total']) * 100
		)
		if results['success_rate'] == 0:
			results['status'] = 'FAILED'
		elif results['success_rate'] == 100:
			results['status'] = 'PASSED'
		else:
			results['status'] = 'PARTIAL'

		if test_name == Config.test_name:
			logger.debug(
				'Finished testing %s steps [Passed: %s, Failed: %s, Skipped: %s] with success rate of: %s%%',
				results['stats']['total'],
				results['stats']['passed'],
				results['stats']['failed'],
				results['stats']['skipped'],
				results['success_rate'],
			)
			tests_log = os.path.join(
				Config._app_path,
				'tests',
				f'NAWAH-TEST_{test_name}_{datetime.datetime.utcnow().strftime("%d-%b-%Y")}',
			)
			if os.path.exists(f'{tests_log}.json'):
				i = 1
				while True:
					if os.path.exists(f'{tests_log}.{i}.json'):
						i += 1
					else:
						tests_log = f'{tests_log}.{i}'
						break
			tests_log += '.json'
			with open(tests_log, 'w') as f:
				f.write(json.dumps(json.loads(JSONEncoder().encode(results)), indent=4))
				logger.debug(f'Full tests log available at: {tests_log}')
			if results['success_rate'] == 100:
				exit(0)
			else:
				exit(1)
		else:
			return results

	@classmethod
	async def run_call(
		cls,
		*,
		results: RESULTS,
		module: str,
		method: str,
		skip_events: List[Event],
		query: List[Any],
		doc: NAWAH_DOC,
		acceptance: Dict[str, Any],
	):
		step: Dict[str, Any] = {
			'step': 'call',
			'module': module,
			'method': method,
			'query': None,
			'doc': None,
			'results': None,
			'acceptance': None,
			'status': True,
		}
		step['query'] = cls.process_obj(results=results, step=step, obj=query)  # type: ignore
		step['doc'] = cls.process_obj(results=results, step=step, obj=doc)  # type: ignore
		try:
			step['results'] = await Config.modules[module].methods[method](
				skip_events=skip_events,
				env={**cls.env, 'session': cls.session},
				query=step['query'],
				doc=step['doc'],
				call_id='__TEST__',
			)
			step['acceptance'] = cls.process_obj(
				results=results,
				step=step,
				obj=copy.deepcopy(acceptance),
			)
			for measure in acceptance.keys():
				if measure.startswith('session.'):
					results_measure = extract_attr(
						scope=cls.session,
						attr_path=f'$__{measure.replace("session.", "", 1)}',
					)
				else:
					results_measure = extract_attr(scope=step['results'], attr_path=f'$__{measure}')
				if results_measure != step['acceptance'][measure]:
					step['status'] = False
					cls.break_debugger(scope=locals(), call_results=step)
					break
			if step['status'] == False:
				logger.debug(
					f'Test step \'call\' failed at measure \'{measure}\'. Required value is \'{step["acceptance"][measure]}\', but test results is \'{results_measure}\''
				)
				step['measure'] = measure
		except Exception as e:
			tb = traceback.format_exc()
			logger.error(f'Exception occurred: {tb}')
			cls.break_debugger(scope=locals(), call_results=step)
			step.update(
				{
					'measure': measure,
					'results': {
						'status': 500,
						'msg': str(e),
						'args': {'tb': tb, 'code': 'SERVER_ERROR'},
					},
				}
			)
			step['status'] = False
			step['measure'] = measure
		if step['status'] == True and 'session' in step['results'].args:
			step['session'] = step['results'].args.session
		return step

	@classmethod
	def process_obj(
		cls,
		*,
		results: RESULTS,
		step: Dict[str, Any],
		obj: Union[Dict[str, Any], List[Any]],
	) -> Union[Dict[str, Any], List[Any]]:
		logger.debug(f'Attempting to process object: {obj}')

		# [DOC] Check if obj is callable
		if callable(obj):
			logger.debug(f'Object is callable. Calling it to extract returned object.')
			obj = obj(session=cls.session, vars=cls.vars, results=results, step=step)
			logger.debug(f'- Returned object: {obj}')

		obj_iter: Iterable
		if type(obj) == dict:
			obj = cast(Dict[str, Any], obj)
			obj_iter = obj.keys()
		elif type(obj) == list:
			obj = cast(List[Any], obj)
			obj_iter = range(len(obj))
		else:
			logger.error(
				f'Object is not of types \'dict\' or \'list\'. Refer to log to check how invalid type obj was attempted to be processed. Exiting.'
			)
			exit(1)

		for j in obj_iter:
			obj[j] = cls.process_value(value=obj[j], results=results, step=step)

		logger.debug(f'Processed object: {obj}')
		return obj

	@classmethod
	def process_value(cls, *, value, results, step):
		if type(value) == ATTR:
			# [DOC] Check for impossible to generate KV_DICT Attr Type value where min+len(req) > max
			if value._type == 'KV_DICT':
				if value._args['max']:
					if (value._args['min'] or 0) + len(value._args['req'] or []) > value._args['max']:
						logger.error(
							f'Attr Generator of type \'KV_DICT\' where Attr Arg \'min\' and length of Attr Arg \'req\' are greater than Attr Arg \'max\' can\'t be generated. Exiting.'
						)
						exit(1)
			return generate_attr(attr_type=value)

		elif type(value) in [CALC, CAST, JOIN]:
			return value.execute(results=results, step=step)

		elif type(value) == dict:
			return cls.process_obj(results=results, step=step, obj=value)

		elif type(value) == list:
			if len(value) and type(value[0]) == dict and '__attr' in value[0].keys():
				if 'count' not in value[0].keys():
					value[0]['count'] = 1
				return [
					generate_attr(attr_type=value[0]['__attr']) for ii in range(value[0]['count'])
				]
			else:
				return cls.process_obj(results=results, step=step, obj=value)

		elif type(value) == str and value.startswith('$__'):
			logger.debug(f'Processing value variable: {value}')
			try:
				if value == '$__session':
					return cls.session
				elif value.startswith('$__session.'):
					return extract_attr(scope=cls.session, attr_path=value.replace('session.', '', 1))
				elif value.startswith('$__vars.'):
					return extract_attr(scope=cls.vars, attr_path=value.replace('vars.', '', 1))
				else:
					return extract_attr(scope=results, attr_path=value)  # type: ignore
			except:
				logger.error('Failed to process value. Exiting.')
				exit(1)

		elif callable(value):
			return value(session=cls.session, vars=cls.vars, results=results, step=step)

		# [DOC] Values that don't require processing will be returned as-is
		return value

	@classmethod
	def break_debugger(
		cls, *, scope: Dict[str, Any], call_results: Dict[str, Any]
	) -> None:
		if Config.test_breakpoint:
			logger.debug(
				'Creating a breakpoint to allow you to investigate step failure. Type \'c\' after finishing to continue.'
			)
			logger.debug('All variables are available under \'scope\' dict.')
			if call_results:
				logger.debug('Call test raised exception available under \'call_results\' dict')
			breakpoint()
