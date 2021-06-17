from nawah.config import Config

import argparse

from ._launch import launch


def generate_ref(args: argparse.Namespace):
	# [DOC] Update Config with Nawah framework CLI args
	from nawah.config import Config

	Config.generate_ref = True
	launch(args=args, custom_launch='generate_ref')


def generate_models(args: argparse.Namespace):
	# [DOC] Update Config with Nawah framework CLI args
	from nawah.config import Config

	Config.generate_models = True
	launch(args=args, custom_launch='generate_models')
