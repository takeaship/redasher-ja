#!/usr/bin/env python
__version__ = '0.1'

import click
from pathlib import Path
from yamlns import namespace as ns
from consolemsg import out, step
from .redash import Redash
from .mapper import Mapper


config = ns.load("config.yaml")

@click.group()
@click.help_option()
@click.version_option(__version__)
def cli():
    'Manages a git controlled and file based version of Redash dashboards'

@cli.command('list')
def _list():
    redash = Redash(config.url, config.apikey)
    for dashboard in redash.dashboards():
        dashboard = ns(dashboard)
        out("{}: {} \"{}\"", dashboard.id, dashboard.slug, dashboard.name)

@cli.command()
@click.argument('id')
def pull(id):
    redash = Redash(config.url, config.apikey)
    dashboard = ns(redash.dashboard(id))
    dashboard.dump("{}.yaml".format(dashboard.slug))
    click.echo(dashboard.dump())


@cli.command()
def qlist():
    redash = Redash(config.url, config.apikey)
    for query in redash.queries():
        query = ns(query)
        print(query.dump())
        out("{}: \"{}\"", query.id, query.name)

@cli.command()
def ulist():
    redash = Redash(config.url, config.apikey)
    for user in redash.users():
        user = ns(user)
        out("{}: \"{}\"", user.id, user.name)

@cli.command()
@click.argument('id')
def qpull(id):
    """Retrieve a query"""
    redash = Redash(config.url, config.apikey)
    query = ns(redash.query(id))
    #query.dump("{}.yaml".format(query.slug))
    click.echo(query.dump())

@cli.command()
@click.argument(
    "servername",
    #help="The name of the server",
)
@click.argument(
    "url",
    #help="Base url of the server",
)
@click.argument(
    "apikey",
    #help="User API key to be used to access the server",
)
def setup(servername, url, apikey):
    configfile = Path('config.yaml')
    config = ns.load(configfile) if configfile.exists else ns()
    servers = config.setdefault('servers', ns())
    servers[servername] = ns(
        url=url,
        apikey=apikey,
    )
    config.setdefault('defaultserver', servername)
    config.dump(configfile)


def serverConfig(servername=None):
    configfile = Path('config.yaml')
    config = ns.load(configfile) if configfile.exists else ns()
    servername = servername or config.get('defaultserver')
    servers = config.setdefault('servers', ns())
    return servers.get(servername)

@cli.command()
@click.argument(
    "servername",
    required=False,
    #help="The name of the server",
)
def checkout(servername):
    config = serverConfig(servername)
    redash = Redash(config.url, config.apikey)
    repopath = Path('.')
    mapper = Mapper(repopath, servername)

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
        dashboard = ns(redash.dashboard(dashboard['slug'])) # TODO: id in new redash version
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

