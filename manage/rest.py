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
from body import register_services, REST
from config import config
import em

# Python imports
from pprint import pformat

# Module imports
from .service import Manage

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

	# Init the service
	oManage = Manage()

	# Register the services
	oRest = register_services({ 'manage': oManage })

	# Get config
	dManage = oRest['manage']

	# Create the REST server using the Client instance
	oServer = REST(
		name = 'manage',
		instance = oManage,
		cors = config.body.rest.allowed('manage.local'),
		on_errors = errors,
		verbose = config.manage.verbose(False)
	)

	# Run the REST server
	oServer.run(
		host = dManage['host'],
		port = dManage['port'],
		workers = dManage['workers'],
		timeout = 'timeout' in dManage and \
			dManage['timeout'] or 30
	)