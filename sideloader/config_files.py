import os


class ConfigFiles(object):
    """
    Container class for storing a list of config files associated with a
    directory that they should be copied into.
    """
    def __init__(self, files, config_dir_path, dependencies=[]):
        """
        :param: files:
        A list of paths to files relative to the repo directory.

        :param: config_dir_path:
        The path to the directory where the config files should be copied.

        :param: dependencies:
        A list of dependencies for these config files. For example, for nginx
        config files to be useful, nginx needs to be installed, so it could be
        added as a dependency.
        """
        self.files = files
        self.config_dir_path = config_dir_path
        self.dependencies = dependencies

    @classmethod
    def nginx(cls, files):
        return ConfigFiles(
            files,
            os.path.join('etc', 'nginx', 'sites-enabled'),
            ['nginx-light']
        )

    @classmethod
    def supervisor(cls, files):
        return ConfigFiles(
            files,
            os.path.join('etc', 'supervisor', 'conf.d'),
            ['supervisor']
        )
