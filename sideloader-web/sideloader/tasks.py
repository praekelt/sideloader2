from hive.client import HiveClient

def build(build):
    c = HiveClient()

    print build

    return c.queue('build', {})
