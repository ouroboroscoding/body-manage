from setuptools import setup

with open('README.md', 'r') as oF:
	long_description=oF.read()

setup(
	name='body_manage',
	version='1.0.4',
	description='Manage contains a service to manage the services themselves',
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://ouroboroscoding.com/body/body-manage',
	project_urls={
		'Documentation': 'https://ouroboroscoding.com/body/body-manage',
		'Source': 'https://github.com/ouroboroscoding/body-manage',
		'Tracker': 'https://github.com/ouroboroscoding/body-manage/issues'
	},
	keywords=[ 'rest', 'microservices', 'body', 'body-oc' ],
	author='Chris Nasr - Ouroboros Coding Inc.',
	author_email='chris@ouroboroscoding.com',
	license='Custom',
	packages=[ 'manage' ],
	package_data={ 'manage': [
		'define/*.json'
	] },
	python_requires='>=3.10',
	install_requires=[
		'arrow>=1.3.0,<1.4',
		'brain2_oc>=2.3.1,<2.4',
		'config-oc>=1.1.0,<1.2',
		'define-oc>=1.0.5,<1.1',
		'email-smtp>=1.0.1,<1.1',
		'jsonb>=1.0.0,<1.1'
	],
	entry_points={
		'console_scripts': [ 'manage=manage.__main__:cli' ]
	},
	zip_safe=True
)