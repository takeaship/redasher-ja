# Logic to deal with the file objects layout

from yamlns import namespace as ns
from pathlib import Path
from consolemsg import fail

configfile = Path('config.yaml')

def loadConfig():
    if not configfile.exists():
        return ns()
    return ns.load(configfile)

def serverConfig(servername=None):
    config = loadConfig()
    servername = servername or config.get('defaultserver')
    servers = config.setdefault('servers', ns())
    return servers.get(servername)

def setServerConfig(servername, url, apikey):
    config = loadConfig()
    servers = config.setdefault('servers', ns())
    servers[servername] = ns(
        url=url,
        apikey=apikey,
    )
    config.setdefault('defaultserver', servername)
    config.dump(configfile)

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

def defaultServer():
    config = loadConfig()
    return config.get('defaultserver', None)



