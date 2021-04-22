# REDASH Git Studio (WIP)

The purpose of this tool is to serialize [Redash](http://redash.io) objects
into the filesystem so that they can be maintained using tools like Git.
You might use it just to keep track of the changes, or
you can even modify those objects with a text editor and update your instance.
By adding a second Redash instance you can use this tool to syncronize their objects.
This is useful, for example, to make and test changes in a development  environment
and eventually apply those changes into a production one.


## Usage


```bash
# Define a server, will create a config.yaml file
# DO NOT COMMIT config.yaml it contains the API key
rds setup prod http://redash.mycompany.com:8012 a2xcvvr23werwcdvhtsdfa23424df

# Download all objects from prod
rds checkout prod

# define a second server 'dev'
rds setup dev http://localhost:8080 sdfa23424dfa2xcvvr23werwcdvht

# Data sources are not uploaded for safety, so
# in order to transfer objects from one server to another,
# you must create them by hand in the target and then bind
# the id to the file object.
# This command, binds datasource id 3 in 'prod'
# with the datasource file object datasource/my-database.yaml
# exported from 'dev'
rds bind prod datasource/my-database.yaml 3

```



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



