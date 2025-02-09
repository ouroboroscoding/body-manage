# coding=utf8
""" Manage

Handles fetching, restarting, and rebooting services
"""

__author__		= "Chris Nasr"
__version__		= "1.0.0"
__copyright__	= "Ouroboros Coding Inc."
__email__		= "chris@ouroboroscoding.com"
__created__		= "2025-02-08"

# Python imports
from os.path import abspath, expanduser
from pathlib import Path
from sys import argv, exit, stderr

# Module imports
from . import install, rest

def cli():
	"""CLI

	Called from the command line to run from the current directory

	Returns:
		uint
	"""

	# If we have no arguments
	if len(argv) == 1:

		# Run the REST server
		return rest.run()

	# Else, if we have one argument
	elif len(argv) == 2:

		# If we are installing
		if argv[1] == 'install':
			return install.install()

		# Else, if we are explicitly stating the rest service
		elif argv[1] == 'rest':
			return rest.run()

	# Else, arguments are wrong, print and return an error
	print('Invalid arguments', file=stderr)
	return 1

# Only run if called directly
if __name__ == '__main__':
	exit(cli())