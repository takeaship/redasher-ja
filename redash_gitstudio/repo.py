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
    normalized = filename
    if filename.name in ('metadata.yaml'):
        normalized = filename.parent
    filetype = _path2type(normalized)
    print(filetype, filename)
    _cleanUp(content, filetype)
    content.dump(filename)

def _write(filename, content):
    filename.parent.mkdir(exist_ok=True)
    print(_path2type(filename), filename)
    filename.write_text(content, encoding='utf8')

def _path2type(path):
    components = list(path.parts)

    def has(part, position):
        if part not in components: return False
        return components.index(part) == position

    if has('datasources', 0):
        return 'datasource'

    if has('dashboards', 0):
        if has('widgets', 2):
            if len(components) != 4:
                return None
            return 'widget'
        if len(components) != 2:
            return None
        return 'dashboard'

    if has('queries', 0):
        if has('visualizations', 2):
            if len(components) != 4:
                return None
            return 'visualization'
        if len(components) != 2:
            return None
        return 'query'

def _read(path):
    return path.read_text(encoding='utf8')

from decorator import decorator
@decorator
def level(f, self, *args, **kwds):
    self.levels +=1
    result = f(self, *args, **kwds)
    self.levels -=1
    return result



class Uploader(object):
    def __init__(self, servername):
        config = serverConfig(servername)
        self.servername = config.name # param might be None, this solves
        self.redash = Redash(config.url, config.apikey)
        self.mapper = Mapper(Path('.'), config.name)
        self.uploaded = set()
        self.levels = 0

    def step(self, msg, *args, **kwds):
        step("  "*self.levels + msg, *args, **kwds)

    def warn(self, msg, *args, **kwds):
        warn("  "*self.levels + msg, *args, **kwds)


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

    @level
    def uploadDashboard(self, filename):
        if not self._check('dashboard', filename):
            return self.mapper.remoteId('dashboard', filename)

        dashboardpath = Path(*filename.parts[:2])
        metadatafile = dashboardpath/'metadata.yaml'
        localDashboard = ns.load(metadatafile)

        dashboardId = self.mapper.remoteId('dashboard', dashboardpath)
        if not dashboardId:
            dashboardId = ns(self.redash.create_dashboard(localDashboard.name)).id
            self.mapper.bind('dashboard', dashboardId, dashboardpath)
            self.step("Created a new dashboard {}", dashboardId)

        # TODO: Compare update date with last date from server

        dashboard_params = {
            param: localDashboard[param]
            for param in [
                "slug",
                "tags",
                "dashboard_filters_enabled",
                "is_archived",
                "is_favorite",
                #"can_edit",
                #"layout",
            ]
            if param in localDashboard
        }
        if dashboard_params:
            self.redash.update_dashboard(dashboardId, dashboard_params)

        for widgetfile in dashboardpath.glob('widgets/*.yaml'):
            self.uploadWidget(widgetfile)

        return dashboardId

    @level
    def uploadWidget(self, filename):
        if not self._check('widget', filename):
            return self.mapper.remoteId('widget', filename)

        widget = ns.load(filename)
        dashboardPath = Path(*filename.parts[:2])
        dashboardId = self.uploadDashboard(dashboardPath)

        visId = (
            self.uploadVisualization(widget.visualization)
            if 'visualization' in widget else None
        )
        widgetId = self.mapper.remoteId('widget', filename)
        widgetData = ns(
            dashboard_id = dashboardId,
            visualization_id = visId,
            text = widget.text,
            width = widget.width,
            options = widget.options,
        )
        if widgetId:
            self.redash.update_widget(widgetId, widgetData)
            self.step("  updated widget {}".format(widgetId))
        else:
            newwidget = ns(self.redash.create_widget(**widgetData))
            widgetId = newwidget.id
            self.mapper.bind('widget', widgetId, filename)
            self.step("  created widget {}".format(widgetId))

        return widgetId

    @level
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

    @level
    def uploadQuery(self, filename):
        filename = Path(filename)
        if not self._check('query', filename):
            return self.mapper.remoteId('query', filename)
        query = ns.load(filename/'metadata.yaml')
        query.query = _read(filename/'query.sql')
        dataSourceId = self.uploadDataSource(query.data_source_id)
        queryId = self.mapper.remoteId('query', filename)
        newQuery = ns(
            name = query.name,
            description = query.description,
            data_source_id = dataSourceId,
            query = query.query,
            schedule = query.schedule,
            is_archived = query.is_archived,
            is_draft = query.is_draft,
            options = query.options,
            tags = query.tags,
        )

        for parameter in query.options.get('parameters', []):
            if 'queryId' in parameter:
                parameter.queryId = self.uploadQuery(parameter.queryId)
        defaultVisualization = None
        if not queryId:
            remotequery = ns(self.redash.create_query(**newQuery))
            queryId = remotequery.id
            defaultVisualization = remotequery.visualizations[0]['id']
            self.mapper.bind('query', queryId, filename)
            self.step("  created query {}", queryId)
        else:
            self.redash.update_query(
                query_id = queryId,
                data = newQuery
            )
            self.step("  updated query {}", queryId)

        for visualizationfile in filename.glob('visualizations/*.yaml'):
            visId = self.uploadVisualization(visualizationfile, defaultVisualization)
            if visId == defaultVisualization:
                defaultVisualization = None

        if defaultVisualization:
            warn("Unbound default TABLE visualization created")

        return queryId

    @level
    def uploadVisualization(self, filename, defaultVisualization=None):
        filename = Path(filename)
        if not self._check('visualization', filename):
            return self.mapper.remoteId('visualization', filename)

        # TODO: What if the default visualization is the first one
        queryfile = visualization2query(filename)
        queryId = self.uploadQuery(queryfile)

        visualization = ns.load(filename)
        visId = self.mapper.remoteId('visualization', filename)

        # Bind the default created visualization
        if not visId and defaultVisualization and visualization.type == 'TABLE':
            self.mapper.bind('visualization', defaultVisualization, filename)
            visId = defaultVisualization
            self.step("  visualization bound to default one")

        data = ns(
            query_id = queryId,
            name = visualization.name,
            description = visualization.description,
            type = visualization.type,
            options = visualization.options,
        )

        if not visId:
            visId = ns(self.redash.create_visualization(**data)).id
            self.mapper.bind('visualization', visId, filename)
            self.step("  visualization created {}".format(visId))
        else:
            self.redash.update_visualization(visId, **data)
            self.step("  visualization updated {}".format(visId))

        return visId

    def _check(self, objecttype, filename):
        if filename in self.uploaded:
            #self.warn("Ignoring already uploaded {} {}", objecttype, filename)
            return False
        filetype = _path2type(filename)
        if filetype != objecttype:
            fail("{} is not a {} but a {}".format(filename, objecttype, filetype))

        self.uploaded.add(filename)
        self.step("Uploading {} {}", objecttype, filename)
        return True



def uploadFile(servername, *filenames):
    uploader = Uploader(servername)
    uploader.upload(*filenames)


def visualization2query(path):
    return Path(*Path(path).parts[:2])

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

        _dump(querypath/'metadata.yaml', query)


        for vis in visualizations:
            vis = ns(vis)
            step("Exporting visualization {id} {type} {name}", **vis)
            vispath = mapper.track('visualization', querypath/'visualizations', vis, suffix='.yaml')
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
        _dump(dashboardpath/'metadata.yaml', dashboard)
        for widget in widgets:
            widget = ns(widget)
            widgetpath = mapper.track('widget', dashboardpath/'widgets', widget, suffix='.yaml')
            vis = widget.get('visualization', None)
            if vis:
                widget.visualization = mapper.get('visualization', vis['id'])
            _dump(widgetpath, widget)

