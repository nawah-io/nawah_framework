from nawah.classes import (
	Query,
	ATTR,
	InvalidCallArgsException,
	InvalidAttrException,
	ConvertAttrException,
)
from nawah.utils import validate_attr

from typing import Union, Dict, Any, List, Literal, Iterable, cast


async def validate_args(
	*,
	args: Union[Query, Dict[str, Any]],
	args_list_label: str,
	args_list: List[Dict[str, ATTR]],
):
	if not args_list:
		return

	sets_check: List[Dict[str, Literal[True, 'missing', 'invalid', 'convert']]] = []

	for args_set in args_list:
		set_status = True
		set_check = len(sets_check)
		sets_check.append({arg: True for arg in args_set.keys()})

		if args_list_label == 'query':
			args_check: Iterable = args
		elif args_list_label == 'doc':
			args = cast(Dict[str, Any], args)
			args_check = args.keys()

		for arg in args_set.keys():
			if arg not in args_check:
				set_status = False
				sets_check[set_check][arg] = 'missing'
			else:
				try:
					if args_list_label == 'query' and arg[0] != '$':
						for i in range(len(args[arg])):
							if ':' not in arg:
								args[arg][i] = await validate_attr(
									mode='create',
									attr_name=arg,
									attr_type=args_set[arg],
									attr_val=args[arg][i],
								)
							else:
								attr_val = args[arg][i]
								if (arg_oper := arg.split(':')[1]) in ['*', '$eq']:
									if type(args[arg][i]) and arg_oper in args[arg][i].keys():
										attr_val = args[arg][i][arg_oper]
								attr_val = await validate_attr(
									mode='create',
									attr_name=arg,
									attr_type=args_set[arg],
									attr_val=attr_val,
								)
								if arg_oper in ['*', '$eq']:
									args[arg][i] = attr_val
								else:
									args[arg][i] = {arg_oper: attr_val}

					elif args_list_label == 'query' and arg[0] == '$':
						args[arg] = await validate_attr(
							mode='create',
							attr_name=arg,
							attr_type=args_set[arg],
							attr_val=args[arg],
						)
					elif args_list_label == 'doc':
						args[arg] = await validate_attr(
							mode='create',
							attr_name=arg,
							attr_type=args_set[arg],
							attr_val=args[arg],
						)
				except InvalidAttrException:
					set_status = False
					sets_check[set_check][arg] = 'invalid'
				except ConvertAttrException:
					set_status = False
					sets_check[set_check][arg] = 'convert'

		if set_status:
			return

	raise InvalidCallArgsException(sets_check)