#!/usr/bin/env python
__version__ = '0.1'

import click
from pathlib import Path
from yamlns import namespace as ns
from consolemsg import out, warn, step, fail
from packaging import version
from .redash import Redash
from .mapper import Mapper
from .repo import (
    serverConfig,
    setServerConfig,
    defaultServer,
    setDefaultServer,
)



@click.group()
@click.help_option()
@click.version_option(__version__)
def cli():
    'Manages a git controlled and file based version of Redash dashboards'

@cli.command('list')
def _list():
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    for dashboard in redash.dashboards():
        dashboard = ns(dashboard)
        out("{}: {} \"{}\"", dashboard.id, dashboard.slug, dashboard.name)

@cli.command()
@click.argument('id')
def pull(id):
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    dashboard = ns(redash.dashboard(id))
    dashboard.dump("{}.yaml".format(dashboard.slug))
    click.echo(dashboard.dump())


@cli.command()
def qlist():
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    for query in redash.queries():
        query = ns(query)
        print(query.dump())
        out("{}: \"{}\"", query.id, query.name)

@cli.command()
def ulist():
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    for user in redash.users():
        user = ns(user)
        out("{}: \"{}\"", user.id, user.name)

@cli.command()
@click.argument('id')
def qpull(id):
    """Retrieve a query"""
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    query = ns(redash.query(id))
    #query.dump("{}.yaml".format(query.slug))
    click.echo(query.dump())

@cli.command()
@click.argument("servername")
@click.argument("url")
@click.argument("apikey")
def setup(servername, url, apikey):
    """Configures a Redash server to work with.

    SERVERNAME is the name setup for the server.
    URL is the base url for the server.
    APIKEY is the validation key related to the user
    the program is going to act in behalf on.

    If no default server has been configured this
    server will be considered default.
    """
    setServerConfig(servername, url, apikey)

@cli.command()
@click.argument("servername", required=False)
def default(servername=None):
    """Sets or shows the default server name to work with.

    Shows instead of setting it, if no SERVERNAME is provided.
    """
    if servername:
        setDefaultServer(servername)
        return
    servername = defaultServer()
    if not servername:
        fail("No default server defined")
    print(servername)


@cli.command()
@click.argument(
    "servername",
    required=False,
    #help="The name of the server",
)
def checkout(servername):
    """Downloads all objects from a Redash server"""
    config = serverConfig(servername)
    redash = Redash(config.url, config.apikey)
    repopath = Path('.')
    mapper = Mapper(repopath, servername)

    status = ns(redash.status())
    dashboard_with_slugs = version.parse(status.version) < version.parse('9-alpha')

    datasourcespath = repopath / 'datasources'
    datasourcespath.mkdir(exist_ok=True)

    for datasource in redash.datasources():
        step("Exporting data source: {id} - {name}", **datasource)
        datasource = ns(redash.datasource(datasource['id'])) # full content
        datasourcepath = mapper.track('datasource', datasourcespath, datasource, suffix='.yaml')

        del datasource.id
        del datasource.groups
        del datasource.queue_name
        del datasource.scheduled_queue_name
        datasource.dump(datasourcepath)

    queriespath = repopath / 'queries'
    queriespath.mkdir(exist_ok=True)

    toreview = []

    for query in redash.queries():
        step("Exporting query: {id} - {name}", **query)
        query = ns(redash.query(query['id'])) # full content

        querypath = mapper.track('query', repopath/'queries', query)
        querypath.mkdir(parents=True, exist_ok=True)

        del query.id
        del query.user
        del query.last_modified_by
        query_text = query.pop('query', None)
        visualizations = query.pop('visualizations',[])
        datasource_id = query.get('data_source_id', None)
        if datasource_id:
            datasourcepath = mapper.get('datasource', datasource_id)
            if not datasourcepath:
                warn("Query refers missing data source '{}'". datasource_id)
            query.data_source_id = datasourcepath

        for parameter in query.get('options', {}).get('parameters', []):
            if 'queryId' not in parameter: continue
            toreview.append(querypath/'metadata.yaml')

        query.dump(querypath/'metadata.yaml')

        if query_text is not None:
            (querypath/'query.sql').write_text(query_text, encoding='utf8')

        for vis in visualizations:
            vis = ns(vis)
            step("Exporting visualization {id} {type} {name}", **vis)
            vispath = mapper.track('visualization', querypath, vis, 'vis-', '.yaml')
            vis.dump(vispath)

    for queryMetaFile in toreview:
        query = ns.load(queryMetaFile)
        for parameter in query.get('options', {}).get('parameters', []):
            if 'queryId' not in parameter: continue
            parameter.queryId = mapper.get('query', parameter.queryId)
        query.dump(queryMetaFile)

    dashboardspath = repopath / 'dashboards'
    dashboardspath.mkdir(exist_ok=True)
    for dashboard in redash.dashboards():
        step("Exporting dashboard: {slug} - {name}", **dashboard)
        dashboard = ns(redash.dashboard(dashboard['slug' if dashboard_with_slugs else 'id']))
        dashboardpath = mapper.track('dashboard', repopath/'dashboards', dashboard)
        del dashboard.id
        del dashboard.user
        del dashboard.user_id
        widgets = dashboard.pop('widgets',[])
        dashboardpath.mkdir(parents=True, exist_ok=True)
        dashboard.dump(dashboardpath/'metadata.yaml')
        for widget in widgets:
            widget = ns(widget)
            widgetpath = mapper.track('widget', dashboardpath/'widgets', widget, suffix='.yaml')
            vis = widget.pop('visualization', None)
            del widget.id
            del widget.dashboard_id
            if vis:
                widget.visualization = mapper.get('visualization', vis['id'])
            widgetpath.parent.mkdir(parents=True, exist_ok=True)
            ns(widget).dump(widgetpath)


if __name__=='__main__':
    cli()

