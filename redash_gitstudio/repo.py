# Logic to deal with the file objects layout

from pathlib import Path
from packaging import version
from yamlns import namespace as ns
from consolemsg import fail, step, warn
from appdirs import user_config_dir
from .redash import Redash
from .mapper import Mapper
import sys

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
        'api_key', # server specific
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
        'version', # TODO: might be used to prevent overwritting remote changes
    ],
    widget = [
        'id', # server specific
        'dashboard_id', # redundant
        'created_at', # server specific
        'updated_at', # TODO: might be used to prevent overwritting remote changes
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
    normalized = filename
    if filename.name in ('metadata.yaml'):
        normalized = filename.parent
    filetype = _path2type(normalized)
    print(filetype, filename)
    _cleanUp(content, filetype)
    content = ns(sorted(content.items()))
    content.dump(filename)

def _write(filename, content):
    filename.parent.mkdir(exist_ok=True)
    print(_path2type(filename), filename)
    filename.write_text(content, encoding='utf8')

def parentObjectPath(path):
    return Path(*path.parts[:2])

def _path2type(path):
    components = list(path.parts)

    def ispart(position, name):
        if name not in components: return False
        return components.index(name) == position

    if ispart(0, 'datasources'):
        return 'datasource'

    if ispart(0, 'dashboards'):
        if ispart(2, 'widgets'):
            if len(components) != 4:
                return None
            return 'widget'
        if len(components) != 2:
            return None
        return 'dashboard'

    if ispart(0, 'queries'):
        if ispart(2, 'visualizations'):
            if len(components) != 4:
                return None
            return 'visualization'
        if len(components) != 2:
            return None
        return 'query'

def _read(path):
    return path.read_text(encoding='utf8')



from decorator import decorator

def level(type):
    def _wrap(f, *args, **kwds):
        self = args[0]
        filename = Path(args[1])
        id = None
        try:
            id = self.enterLevel(type, filename)
            if id: return id
            id = f(self, filename)
        finally:
            self.exitLevel(type, filename, id)
        return id

    return decorator(_wrap)



class Uploader(object):
    def __init__(self, servername):
        config = serverConfig(servername)
        self.servername = config.name # param might be None, this solves
        self.redash = Redash(config.url, config.apikey)
        self.mapper = Mapper(Path('.'), config.name)

        self.uploaded = set()
        self.levels = 0
        self.unboundDefaultVisualizations = ns()

    def step(self, msg, *args, **kwds):
        step("  "*self.levels + msg, *args, **kwds)

    def warn(self, msg, *args, **kwds):
        warn("  "*self.levels + msg, *args, **kwds)

    def enterLevel(self, objecttype, filename):
        self.levels +=1

        if filename in self.uploaded:
            self.step("Skipped {} {}", objecttype, filename)
            return self.mapper.remoteId(objecttype, filename)

        id = self.mapper.remoteId(objecttype, filename)
        self.step("{} {} {}", "Update" if id else "Create", objecttype, filename)
        filetype = _path2type(filename)
        if filetype != objecttype:
            fail("{} is not a {} but a {}".format(filename, objecttype, filetype))

        self.uploaded.add(filename)
        return False

    def exitLevel(self, objecttype, filename, id):
        #self.step("Done {} {} = {}", objecttype, filename, id)
        self.levels -=1

    def upload(self, *filenames):
        for filename in filenames:
            self.step("Recursive upload starting at {}", filename)
            filename = Path(filename)
            if filename.name == 'metadata.yaml':
                filename = filename.parent
            filetype = _path2type(filename)
            handler = dict(
                dashboard = self.uploadDashboard,
                query = self.uploadQuery,
                widget = self.uploadWidget,
                visualization = self.uploadVisualization,
            ).get(filetype, None)
            if not handler:
                fail("Unsuported file object type '{}'".format(filename))
            handler(filename)

        for view, visId in self.unboundDefaultVisualizations.items():
            warn("Unbound default TABLE visualization {} created for {}".
                format(visId, view)
            )

    @level('dashboard')
    def uploadDashboard(self, filename):

        metadatafile = filename/'metadata.yaml'
        dashboard = ns.load(metadatafile)

        dashboardId = self.mapper.remoteId('dashboard', filename)
        if not dashboardId:
            dashboardId = ns(self.redash.create_dashboard(dashboard.name)).id
            self.mapper.bind('dashboard', dashboardId, filename)
            self.step("Created a new dashboard {}", dashboardId)

        # TODO: Compare update date with last date from server

        params = {
            param: dashboard[param]
            for param in [
                "slug",
                "tags",
                "dashboard_filters_enabled",
                "is_archived",
                "is_favorite",
                "is_draft",
                #"can_edit",
                #"layout",
            ]
            if param in dashboard
        }
        if params:
            self.redash.update_dashboard(dashboardId, params)

        for widgetfile in filename.glob('widgets/*.yaml'):
            self.uploadWidget(widgetfile)

        return dashboardId

    @level('widget')
    def uploadWidget(self, filename):

        widget = ns.load(filename)
        dashboardPath = parentObjectPath(filename)
        dashboardId = self.uploadDashboard(dashboardPath)

        visId = (
            self.uploadVisualization(widget.visualization)
            if 'visualization' in widget else None
        )
        widgetId = self.mapper.remoteId('widget', filename)
        params = ns(
            dashboard_id = dashboardId,
            visualization_id = visId,
            text = widget.text,
            width = widget.width,
            options = widget.options,
        )
        if widgetId:
            self.redash.update_widget(widgetId, params)
        else:
            newwidget = ns(self.redash.create_widget(**params))
            widgetId = newwidget.id
            self.mapper.bind('widget', widgetId, filename)

        return widgetId

    @level('datasource')
    def uploadDataSource(self, filename):
        dataSourceId = self.mapper.remoteId('datasource', filename)
        if dataSourceId: return dataSourceId
        # No creation is done when not found.
        # Data sources are defined differently on each server,
        # so it must be done by hand.
        available = "\n".join(
            "  {id}: {name}".format(**ns(ds))
            for ds in self.redash.datasources()
            ) or "No data source available yet in the server."
        fail(
            "Data source {filename} is not bound to any sources on server '{server}'.\n"
            "You might want to choose or create one in the server "
            "and bind it with the following command:\n"
            "  {command} bind {server} datasource {filename} <id>\n"
            "Available data sources are:\n{available}"
            .format(
                command=sys.argv[0],
                filename=filename,
                server=self.servername,
                available=available,
            )
        )

    @level('query')
    def uploadQuery(self, filename):
        query = ns.load(filename/'metadata.yaml')
        query.query = _read(filename/'query.sql')
        dataSourceId = self.uploadDataSource(query.data_source_id)
        queryId = self.mapper.remoteId('query', filename)
        params = ns(
            name = query.name,
            description = query.description,
            data_source_id = dataSourceId,
            query = query.query,
            schedule = query.schedule,
            is_archived = query.is_archived,
            is_draft = query.is_draft,
            options = query.options,
        )

        for parameter in query.options.get('parameters', []):
            if 'queryId' in parameter:
                parameter.queryId = self.uploadQuery(parameter.queryId)
        if queryId:
            self.redash.update_query(queryId, params)
        else:
            remotequery = ns(self.redash.create_query(**params))
            queryId = remotequery.id
            self.mapper.bind('query', queryId, filename)

            defaultView = remotequery.visualizations[0]['id']
            self.unboundDefaultVisualization(filename, defaultView)

        self.redash.update_query(queryId, ns(
            tags = query.tags,
            is_draft = query.is_draft,
        ))


        for visualizationfile in filename.glob('visualizations/*.yaml'):
            visId = self.uploadVisualization(visualizationfile)

        return queryId

    def unboundDefaultVisualization(self, queryfile, visId):
        self.unboundDefaultVisualizations[queryfile]=visId

    def bindDefaultVisualization(self, filename):
        queryfile = parentObjectPath(filename)
        visId = self.unboundDefaultVisualizations.pop(queryfile, None)
        if visId:
            self.mapper.bind('visualization', visId, filename)
            self.step(
                "Visualization bound to default created one {}"
                .format(visId)
            )
        return visId

    @level('visualization')
    def uploadVisualization(self, filename):
        queryfile = parentObjectPath(filename)
        queryId = self.uploadQuery(queryfile)

        visualization = ns.load(filename)
        visId = self.mapper.remoteId('visualization', filename)

        # Bind the default created visualization
        if not visId and visualization.type == 'TABLE':
            visId = self.bindDefaultVisualization(filename)

        params = ns(
            query_id = queryId,
            name = visualization.name,
            description = visualization.description,
            type = visualization.type,
            options = visualization.options,
        )

        if not visId:
            visId = ns(self.redash.create_visualization(**params)).id
            self.mapper.bind('visualization', visId, filename)
        else:
            self.redash.update_visualization(visId, **params)

        return visId


def uploadFile(servername, *filenames):
    uploader = Uploader(servername)
    uploader.upload(*filenames)

def checkoutAll(servername):
    Downloader(servername).checkoutAll()

class Downloader(object):
    def __init__(self, servername):
        config = serverConfig(servername)
        self.servername = config.name # param might be None, this solves
        self.redash = Redash(config.url, config.apikey)
        self.repopath = Path('.')
        self.mapper = Mapper(self.repopath, config.name)

    def checkoutDataSources(self):
        datasourcespath = self.repopath / 'datasources'
        datasourcespath.mkdir(exist_ok=True)

        for datasource in self.redash.datasources():
            step("Exporting data source: {id} - {name}", **datasource)
            datasource = ns(self.redash.datasource(datasource['id'])) # full content
            datasourcepath = self.mapper.track('datasource', datasourcespath, datasource, suffix='.yaml')
            _dump(datasourcepath, datasource)

    def checkoutQueries(self):
        queriespath = self.repopath / 'queries'
        queriespath.mkdir(exist_ok=True)

        toreview = []

        for query in self.redash.queries():
            step("Exporting query: {id} - {name}", **query)
            query = ns(self.redash.query(query['id'])) # full content

            querypath = self.mapper.track('query', self.repopath/'queries', query)
            querypath.mkdir(parents=True, exist_ok=True)

            query_text = query.get('query', None)
            visualizations = query.get('visualizations',[])
            datasource_id = query.get('data_source_id', None)

            if datasource_id:
                datasourcepath = self.mapper.get('datasource', datasource_id)
                if not datasourcepath:
                    warn("Query refers missing data source '{}'". datasource_id)
                query.data_source_id = datasourcepath

            for parameter in query.get('options', {}).get('parameters', []):
                if 'queryId' not in parameter: continue
                toreview.append(querypath/'metadata.yaml')

            if query_text is not None:
                _write(querypath/'query.sql', query_text)

            _dump(querypath/'metadata.yaml', query)


            for vis in visualizations:
                vis = ns(vis)
                step("Exporting visualization {id} {type} {name}", **vis)
                vispath = self.mapper.track('visualization', querypath/'visualizations', vis, suffix='.yaml')
                _dump(vispath, vis)

        for queryMetaFile in toreview:
            query = ns.load(queryMetaFile)
            for parameter in query.get('options', {}).get('parameters', []):
                if 'queryId' not in parameter: continue
                parameter.queryId = self.mapper.get('query', parameter.queryId)
            _dump(queryMetaFile, query)

    def checkoutDashboards(self):
        status = ns(self.redash.status())
        dashboard_with_slugs = version.parse(status.version) < version.parse('9-alpha')

        for dashboard in self.redash.dashboards():
            step("Exporting dashboard: {slug} - {name}", **dashboard)
            idfield = 'slug' if dashboard_with_slugs else 'id'
            dashboard = ns(self.redash.dashboard(dashboard[idfield]))
            dashboardpath = self.mapper.track('dashboard', self.repopath/'dashboards', dashboard)
            widgets = dashboard.get('widgets',[])
            _dump(dashboardpath/'metadata.yaml', dashboard)
            for widget in widgets:
                widget = ns(widget)
                widgetpath = self.mapper.track('widget', dashboardpath/'widgets', widget, suffix='.yaml')
                vis = widget.get('visualization', None)
                if vis:
                    widget.visualization = self.mapper.get('visualization', vis['id'])
                _dump(widgetpath, widget)

    def checkoutAll(self):
        self.checkoutDataSources()
        self.checkoutQueries()
        self.checkoutDashboards()





