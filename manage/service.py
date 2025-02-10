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
from os.path import abspath, expanduser, isdir, isfile
from pathlib import Path
import subprocess

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
			return Error(
				errors.DATA_FIELDS,
				[ [ 'record.%s' % l[0], l[1] ] \
	 				for l in self._portal._validation_failures ]
			)

		# Init possible file errors
		lErrors = []

		# Strip pre/post whitespace
		data.path = data.path.strip()

		# Copy it
		sDir = data.path

		# If we got a tilde
		if '~' in sDir:
			sDir = expanduser(sDir)

		# Turn it into an absolute path
		sDir = abspath(sDir)

		# If it's not a valid directory
		if not isdir(sDir):
			lErrors.append([ 'path', 'not a valid directory' ])

		# Strip pre/post whitespace
		data.output = data.output.strip()

		# Copy it
		sDir = data.output

		# If we got a tilde
		if '~' in sDir:
			sDir = expanduser(sDir)

		# Turn it into an absolute path
		sDir = abspath(sDir)

		# If it's not a valid directory
		if not isdir(sDir):
			lErrors.append([ 'output', 'not a valid directory' ])

		# If we have an 'nvm' argument
		if 'nvm' in data.node and data.node.nvm:

			# Strip pre/post whitespace
			data.node.nvm = data.node.nvm.strip()

			# If we have a value
			if data.node.nvm:

				# Get the list of nvm aliases
				try:
					sOut = subprocess.check_output(
						'/bin/bash -i -c "nvm alias %s"' % data.node.nvm,
						shell = True
					)

					# If we got not nothing
					if not sOut:
						lErrors.append([ 'record.node.nvm', 'invalid alias' ])

				# If there was an error
				except subprocess.CalledProcessError as e:
					print(e)
					lErrors.append([ 'record.node.nvm', str(e.args) ])

			# Else, set it to null
			else:
				data.node.nvm = None

		# Else, set it to null
		else:
			data.node.nvm = None

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
			return Error(
				errors.DATA_FIELDS,
				[ [ 'record.%s' % l[0], l[1] ] \
	 				for l in self._rest._validation_failures ]
			)

		# Init possible file errors
		lErrors = []

		# Strip pre/post whitespace
		data.path = data.path.strip()

		# Copy it
		sDir = data.path

		# If we got a tilde
		if '~' in sDir:
			sDir = expanduser(sDir)

		# Turn it into an absolute path
		sDir = abspath(sDir)

		# If it's not a valid directory
		if not isdir(sDir):
			lErrors.append([ 'path', 'not a valid directory' ])

		# If we have a 'which' argument
		if 'which' in data.python and data.python.which:

			# Strip pre/post whitespace
			data.python.which = data.python.which.strip()

			# If it's not empty
			if data.python.which:

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

			# Else, set it to null
			else:
				data.python.which = None

		# Else, set it to null
		else:
			data.python.which = None

		# If we have a 'requirements' argument
		if 'requirements' in data.python and data.python.requirements:

			# Strip pre/post whitespace
			data.python.requirements = data.python.requirements.strip()

			# If it's not empty
			if data.python.requirements:

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

			# Else, set it to null
			else:
				data.python.requirements = None

		# Else, set it to null
		else:
			data.python.requirements = None

		# Try to call a subprocess
		try:

			# Fetch the list of supervisor programs and store just the name
			lOut = subprocess.check_output(
				'supervisorctl avail',
				shell = True).decode().split('\n')

			# Init the list of programs
			lPrograms = []

			# Go though each line, get the program, and add it to the list
			for s in lOut:
				if s != '':
					l = s.split(' ', 1)
					lPrograms.append(l[0])

		# If there's any issue with the process
		except subprocess.CalledProcessError as e:
			lErrors.append([ 'record.services', str(e.args) ])

		# Step through the services
		for k, d in data.services.items():

			# If we have a 'supervisor' argument
			if 'supervisor' in d and d.supervisor:

				# Strip pre/post whitespace
				d.supervisor = d.supervisor.strip()

				# If we have a value
				if d.supervisor:
					pass

				# Else, set it to null
				else:
					d.supervisor = None

			# Else, set it to null
			else:
				d.supervisor = None

			# If we have a specific value
			if d.supervisor:
				if d.supervisor not in lPrograms:
					lErrors.append(
						[ 'record.services.%s.supervisor' % k,
	   						'not a valid supervisor program' ]
					)

			# Else, check the main name
			else:
				if k not in lPrograms:
					lErrors.append(
						[ 'record.services.%s' % k,
					 		'not a valid supervisor program' ]
					)

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