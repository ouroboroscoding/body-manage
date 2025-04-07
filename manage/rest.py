# coding=utf8
""" Manage REST

Handles starting the REST server using the Manage service
"""

__author__		= "Chris Nasr"
__version__		= "1.0.0"
__copyright__	= "Ouroboros Coding Inc."
__email__		= "chris@ouroboroscoding.com"
__created__		= "2025-02-08"

# Ouroboros imports
from config import config
import em

# Python imports
from pprint import pformat

# Module imports
from manage.service import Manage

def errors(error):

	# If we don't send out errors
	if not config.manage.send_error_emails(False):
		return True

	# Generate a list of the individual parts of the error
	lErrors = [
		'ERROR MESSAGE\n\n%s\n' % error['traceback'],
		'REQUEST\n\n%s %s:%s\n' % (
			error['method'], error['service'], error['path']
		)
	]
	if 'data' in error and error['data']:
		lErrors.append('DATA\n\n%s\n' % pformat(error['data']))
	if 'session' in error and error['session']:
		lErrors.append('SESSION\n\n%s\n' % pformat({
			k:error['session'][k] for k in error['session']
		}))
	if 'environment' in error and error['environment']:
		lErrors.append('ENVIRONMENT\n\n%s\n' % pformat(error['environment']))

	# Send the email
	return em.error('\n'.join(lErrors))

def run():
	"""Run

	Starts the http REST server

	Returns:
		None
	"""

	# Init and run the service as REST server
	Manage().rest(
		on_errors = errors
	)