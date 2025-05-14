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
from tools import clone, combine, evaluate

# Python imports
import arrow
from os import scandir
from os.path import abspath, expanduser, isdir, isfile
from pathlib import Path
import subprocess

# Project imports
from .errors import SHELL_ISSUE

class Manage(Service):
	"""Manage Service class

	Service for managing services and portals

	docs-file:
		rest

	docs-body:
		manage
	"""

	@classmethod
	def _real(cls, path: str) -> str:
		"""Real

		Takes a possible relative and user based path into a full absolute path

		Arguments:
			path (str): The path to turn into an absolute path

		Returns:
			str
		"""
		return abspath(
			'~' in path and expanduser(path) or path
		)

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

		# If it's not a valid directory
		if not isdir(self._real(data.path)):
			lErrors.append([ 'record.path', 'not a valid directory' ])

		# If we have a 'build' argument
		if 'build' in data and data.build:

			# Strip pre/post whitespace
			data.build = data.build.strip()

			# If it's not a valid directory
			if not isdir(self._real(data.build)):

				# Check the parent
				if not isdir(Path(self._real(data.build)).parent.resolve()):
					lErrors.append([ 'record.build', 'not a valid directory' ])

		# Strip pre/post whitespace
		data.web_root = data.web_root.strip()

		# If it's not a valid directory
		if not isdir(self._real(data.web_root)):
			lErrors.append([ 'record.web_root', 'not a valid directory' ])

		# If we have a 'backups' argument
		if 'backups' in data and data.backups:

			# Strip pre/post whitespace
			data.backups = data.backups.strip()

			# If it's not a valid directory
			if not isdir(self._real(data.backups)):
				lErrors.append([ 'record.backups', 'not a valid directory' ])

		# If we have an 'nvm' argument
		if 'nvm' in data.node and data.node.nvm:

			# Strip pre/post whitespace
			data.node.nvm = data.node.nvm.strip()

			# If we have a value
			if data.node.nvm:

				# Run NVM
				try:
					sOut = subprocess.check_output(
						'bash -c ". %s && nvm alias %s"' % (
							self._real('~/.nvm/nvm.sh'),
							data.node.nvm
						),
						shell = True,
						stderr = subprocess.STDOUT
					).decode().strip()

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

	def portal_backups_read(self, req: jobject) -> Response:
		"""Portal Backups read

		Returns the list of backups currently on the system

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(
			req.session, { 'name': 'manage_portal_build', 'right': access.READ }
		)

		# Verify minimum data
		try: evaluate(req.data, [ 'name' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If the portal doesn't exist
		if req.data.name not in self._conf.portals:
			return Error(errors.DB_NO_RECORD, [ req.data.name, 'portal' ])

		# If the portal doesn't allow backups
		if 'backups' not in self._conf.portals[req.data.name] or \
			not self._conf.portals[req.data.name].backups:
			return Error(errors.RIGHTS, 'portal does not allow backups')

		# Get all the folders currently in the backups folder, sort them by
		#	newest first
		lBackups = [
			f.name \
			for f in scandir(
				self._real(self._conf.portals[req.data.name].backups)
			) \
			if f.is_dir()
		]
		lBackups.sort(reverse = True)

		# Return the backups
		return Response(lBackups)

	def portal_build_create(self, req: jobject) -> Response:
		"""Portal Build create

		Runs the update process for the specific portal

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(
			req.session,
			{ 'name': 'manage_portal_build', 'right': access.CREATE }
		)

		# Verify minimum data
		try: evaluate(req.data, [ 'name' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If the portal doesn't exist
		if req.data.name not in self._conf.portals:
			return Error(errors.DB_NO_RECORD, [ req.data.name, 'portal' ])

		# Simplify life
		dPortal = self._conf.portals[req.data.name]

		# Change directory and git fetch
		lCommands = [
			'cd %s' % self._real(dPortal.path),
			'%s fetch' % self._git
		]

		# If we have a clear flag
		if 'clear' in req.data and req.data['clear']:
			lCommands.append('%s checkout .' % self._git)

		# If we have a checkout branch, add the checkout part
		if 'checkout' in req.data and req.data.checkout:
			lCommands.append('%s checkout %s' % ( self._git, req.data.checkout ))

		# git pull
		lCommands.append(dPortal.git.submodules and \
			'%s pull --recurse-submodules' % self._git or \
			'%s pull'
		)

		# If we have an nvm alias, add the nvm part
		if dPortal.node.nvm:
			lCommands.extend([
				'. %s' % self._real('~/.nvm/nvm.sh'),
				'nvm alias %s' % dPortal.node.nvm
			])

		# npm install
		lCommands.append(dPortal.node.force_install and \
			'npm install --force' or \
			'npm install'
		)

		# The build command
		lCommands.append('npm run %s' % dPortal.node.script or 'build')

		# If we allow and need a backup
		if 'backups' in dPortal and dPortal.backups and \
			'backup' in req.data and req.data.backup:
			lCommands.append('(mv -v %s %s/%s || true)' % (
				self._real(dPortal.web_root),
				self._real(dPortal.backups),
				arrow.get().format('YYYYMMDDHHmmss')
			))
		else:
			lCommands.append('rm -Rf %s' % self._real(dPortal.web_root))

		# Copy the built files to the web
		lCommands.extend([
			'mkdir -vp %s' % self._real(dPortal.web_root),
			'cp -vr %s/* %s/.' % (
				self._real(('build' in dPortal and \
					dPortal.build or \
					('%s/dist' % dPortal.path)
				)),
				self._real(dPortal.web_root)
		)])

		# Generate the command string
		sCommands = 'bash -c "%s"' % ' && '.join(lCommands)

		# Run the commands
		try:
			sOutput = subprocess.check_output(
				sCommands,
				shell = True,
				stderr = subprocess.STDOUT
			).decode().strip()

		# If there's any errors
		except subprocess.CalledProcessError as e:
			return Error(SHELL_ISSUE, [ sCommands, str(e.args) ])

		# Return the commands output
		return Response({
			'commands': sCommands,
			'output': sOutput
		})

	def portal_build_read(self, req: jobject) -> Response:
		"""Portal Build read

		Fetches info about the repo for the specific portal

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(
			req.session,
			{ 'name': 'manage_portal_build', 'right': access.READ }
		)

		# Verify minimum data
		try: evaluate(req.data, [ 'name' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If the portal doesn't exist
		if req.data.name not in self._conf.portals:
			return Error(errors.DB_NO_RECORD, [ req.data.name, 'portal' ])

		# Simplify life
		dPortal = self._conf.portals[req.data.name]

		# Init return
		dRet = jobject({})

		# Copy the folder
		sDir = dPortal.path

		# If the portal has ~
		if '~' in sDir:
			sDir = expanduser(sDir)

		# Make it an absolute path
		sDir = abspath(sDir)

		# Get the repo up to date
		try:
			subprocess.check_output(
				'cd %s && %s fetch' % (sDir, self._git),
				shell = True
			)
		except subprocess.CalledProcessError as e:
			return Error(SHELL_ISSUE, str(e))

		# Fetch the git status
		try:
			dRet.status = subprocess.check_output('cd %s && %s status' % (
				sDir,
				self._git
			), shell = True).decode().strip()
		except subprocess.CalledProcessError as e:
			return Error(SHELL_ISSUE, str(e))

		# If checkout is allowed
		if dPortal.git.checkout:

			# Fetch the list of branches
			try:
				lBranches = subprocess.check_output(
					'cd %s && %s branch --list' % (
						sDir,
						self._git
					),
					shell = True
				).decode().strip().split('\n')

			except subprocess.CalledProcessError as e:
				return Error(SHELL_ISSUE, str(e))

			# Init return branches
			dRet.branches = []

			# Step through the branches
			for s in lBranches:

				# If the branch is set, store it in the return
				if s[0] == '*':
					dRet.branch = s[2:]

				# Add the branch
				dRet.branches.append(s[2:])

		# Return info
		return Response(dRet)

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
		access.verify(
			req.session, { 'name': 'manage_portal', 'right': access.CREATE }
		)

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
		access.verify(
			req.session, { 'name': 'manage_portal', 'right': access.DELETE }
		)

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

	def portal_restore_create(self, req: jobject) -> Response:
		"""Portal update

		Updates an existing portal entry by name

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(
			req.session, { 'name': 'manage_portal_build', 'right': access.READ }
		)

		# Verify minimum data
		try: evaluate(req.data, [ 'name', 'backup' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If the portal doesn't exist
		if req.data.name not in self._conf.portals:
			return Error(errors.DB_NO_RECORD, [ req.data.name, 'portal' ])

		# If the portal doesn't allow backups
		if not self._conf.portals[req.data.name].backups:
			return Error(errors.RIGHTS, 'portal does not allow backups')

		# If the backup doesn't exist
		if not isdir('%s/%s' % (
			self._real(self._conf.portals[req.data.name].backups),
			req.data.backup
		)):
			return Error(
				errors.DATA_FIELDS, [ [ 'backup', 'folder not found' ] ]
			)

		# Simplify life
		dPortal = self._conf.portals[req.data.name]

		# Init the commands
		lCommands = []

		# If we want to first backup the current version
		if 'backup_current' in req.data and req.data.backup_current:
			lCommands.append('mv -v %s %s/previous' % (
				self._real(dPortal.web_root),
				self._real(dPortal.backups)
			))

		# Else, we will just remove it
		else:
			lCommands.append('rm -vRf %s' % self._real(dPortal.web_root))

		# Copy all the files from the backup to the web root
		lCommands.extend([
			'mkdir -vp %s' % self._real(dPortal.web_root),
			'cp -vr %s/%s/* %s/.' % (
				self._real(dPortal.backups),
				req.data.backup,
				self._real(dPortal.web_root)
			)
		])

		# Generate the command string
		sCommands = ' && '.join(lCommands)

		# Run the commands
		try:
			sOutput = subprocess.check_output(
				sCommands,
				shell = True,
				stderr = subprocess.STDOUT
			).decode().strip()

		# If there's any errors
		except subprocess.CalledProcessError as e:
			return Error(SHELL_ISSUE, [ sCommands, str(e.args) ])

		# Return the commands output
		return Response({
			'commands': sCommands,
			'output': sOutput
		})

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
		access.verify(
			req.session, { 'name': 'manage_portal', 'right': access.UPDATE }
		)

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
		access.verify(
			req.session, { 'name': 'manage_portal', 'right': access.READ }
		)

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

		# If it's not a valid directory
		if not isdir(self._real(data.path)):
			lErrors.append([ 'record.path', 'not a valid directory' ])

		# If we have a 'which' argument
		if 'which' in data.python and data.python.which:

			# Strip pre/post whitespace
			data.python.which = data.python.which.strip()

			# If it's not empty
			if data.python.which:

				# If it's not a valid file
				if not isfile(self._real(data.python.which)):
					lErrors.append([ 'record.python.which', 'not found' ])

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

				# If it's not a valid file
				if not isfile(self._real(data.python.requirements)):
					lErrors.append(
						[ 'record.python.requirements', 'not found' ]
					)

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
				shell = True
			).decode().split('\n')

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

	def reset(self):
		"""Reset

		Called to reset the config and connections

		Returns:
			Manage
		"""

		# Generate the definitions path
		sDefine = '%s/define' % Path(__file__).parent.resolve()

		# Load the rest and portal Parents
		self._rest = Parent.from_file('%s/rest.json' % sDefine)
		self._portal = Parent.from_file('%s/portal.json' % sDefine)

		# Store the name of the file
		self._path = config.manage.config('../.data/manage.json')
		self._git = config.manage.git('/usr/bin/git')

		# Fetch the configuration and store it as a jobject
		self._conf = jobject( jsonb.load( self._path ) )

		# Return self for chaining
		return self

	def rest_build_read(self, req: jobject) -> Response:
		"""Portal Build read

		Fetches info about the repo for the specific rest

		Arguments:
			req (jobject): The request details, which can include 'data', \
						'environment', and 'session'

		Returns:
			Response
		"""

		# Verify the permissions
		access.verify(
			req.session, { 'name': 'manage_rest_build', 'right': access.READ }
		)

		# Verify minimum data
		try: evaluate(req.data, [ 'name' ])
		except ValueError as e:
			return Error(
				errors.DATA_FIELDS, [ [ f, 'missing' ] for f in e.args ]
			)

		# If the rest doesn't exist
		if req.data.name not in self._conf.rest:
			return Error(errors.DB_NO_RECORD, [ req.data.name, 'rest' ])

		# Simplify life
		dPortal = self._conf.rest[req.data.name]

		# Init return
		dRet = jobject({})

		# Copy the folder
		sDir = dPortal.path

		# If the rest has ~
		if '~' in sDir:
			sDir = expanduser(sDir)

		# Make it an absolute path
		sDir = abspath(sDir)

		# Get the repo up to date
		try:
			subprocess.check_output(
				'cd %s && %s fetch --all' % (sDir, self._git),
				shell = True
			)
		except subprocess.CalledProcessError as e:
			return Error(SHELL_ISSUE, str(e))

		# Fetch the git status
		try:
			dRet.status = subprocess.check_output('cd %s && %s status' % (
				sDir,
				self._git
			), shell = True).decode().strip()
		except subprocess.CalledProcessError as e:
			return Error(SHELL_ISSUE, str(e))

		# If checkout is allowed
		if dPortal.git.checkout:

			# Fetch the list of branches
			try:
				lBranches = subprocess.check_output(
					'cd %s && %s branch -r' % (
						sDir,
						self._git
					),
					shell = True
				).decode().strip().split('\n')

			except subprocess.CalledProcessError as e:
				return Error(SHELL_ISSUE, str(e))

			# Init return branches
			dRet.branches = []

			# Step through the branches
			for s in lBranches:

				# If the branch is set, store it in the return
				if s[0] == '*':
					dRet.branch = s[2:]

				# Add the branch
				dRet.branches.append(s[2:])

		# Return info
		return Response(dRet)

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
		access.verify(
			req.session, { 'name': 'manage_rest', 'right': access.CREATE }
		)

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
		access.verify(
			req.session, { 'name': 'manage_rest', 'right': access.DELETE }
		)

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
		access.verify(
			req.session, { 'name': 'manage_rest', 'right': access.READ }
		)

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
		access.verify(
			req.session, { 'name': 'manage_rest', 'right': access.UPDATE }
		)

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

		# If we specifically changed services
		if 'services' in req.data.record:
			dRest['services'] = req.data.record.services

		# If any services are None, delete them
		for s in list(dRest.services.keys()):
			if dRest.services[s] == None:
				del dRest.services[s]

		# Call and return the validation methods
		return self._rest_validation(req.data.name, dRest)