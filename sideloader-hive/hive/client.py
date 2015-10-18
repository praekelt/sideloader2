import redis
import json
import uuid

class HiveClient(object):
    """
    Hive client
    """
    def __init__(self, host='localhost', port=6379, db=0):
        self.host = host
        self.port = port
        self.db = db

    def _get_client(self):
        return redis.StrictRedis(host=self.host, port=self.port, db=self.db)

    def queue(self, message, params={}, queue=0):
        """
        Queue a job in Hive
        """
        d = {
            'id': uuid.uuid1().get_hex(),
            'version': 1,
            'message': message,
            'params': params
        }

        self._get_client().lpush('hive.q%s' % queue, json.dumps(d))
        print 'queued'
        return d['id']

    def getResult(self, id):
        """
        Retrieve the result of a job from its ID
        """
        return json.loads(
            self._get_client().get('hive.r.%s' % id)
        )

