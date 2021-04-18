# REDASH Git Studio

The purpose of this tool is to serialize [Redash](http://redash.io) objects
into the filesystem so that they can be maintained using tools like Git.
You might use it just to keep track of the changes, or
you can even modify those objects with a text editor and update your instance.
By adding a second Redash instance you can use this tool to syncronize their objects.
This is useful, for example, to make and test changes in a development  environment
and eventually apply those changes into a production one.


## The serialization format

(Proposal)

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




