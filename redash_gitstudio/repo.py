# Logic to deal with the file objects layout

from pathlib import Path
from packaging import version
from yamlns import namespace as ns
from consolemsg import fail, step
from appdirs import user_config_dir
from .redash import Redash
from .mapper import Mapper

configfile = Path(user_config_dir('redash_gitstudio'),'config.yaml')

def loadConfig():
    if not configfile.exists():
        return ns()
    return ns.load(configfile)

def serverConfig(servername=None):
    config = loadConfig()
    servername = servername or config.get('defaultserver')
    servers = config.setdefault('servers', ns())
    if not servers:
        fail("No server defined. Use setup subcommand.")
    server = servers.get(servername)
    if not server:
        fail("No such server `{}`. Try with '{}'.".format(
            servername, "', '".join(servers.keys())
        ))
    return ns(servers.get(servername), name=servername)

def setServerConfig(servername, url, apikey):
    config = loadConfig()
    servers = config.setdefault('servers', ns())
    servers[servername] = ns(
        url=url,
        apikey=apikey,
    )
    config.setdefault('defaultserver', servername)
    configfile.parent.mkdir(exist_ok=True)
    config.dump(configfile)

def defaultServer():
    config = loadConfig()
    return config.get('defaultserver', None)

def setDefaultServer(servername):
    config = loadConfig()
    servers = config.setdefault('servers', ns())
    if servername not in servers:
        fail("Server '{}' not setup.".format(servername) + (
            " Try with '{}'".format(
                "', '".join(servers))
            if servers else
            " None defined."))
    config.defaultserver = servername
    configfile.parent.mkdir(exist_ok=True)
    config.dump(configfile)


_attributesToClean = dict(
    datasource = [
        'id', # server specific
        'groups', # server specific
        'queue_name', # run-time detail
        'scheduled_queue_name', # run-time detail
        'paused', # run-time detail
    ],
    query = [
        'id', # server specific
        'user', # server specific
        'apikey', # server specific
        'last_modified_by', # server specific
        'latest_query_data_id', # run-time detail
        'query_hash', # mutates with query content
        'visualizations', # apart
        'query', # apart
        'created_at', # server specific
        'updated_at', # TODO: might be used to prevent overwritting remote changes
    ],
    dashboard = [
        'id', # server specific
        'user', # server specific
        'user_id', # server specific
        'created_at', # server specific
        'updated_at', # TODO: might be used to prevent overwritting remote changes
        'widgets', # apart
    ],
    widget = [
        'id', # server specific
        'dashboard_id', # redundant
    ],
    visualization = [
        'id', # server specific
        'created_at', # server specific
        'updated_at', # TODO: might be used to prevent overwritting remote changes
    ],
)

def _cleanUp(object, type):
    attributes = _attributesToClean.get(type, [])
    for attribute in attributes:
        if attribute not in object:
            continue
        del object[attribute]

def _dump(filename, content):
    filename.parent.mkdir(exist_ok=True, parents=True)
    print(filename)
    content.dump(filename)

def _write(filename, content):
    filename.parent.mkdir(exist_ok=True)
    filename.write_text(content, encoding='utf8')

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
        _cleanUp(datasource, 'datasource')
        _dump(datasourcepath, datasource)

    queriespath = repopath / 'queries'
    queriespath.mkdir(exist_ok=True)

    toreview = []

    for query in redash.queries():
        step("Exporting query: {id} - {name}", **query)
        query = ns(redash.query(query['id'])) # full content

        querypath = mapper.track('query', repopath/'queries', query)
        querypath.mkdir(parents=True, exist_ok=True)

        query_text = query.get('query', None)
        visualizations = query.get('visualizations',[])
        datasource_id = query.get('data_source_id', None)

        if datasource_id:
            datasourcepath = mapper.get('datasource', datasource_id)
            if not datasourcepath:
                warn("Query refers missing data source '{}'". datasource_id)
            query.data_source_id = datasourcepath

        for parameter in query.get('options', {}).get('parameters', []):
            if 'queryId' not in parameter: continue
            toreview.append(querypath/'metadata.yaml')

        if query_text is not None:
            _write(querypath/'query.sql', query_text)

        _cleanUp(query, 'query')
        _dump(querypath/'metadata.yaml', query)


        for vis in visualizations:
            vis = ns(vis)
            step("Exporting visualization {id} {type} {name}", **vis)
            vispath = mapper.track('visualization', querypath/'visualizations', vis, suffix='.yaml')
            _cleanUp(vis, 'visualization')
            _dump(vispath, vis)

    for queryMetaFile in toreview:
        query = ns.load(queryMetaFile)
        for parameter in query.get('options', {}).get('parameters', []):
            if 'queryId' not in parameter: continue
            parameter.queryId = mapper.get('query', parameter.queryId)
        _dump(queryMetaFile, query)

    for dashboard in redash.dashboards():
        step("Exporting dashboard: {slug} - {name}", **dashboard)
        dashboard = ns(redash.dashboard(dashboard['slug' if dashboard_with_slugs else 'id']))
        dashboardpath = mapper.track('dashboard', repopath/'dashboards', dashboard)
        widgets = dashboard.get('widgets',[])
        _cleanUp(dashboard, 'dashboard')
        _dump(dashboardpath/'metadata.yaml', dashboard)
        for widget in widgets:
            widget = ns(widget)
            widgetpath = mapper.track('widget', dashboardpath/'widgets', widget, suffix='.yaml')
            vis = widget.get('visualization', None)
            if vis:
                widget.visualization = mapper.get('visualization', vis['id'])
            _cleanUp(widget, 'widget')
            _dump(widgetpath, widget)


