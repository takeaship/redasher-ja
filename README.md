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
rds setup dev http://localhost:8080 sdfa23424dfa2xcvvr23werwcdvht

# set 'dev' the default server
rds default dev

# Download all objects from dev
rds checkout

# define a second server 'prod'
rds setup prod http://redash.mycompany.com:8012 a2xcvvr23werwcdvhtsdfa23424df

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
/servers/  # contains server configurations and id object mappings
/servers/<name>.yaml # contains server configurations and id object mappings
/dashboards/<name>.yaml
/dashboards/<name>-widget-<name>.yaml
/queries/<name>/config.yaml
/queries/<name>/query.sql
/queries/<name>/query.yaml
/queries/<name>/visualization/
/queries/<name>/visualization/<name>.yaml
```

### Considerations

- Users are not to be maintained (unless you force it)
- Thus, creation and modification users are not kept
- Object creation and modification dates are not to be kept
- Groups?
- Data sources are mapped as well but not updated

### Operations (proposal)


```bash
rdgs setup testing http://localhost:8080 sdfa23424dfa2xcvvr23werwcdvht
rdgs default testing
rdgs checkout
```


