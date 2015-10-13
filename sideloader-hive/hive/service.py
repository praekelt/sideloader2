import time
import json
import traceback

from twisted.application import service
from twisted.internet import task, reactor, protocol, defer
from twisted.python import log

from txredis.client import RedisClient, RedisSubscriber


class HiveService(service.Service):
    """ Hive service
    Runs timers, configures sources and and manages the queue
    """
    def __init__(self, config):
        self.config = config

    @defer.inlineCallbacks
    def grabQueue(self, queue=0):
        response = yield self.client.rpop("hive.q%s" % queue)

        if response:
            response = json.loads(response)
        
        defer.returnValue(response)

    @defer.inlineCallbacks
    def reQueue(self, request, queue=0):
        response = yield self.client.lpush("hive.q%s" % queue)

    def processItem(self, item):
        pass

    @defer.inlineCallbacks
    def queueRun(self):
        item = yield self.grabQueue()

        if item:
            m = item.get('message')
            if m:
                id = item['id']
                try:
                    result = yield self.processItem(item)

                    d = {
                        'result': result,
                        'time': time.time()
                    }

                    yield self.client.set(
                        'hive.q0.%s' % id, json.dumps(d), expire=3600)

                except Exception, e:
                    log.msg('Error %s' % e)
                    log.msg(traceback.format_exc())

            reactor.callLater(0.01, self.queueRun)
        else:
            reactor.callLater(1.0, self.queueRun)

        defer.returnValue(None)

    @defer.inlineCallbacks
    def startService(self):
        clientCreator = protocol.ClientCreator(reactor, RedisClient)
        self.client = yield clientCreator.connectTCP(
            self.redis_host, self.redis_port)

        yield self.queueRun()

def makeService(config):
    return HiveService(config)

