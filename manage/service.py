# coding=utf8
""" Manage Service

Handles updating and managing services and portals
"""

__author__		= "Chris Nasr"
__copyright__	= "Ouroboros Coding Inc."
__version__		= "1.0.0"
__email__		= "chris@ouroboroscoding.com"
__created__		= "2025-02-08"

# Limit exports
__all__ = [ 'errors', 'Manage' ]

# Ouroboros imports
from body import Error, errors, Response, Service
from brain.helpers import access
from config import config
from define import Parent
from jobject import jobject
import jsonb
from tools import clone, combine, evaluate, without

# Python imports
from pathlib import Path
from os.path import abspath, expanduser, isfile

class Manage(Service):
	"""Manage Service class

	Service for managing services and portals
	"""

	def __init__(self):
		"""Constructor

		Initialises the instance

		Returns:
			Manage
		"""

		# Load the definitions
		sDefine = '%s/define' % Path(__file__).parent.resolve()
		self._rest = Parent.from_file('%s/rest.json' % sDefine)
		self._portal = Parent.from_file('%s/portal.json' % sDefine)

		# Init the config
		self.reset()

	def _portal_validation(self, name: str, data: dict) -> Response:
		"""Portal Validation

		Shared code between create and update

		Arguments:
			name (str): The name of the entry
			data (dict): The new / updated data

		Returns:
			Response
		"""

		# Validate the data
		if not self._portal.valid(data):
			return Error(errors.DATA_FIELDS, self._portal._validation_failures)

		# Init possible file errors
		lErrors = []

		# Do we have a git section?
		if 'git' in data:

			# Do we have a checkout flag, is it false, then delete it
			if 'checkout' in data.git and \
				data.git.checkout == False:
				del data.git.checkout

			# Do we have a submodule flag, is it false, then delete it
			if 'submodule' in data.git and \
				data.git.submodule == False:
				del data.git.submodule

			# If we don't have any flags, delete git
			if not data.git:
				del data.git

		# Do we have a node section
		if 'node' in data:

			# Do we have a force_install flag, is it false, then delete it
			if 'force_install' in data.git and \
				data.git.force_install == False:
				del data.git.force_install

			# Do we have a nvm string
			if 'nvm' in data.node:

				# If it's an empty string, then delete it
				if not data.node.nvm or data.node.nvm.strip() == '':
					del data.node.nvm

				# Else, we got something
				else:

					# If it's not a valid alias
					# TODO check alias
					pass

			# If we don't have any flags, delete node
			if not data.node:
				del data.node

		# If there's errors
		if lErrors:
			return Error(errors.DATA_FIELDS, lErrors)

		# Copy the config
		dConf = clone(self._conf)

		# Add the new entry
		dConf.portals[name] = data

		# Store the conf
		try:
			jsonb.store(dConf, self._path, 2)
		except Exception as e:
			return Error(errors.DB_CREATE_FAILED, str(e))

		# Update the local variables
		self._conf = dConf

		# Return OK
		return Response(True)

	def portal_create(self, req: jobject) -> Response:
		"""Portal create

		Creates a new portal and adds it to the config

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(req.session, 'manage_portal', access.CREATE)

		# Verify minimum data
		try: evaluate(req.data, [ 'name', 'record' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If there's another portal with that name
		if req.data.name in self._conf.portals:
			return Error(errors.DB_DUPLICATE, [ req.data.name, 'portals' ])

		# Call and return the validation methods
		return self._portal_validation(req.data.name, req.data.record)

	def portal_delete(self, req: jobject) -> Response:
		"""Portal delete

		Deletes a specific portal by name

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(req.session, 'manage_portal', access.DELETE)

		# Verify minimum data
		try: evaluate(req.data, [ 'name' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If the portal doesn't exist
		if req.data.name not in self._conf.portals:
			return Error(errors.DB_NO_RECORD, [ req.data.name, 'portal' ])

		# Copy the config
		dConf = clone(self._conf)

		# Delete the portal
		del dConf.portals[req.data.name]

		# Store the conf
		try:
			jsonb.store(dConf, self._path, 2)
		except Exception as e:
			return Error(errors.DB_CREATE_FAILED, str(e))

		# Update the local variables
		self._conf = dConf

		# Return OK
		return Response(True)

	def portal_update(self, req: jobject) -> Response:
		"""Portal update

		Updates an existing portal entry by name

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(req.session, 'manage_portal', access.UPDATE)

		# Verify minimum data
		try: evaluate(req.data, [ 'name', 'record' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If the portal doesn't exist
		if req.data.name not in self._conf.portals:
			return Error(errors.DB_NO_RECORD, [ req.data.name, 'portal' ])

		# Make a new record from the old and new data
		dRest = combine(self._conf.portals[req.data.name], req.data.record)

		# Call and return the validation methods
		return self._portal_validation(req.data.name, dRest)

	def portals_read(self, req: jobject) -> Response:
		"""Portals read

		Returns all the current portals in the system

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(req.session, 'manage_portal', access.READ)

		# Return the services
		return Response(self._conf.portals)

	def _rest_validation(self, name: str, data: dict) -> Response:
		"""Rest Validation

		Shared code between create and update

		Arguments:
			name (str): The name of the entry
			data (dict): The new / updated data

		Returns:
			Response
		"""

		# Validate the data
		if not self._rest.valid(data):
			return Error(errors.DATA_FIELDS, self._rest._validation_failures)

		# Init possible file errors
		lErrors = []

		# Do we have a git section?
		if 'git' in data:

			# Do we have a checkout flag, is it false, then delete it
			if 'checkout' in data.git and \
				data.git.checkout == False:
				del data.git.checkout

			# Do we have a submodule flag, is it false, then delete it
			if 'submodule' in data.git and \
				data.git.submodule == False:
				del data.git.submodule

			# If we don't have any flags, delete git
			if not data.git:
				del data.git

		# Do we have a python section
		if 'python' in data:

			# Do we have a which string
			if 'which' in data.python:

				# Is it an empty string, then delete it
				if not data.python.which or data.python.which.strip() == '':
					del data.python.which

				# Else, we got something
				else:

					# Copy it
					sFile = data.python.which

					# If we got a tilde
					if '~' in sFile:
						sFile = expanduser(sFile)

					# Turn it into an absolute path
					sFile = abspath(sFile)

					# If it's not a valid file
					if not isfile(sFile):
						lErrors.append([ 'python.which', 'not found' ])

			# Do we have a requirements string
			if 'requirements' in data.python:

				# If it's an empty string, then delete it
				if not data.python.requirements or \
					data.python.requirements.strip() == '':
					del data.python.requirements

				# Else, we got something
				else:

					# Copy it
					sFile = data.python.requirements

					# If we got a tilde
					if '~' in sFile:
						sFile = expanduser(sFile)

					# Turn it into an absolute path
					sFile = abspath(sFile)

					# If it's not a valid file
					if not isfile(sFile):
						lErrors.append([ 'python.requirements', 'not found' ])

			# If we don't have any flags, delete python
			if not data.python:
				del data.python

		# Step through the services
		for d in data.services.values():

			# If there's a supervisor string, and it's empty, then delete it
			if 'supervisor' in d and \
				d.supervisor.strip() == '':
				del d.supervisor

		# If there's errors
		if lErrors:
			return Error(errors.DATA_FIELDS, lErrors)

		# Copy the config
		dConf = clone(self._conf)

		# Add the new entry
		dConf.rest[name] = data

		# Store the conf
		try:
			jsonb.store(dConf, self._path, 2)
		except Exception as e:
			return Error(errors.DB_CREATE_FAILED, str(e))

		# Update the local variables
		self._conf = dConf

		# Return OK
		return Response(True)

	def rest_create(self, req: jobject) -> Response:
		"""REST create

		Creates a new REST entry and adds it to the config

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(req.session, 'manage_rest', access.CREATE)

		# Verify minimum data
		try: evaluate(req.data, [ 'name', 'record' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If there's another rest with that name
		if req.data.name in self._conf.rest:
			return Error(errors.DB_DUPLICATE, [ req.data.name, 'rest' ])

		# Call and return the validation methods
		return self._rest_validation(req.data.name, req.data.record)

	def rest_delete(self, req: jobject) -> Response:
		"""Portal delete

		Deletes a specific REST entry by name

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(req.session, 'manage_rest', access.DELETE)

		# Verify minimum data
		try: evaluate(req.data, [ 'name' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If the rest doesn't exist
		if req.data.name not in self._conf.rest:
			return Error(errors.DB_NO_RECORD, [ req.data.name, 'rest' ])

		# Copy the config
		dConf = clone(self._conf)

		# Delete the rest
		del dConf.rest[req.data.name]

		# Store the conf
		try:
			jsonb.store(dConf, self._path, 2)
		except Exception as e:
			return Error(errors.DB_CREATE_FAILED, str(e))

		# Update the local variables
		self._conf = dConf

		# Return OK
		return Response(True)

	def rest_read(self, req: jobject) -> Response:
		"""REST read

		Returns all the current REST entries

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(req.session, 'manage_rest', access.READ)

		# Return the services
		return Response(self._conf.rest)

	def rest_update(self, req: jobject) -> Response:
		"""REST update

		Updates an existing rest entry by name

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(req.session, 'manage_rest', access.UPDATE)

		# Verify minimum data
		try: evaluate(req.data, [ 'name', 'record' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If the rest doesn't exist
		if req.data.name not in self._conf.rest:
			return Error(errors.DB_NO_RECORD, [ req.data.name, 'rest' ])

		# Make a new record from the old and new data
		dRest = combine(self._conf.rest[req.data.name], req.data.record)

		# If any services are None, delete them
		for s in list(dRest.services.keys()):
			if dRest.services[s] == None:
				del dRest.services[s]

		# Call and return the validation methods
		return self._rest_validation(req.data.name, dRest)

	def reset(self):
		"""Reset

		Called to reset the config and connections

		Returns:
			Manage
		"""

		# Store the name of the file
		self._path = config.manage.config('./manage.json')

		# Fetch the configuration and store it as a jobject
		self._conf = jobject( jsonb.load( self._path ) )

		# Return self for chaining
		return self