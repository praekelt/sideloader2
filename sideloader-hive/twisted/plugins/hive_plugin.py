from zope.interface import implements
 
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
 
from hive import service
 
class Options(usage.Options):
    optParameters = [
        ["config", "c", "hive.yml", "Config file"],
    ]
 
class HiveServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "hive"
    description = "An asynchronous job queue for Sideloader"
    options = Options
 
    def makeService(self, options):
        try:
            config = open(options['config'])
        except:
            config = "{}"
        return service.makeService(config)
 
serviceMaker = HiveServiceMaker()
