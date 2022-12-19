# Redasher-ja

This project was forked from [Redasher](https://github.com/Som-Energia/redasher) for Japanese-titled redash objects.

This tool manages Redash objects as files,
enabling version control and having development environments.

The purpose of this tool is to serialize [Redash](http://redash.io) objects
(dashboards, queries, visualizations...)
into the filesystem so that they can be maintained using tools like Git.
You might use that to keep track of the changes with tools like git, or
you can even modify those objects with a text editor and update your instance.
By tracking a second Redash instance you can use this tool to syncronize objects among them.
This is useful, for example, to make and test changes in a development  environment
and eventually apply those changes into a production one.


## Usage

Lets start by defining our production server, by setting up the base url
and the API key of the user we will use to interact.

```bash
redasher setup prod http://redash.mycompany.com:8012 a2xcvvr23werwcdvhtsdfa23424df
```

A configuration file in `.redasher-ja/config.yaml` will be created.

Then lets download all the objects from `prod`

```bash
redasher checkout prod
```

This will create the following directory structure in the current directory:

```
maps/
maps/prod.yaml # mappings from local files to object ids in `prod` server
dashboards/<name>/metadata.yaml # dashboards metadata
dashboards/<name>/widgets/<name>.yaml # dashboard widgets
queries/<name>/query.sql # The query string file
queries/<name>/metadata.yaml # The rest of the metadata
queries/<name>/visualizations/<name>.yaml # query visualizatons
```

You can put those files under the wing of a version control system like git,
and keep track of your object changes in redash
by running checkout and committing resulting files at any step.

You can also modify the content of those files
and then upload them back to the server:

```bash
redasher upload prod dashboard/my-dashboard
```

Another common workflow is working with an internal server
to develop without disturbing production users and
synchronize when you are done with the changes.

For that you must define a new server:

```bash
redasher setup dev http://localhost:8080 sdfa23424dfa2xcvvr23werwcdvht
```

Redash datasource objects are considered readonly.
If you want to synchronize two servers, first you must
manually bind the datasource file object
checked out from the first server, to the
id of an equivalent datasource you created in the second server.

```bash
redasher bind dev datasource/my-database.yaml 3
```

Then you can upload the objects to create them.

```bash
redasher upload dev dashboard/my-dashboard
```

From now on, succesive file uploads to the new server
will be updates on the same objects.


## Understanding maps/

The directory `maps` contains a file for each server.
Such files relate server object id's to file objects.
Such a relation is set the first time you checkout an object from a server,
or the first time you upload an object into a server and thus creating a new object.

When you upload a file object to a server.
If the file object already has a bound id on the server,
the object is updated.
Otherwise a new object is created.

Likewise, whenever you checkout an object from a server,
if the map exists, the content will be dump in the same file.
If not, a proper file name will be generated based on the slug
of the current object name.
If the name already exists a serial number is added.

You can also set a server mapping by hand with the `bind` subcommand
like in the previous example with the datasource.



## Design

### Decision Log

- Sluggified names are used as object file names since they are more easily spotted than a hash
- Sluggified names are keept even if the name of the object changes later
- Non composition relations are mapped with an attribute refering the object path names instead of ids.
  - Numeric id's from server are instance dependant
  - A common numeric serialization id would solve that but it would be harder to search and replace
- Composition relations (dashboard -> widgets, query -> visualizations) are
  mapped as directory hierarchy. This eases copying objects as a whole.
- Ids in each redash instance are different so "instance id" to "object file" maps should be tracked per instance
- While production object mapping should be part of a shared repository,
  private development servers might have sense for a single developer.
  So, file-id maps should be in different files for each file so you can
  decide which servers are shared in a repository.
- Permanent mapping from id and a file object should be stablished:
  - The first time you download a given server object with no previous bound in that server
  - The first time you upload a file object to a given server with no previous bound in that server
- Successive uploads and downloads should keep that binding
  - Uploading a file object to a server where it has a bound, should update the object instead of creating it
  - Downloading an object from a server having already a bound to a file object, overwrites the same file object
- Data sources are mapped as well but not updated on upload, since they might point to different database configurations depending on the instance.
  - Thus, before uploading objects refering to a datasource into a new instance,
    it has to be created in the instance and bound using the bind command before uploading.
- Server configuration is not to be committed, and apikey should be kept private,
  thus it has been separated from the server id map into a user configuration file.
- Users might be different in production and testing, a dashboard could
  be created using a different user. 
  Thus, creation and modification users are not kept
- Object creation and modification dates are not to be kept, or do they? (they might be used to compare update times and detecting overwritten changes)
- Cascading uploads
  - Uploading a dashboard uploads all its widgets
  - Uploading a widget uploads its dashboard and its visualization
  - Uploading a visualization uploads its query
  - Uploading a query uploads its datasource, its visualizations and any param query

### TODO

- Partial checkouts
- Alerts and destinations
- Groups
- Detecting overwritting changes on upload
- git ops executed automatically



