# coding=utf8
""" Install

Method to install the necessary manage data
"""

__author__		= "Chris Nasr"
__copyright__	= "Ouroboros Coding Inc."
__version__		= "1.0.0"
__email__		= "chris@ouroboroscoding.com"
__created__		= "2025-01-08"

# Ouroboros imports
from config import config
import jsonb

# Python imports
from os.path import isfile

def install():
	"""Install

	Installs the default records file for the service

	Returns:
		int
	"""

	# Get the path to the file
	sFile = config.manage.config('./manage.json')

	# If the file already exists
	if isfile(sFile):

		# Loop until we have a valid answer
		while True:

			# Print a warning
			print('File "%s" already exists' % sFile)
			sIndex = input('Do you want to [q]uit, or [r]eplace the file: ')

			# If it's 'q'
			if sIndex == 'q':
				return 1

			# Else, if it's 'r'
			elif sIndex == 'r':
				break

	# Store the base config files using the path
	with open(sFile, 'w') as oF:
		oF.write(jsonb.encode({
			'rest': {},
			'portals': {}
		}))

	# Return OK
	return 0