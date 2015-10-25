class Plugin(object):
    def __init__(self, config):
        self.config = config

    def call_test(self, params):
        print params
