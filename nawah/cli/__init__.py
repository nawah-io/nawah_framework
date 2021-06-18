from ._cli import nawah_cli
from ._launch import launch

TESTING_COMPATIBILITY: bool = False


def _set_testing(val):
	global TESTING_COMPATIBILITY

	TESTING_COMPATIBILITY = val
