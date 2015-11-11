from rhumba.client import RhumbaClient

def build(build):
    c = RhumbaClient()

    print build

    return c.queue('sideloader', 'build', {})

def getClusterStatus():
    return RhumbaClient().clusterStatus()
