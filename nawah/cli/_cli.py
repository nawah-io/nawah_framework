from nawah import __version__

from typing import Dict, Literal, Any, Optional

import argparse, os, logging, datetime, sys, subprocess, asyncio, traceback, shutil, urllib.request, re, tarfile, string, random, tempfile, pkgutil, glob


def nawah_cli():
	from ._logging import logger
	from ._create import create
	from ._launch import launch
	from ._packages import packages_audit, packages_install, _packages_add, _packages_rm
	from ._generate import generate_ref, generate_models

	if sys.version_info.major != 3 or sys.version_info.minor < 8:
		print('Nawah framework CLI can only run with Python >= 3.8. Exiting.')
		exit(1)

	parser = argparse.ArgumentParser()
	parser.add_argument(
		'--version',
		help='Show Nawah framework version and exit',
		action='version',
		version=f'Nawah framework v{__version__}',
	)

	subparsers = parser.add_subparsers(
		title='Command', description='Nawah framework CLI command to run', dest='command'
	)

	parser_create = subparsers.add_parser('create', help='Create new Nawah app')
	parser_create.set_defaults(func=create)
	parser_create.add_argument('app_name', type=str, help='Name of the app to create')
	parser_create.add_argument(
		'app_path',
		type=str,
		nargs='?',
		help='Path to create new Nawah app. [default .]',
		default='.',
	)
	parser_create.add_argument(
		'--default-config',
		help='Create new Nawah app with default config',
		action='store_true',
	)

	parser_launch = subparsers.add_parser('launch', help='Launch Nawah app')
	parser_launch.set_defaults(func=launch)
	parser_launch.add_argument('--env', help='Choose specific env')
	parser_launch.add_argument('--debug', help='Enable debug mode', action='store_true')
	parser_launch.add_argument(
		'--log',
		help='Enable debug mode and log all debug messages to log file',
		action='store_true',
	)
	parser_launch.add_argument('-p', '--port', help='Set custom port [default 8081]')
	parser_launch.add_argument(
		'--force-admin-check',
		help='Force ADMIN doc checked and updated, if ADMIN doc is changed',
		action='store_true',
	)

	parser_packages = subparsers.add_parser('packages', help='Manage Nawah app packages')
	parser_packages.set_defaults(func=lambda _: None)
	packages_subparser = parser_packages.add_subparsers(
		title='Packages Command',
		description='Packages command to run',
		dest='packages_command',
	)

	parser_packages_install = packages_subparser.add_parser(
		'install', help='Install Nawah app packages'
	)
	parser_packages_install.set_defaults(func=packages_install)

	parser_packages_add = packages_subparser.add_parser(
		'add', help='Add package to Nawah app'
	)
	parser_packages_add.set_defaults(
		func=lambda args: _packages_add(
			package_name=args.package_name,
			source=args.source,
			version=args.version,
			auth=args.auth,
		)
	)
	parser_packages_add.add_argument(
		'package_name', help='Package name to add to Nawah app'
	)
	parser_packages_add.add_argument(
		'--source',
		help='Package source [default https://gitlab.com/api/v4/projects/24381550/packages/pypi/simple]',
		default='https://gitlab.com/api/v4/projects/24381550/packages/pypi/simple',
	)
	parser_packages_add.add_argument(
		'--version',
		help='Package version (repo tag name) to install [default latest]',
		default='latest',
	)
	parser_packages_add.add_argument(
		'--auth',
		help='String representing colon-separated username and password combination to authorise the source',
	)

	parser_packages_rm = packages_subparser.add_parser(
		'rm', help='Remove package from Nawah app'
	)
	parser_packages_rm.set_defaults(
		func=lambda args: _packages_rm(package_name=args.package_name, confirm=not args.y)
	)
	parser_packages_rm.add_argument(
		'package_name', help='Package name to remove from Nawah app'
	)
	parser_packages_rm.add_argument('-y', help='Skip confirmation', action='store_true')

	parser_packages_audit = packages_subparser.add_parser(
		'audit', help='Audit packages in Nawah app'
	)
	parser_packages_audit.set_defaults(func=packages_audit)

	parser_ref = subparsers.add_parser('generate_ref', help='Generate Nawah app reference')
	parser_ref.set_defaults(func=generate_ref)
	parser_ref.add_argument('--debug', help='Enable debug mode', action='store_true')

	parser_ref = subparsers.add_parser('generate_models', help='Generate Nawah app models')
	parser_ref.set_defaults(func=generate_models)
	parser_ref.add_argument('format', help='Format of models', choices=['js', 'ts'])
	parser_ref.add_argument('--debug', help='Enable debug mode', action='store_true')

	args = parser.parse_args()

	if args.command:
		if args.command == 'packages' and not args.packages_command:
			parser_packages.print_help()
		else:
			args.func(args)
	else:
		parser.print_help()
