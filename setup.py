from nawah import __version__

from distutils.command.install import install

import setuptools


class version(install):
	def run(self):
		print(__version__)


class api_level(install):
	def run(self):
		print('.'.join(__version__.split('.')[:2]))


class generate_stubs(install):
	def run(self):
		from mypy.stubgen import main as stubgen
		import sys, tarfile

		# [DOC] Manipulate sys.argv to let mypy.stubgen.main process it correctly
		sys.argv = [None, 'nawah']
		stubgen()

		# [DOC] Archive stubs as subs.tar.gz
		with tarfile.open('out/nawah/stubs.tar.gz', "w:gz") as tar:
			tar.add('out/nawah', arcname='.')
			print('Stubs archive \'stubs.tar.gz\' created successfully.')


with open('README.md', 'r') as f:
	long_description = f.read()

with open('./requirements.txt', 'r') as f:
	requirements = f.readlines()

with open('./dev_requirements.txt', 'r') as f:
	dev_requirements = f.readlines()

setuptools.setup(
	name='nawah',
	version=__version__,
	author='Mahmoud Abduljawad',
	author_email='mahmoud@masaar.com',
	description='Nawah framework--Rapid app development framework',
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://github.com/nawah-io/nawah_framework',
	package_data={
		'nawah': ['py.typed'],
		'nawah.classes': ['py.typed'],
		'nawah.data': ['py.typed'],
		'nawah.utils': ['py.typed'],
		'nawah.packages': ['py.typed'],
		'nawah.packages.core': ['py.typed'],
	},
	packages=[
		'nawah',
		'nawah.classes',
		'nawah.data',
		'nawah.utils',
		'nawah.packages',
		'nawah.packages.core',
	],
	project_urls={
		'Docs: Github': 'https://github.com/nawah-io/nawah_docs',
		'GitHub: issues': 'https://github.com/nawah-io/nawah_framework/issues',
		'GitHub: repo': 'https://github.com/nawah-io/nawah_framework',
	},
	classifiers=[
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.8',
		'Development Status :: 5 - Production/Stable',
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Operating System :: OS Independent',
		'Topic :: Internet :: WWW/HTTP',
		'Framework :: AsyncIO',
	],
	python_requires='>=3.8',
	install_requires=requirements,
	extras_require={'dev': dev_requirements},
	cmdclass={
		'generate_stubs': generate_stubs,
		'version': version,
		'api_level': api_level,
	},
	zip_safe=False,
)
