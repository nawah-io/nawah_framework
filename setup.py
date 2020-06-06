import setuptools

with open('README.md', 'r') as f:
	long_description = f.read()

from nawah import __version__

setuptools.setup(
	name='nawah',
	version=__version__,
	author='Mahmoud Abduljawad',
	author_email='mahmoud@masaar.com',
	description='Nawah framework--Rapid app development framework',
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://github.com/nawah-io/nawah_framework',
	packages=['nawah', 'nawah.packages', 'nawah.packages.core'],
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
)
