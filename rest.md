# Manage
Service for managing services and portals

- [Portal Backups read](#portal-backups-read)
- [Portal Build create](#portal-build-create)
- [Portal Build read](#portal-build-read)
- [Portal create](#portal-create)
- [Portal delete](#portal-delete)
- [Portal update](#portal-update)
- [Portal update](#portal-update)
- [Portals read](#portals-read)
- [Portal Build read](#portal-build-read)
- [REST create](#rest-create)
- [Portal delete](#portal-delete)
- [REST read](#rest-read)
- [REST update](#rest-update)

## Portal Backups read
Returns the list of backups currently on the system

Using @ouroboros/manage
```javascript
manage.read(
	'portal/backups' 
).then(data => {}, error => {});
```

## Portal Build create
Runs the update process for the specific portal

Using @ouroboros/manage
```javascript
manage.create(
	'portal/build' 
).then(data => {}, error => {});
```

## Portal Build read
Fetches info about the repo for the specific portal

Using @ouroboros/manage
```javascript
manage.read(
	'portal/build' 
).then(data => {}, error => {});
```

## Portal create
Creates a new portal and adds it to the config

Using @ouroboros/manage
```javascript
manage.create(
	'portal' 
).then(data => {}, error => {});
```

## Portal delete
Deletes a specific portal by name

Using @ouroboros/manage
```javascript
manage.delete(
	'portal' 
).then(data => {}, error => {});
```

## Portal update
Updates an existing portal entry by name

Using @ouroboros/manage
```javascript
manage.create(
	'portal/restore' 
).then(data => {}, error => {});
```

## Portal update
Updates an existing portal entry by name

Using @ouroboros/manage
```javascript
manage.update(
	'portal' 
).then(data => {}, error => {});
```

## Portals read
Returns all the current portals in the system

Using @ouroboros/manage
```javascript
manage.read(
	'portals' 
).then(data => {}, error => {});
```

## Portal Build read
Fetches info about the repo for the specific rest

Using @ouroboros/manage
```javascript
manage.read(
	'rest/build' 
).then(data => {}, error => {});
```

## REST create
Creates a new REST entry and adds it to the config

Using @ouroboros/manage
```javascript
manage.create(
	'rest' 
).then(data => {}, error => {});
```

## Portal delete
Deletes a specific REST entry by name

Using @ouroboros/manage
```javascript
manage.delete(
	'rest' 
).then(data => {}, error => {});
```

## REST read
Returns all the current REST entries

Using @ouroboros/manage
```javascript
manage.read(
	'rest' 
).then(data => {}, error => {});
```

## REST update
Updates an existing rest entry by name

Using @ouroboros/manage
```javascript
manage.update(
	'rest' 
).then(data => {}, error => {});
```
