# Logic to deal with the file objects layout

from pathlib import Path
from packaging import version
from yamlns import namespace as ns
from consolemsg import fail, step
from .redash import Redash
from .mapper import Mapper

configfile = Path('config.yaml')

def loadConfig():
    if not configfile.exists():
        return ns()
    return ns.load(configfile)

def serverConfig(servername=None):
    config = loadConfig()
    servername = servername or config.get('defaultserver')
    servers = config.setdefault('servers', ns())
    return ns(servers.get(servername), name=servername)

def setServerConfig(servername, url, apikey):
    config = loadConfig()
    servers = config.setdefault('servers', ns())
    servers[servername] = ns(
        url=url,
        apikey=apikey,
    )
    config.setdefault('defaultserver', servername)
    config.dump(configfile)

def defaultServer():
    config = loadConfig()
    return config.get('defaultserver', None)

def setDefaultServer(servername):
    config = loadConfig()
    servers = config.setdefault('servers', ns())
    if servername not in servers:
        fail("Server '{}' not setup.".format(servername) + (
            " Try with {}".format(
                ', '.join(servers))
            if servers else
            " None defined."))
    config.defaultserver = servername
    config.dump(configfile)


def checkoutAll(servername):
    config = serverConfig(servername)
    redash = Redash(config.url, config.apikey)
    repopath = Path('.')
    mapper = Mapper(repopath, config.name)

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


