# REDASH Git Studio (WIP)

The purpose of this tool is to serialize [Redash](http://redash.io) objects
into the filesystem so that they can be maintained using tools like Git.
You might use it just to keep track of the changes, or
you can even modify those objects with a text editor and update your instance.
By adding a second Redash instance you can use this tool to syncronize their objects.
This is useful, for example, to make and test changes in a development  environment
and eventually apply those changes into a production one.


## Usage

Lets start by defining our production server, by setting up the base url
and the API key of the user we will use to interact.

```bash
rds setup prod http://redash.mycompany.com:8012 a2xcvvr23werwcdvhtsdfa23424df
```

This will create a file config.yaml in the current directory.
**DO NOT COMMIT `config.yaml`!** to a public git repository since it contains API key.

Then lets download all the object from `prod`

```bash
rds checkout prod
```

This will create some folder structure in the current directory:

```
config.yaml
maps/
maps/prod.yaml # local object files map to object ids in `prod` server
dashboards/<name>.yaml
dashboards/<name>/widgets/<name>.yaml
queries/<name>/query.sql # The query string file
queries/<name>/metadata.yaml # The rest of the metadata
queries/<name>/visualization/
queries/<name>/visualization/<name>.yaml
```

You can add those file to a version control system like git,
and keep track of your object changes in redash.

You can also modify the content of those files
and then upload them back to the server:

```bash
rds upload prod dashboard/my-dashboard
```

Another common workflow is working with an internal server
to develop without disturbing production users and then
synchronize them.

For that you must define a new server:

```bash
rds setup dev http://localhost:8080 sdfa23424dfa2xcvvr23werwcdvht
```

Datasource objects are considered readonly.
You have to define them first in your second server,
pointing to an equivalent database or API.
Then you can use the following command to relate
the object file exported from the first server
to the id of the new datasource created on the second server.


```bash
rds bind dev datasource/my-database.yaml 3
```

Then you can upload the objects to create them.

```bash
rds upload dev dashboard/my-dashboard
```

By uploading it again you will be updating them.

## Understanding maps/

The directory `maps` contains a file for each server.
Such files relates server object id's to file objects.
Such a relation is set every time you checkout an object,
or any time you upload an object for the first time into a server.

When you upload a file object to a server.
If the file object already has a bound id on the server,
the object is updated.
Otherwise a new object is created.

You can also set a server mapping by hand with the `bind` subcommand
like in the previous example with the datasource.


## Design

### The serialization format (proposal)

```
/maps/  # contains server configurations and id object mappings
/maps/<name>.yaml # contains server configurations and id object mappings
/dashboards/<name>.yaml
/dashboards/<name>/widgets/<name>.yaml
/queries/<name>/config.yaml
/queries/<name>/query.sql
/queries/<name>/query.yaml
/queries/<name>/visualization/
/queries/<name>/visualization/<name>.yaml
```

### Design forces

- While production object mapping should be part of a shared repository,
  private development servers might have sense for a single person.
  So, file-id maps should be in different files for each file so you can
  decide which servers are shared in a repository.
- Server configuration is not to be committed, apikey should be kept private
  thus separated from the server id map.
- Users might be different in production and testing, a dashboard could
  be created using a different user.
- Thus, creation and modification users are not kept
- Object creation and modification dates are not to be kept, or do they (just to compare update times)
- Groups?
- Data sources are mapped as well but not updated on upload



