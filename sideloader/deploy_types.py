import os

from utils import create_venv_paths


class DeployType(object):
    """
    Object that defines certain attributes of our (not fpm's) deploy types.
    """

    def __init__(self, fpm_deploy_type='dir', dependencies=[],
                 provides_version=False):
        """
        :param: fpm_deploy_type:
        A string of the deploy type used with fpm.

        :param: dependencies:
        A list of string dependencies specific to the *deployment type* (not
        any particular deployment). For example, virtualenv deployments require
        that `python-virtualenv` is installed on the target machine.

        :param: provides_version:
        Some deploy types have their own version information. If so, this
        should be set true and fpm will determine the version of the package
        from the source. For example, python packages have their versions
        specified in `setup.py`.
        """
        self.fpm_deploy_type = fpm_deploy_type
        self.dependencies = dependencies
        self.provides_version = provides_version

    def get_set_up_script(self, workspace, deploy):
        """
        Generate scripting to inject before the user's postinstall script.

        :param: workspace:
        The workspace for the build.

        :param: install_location:
        The loaded deploy configuration.
        """
        return ''

    def get_tear_down_script(self):
        """
        Generate scripting to inject after the user's postinstall script.
        """
        return ''

    def get_fpm_args(self, ws_paths):
        """
        Get the arguments (not options) to pass to fpm to build the package.
        Usually the paths to the source.

        :returns: A list of string arguments.
        """
        return os.listdir(ws_paths.package)


class Python(DeployType):
    """docstring for Python"""
    def __init__(self):
        super(Python, self).__init__(fpm_deploy_type='python',
                                     provides_version=True)

    def get_fpm_args(self, ws_paths):
        return os.path.join(ws_paths.repo, 'setup.py')


class VirtualEnv(DeployType):

    def __init__(self):
        super(VirtualEnv, self).__init__(dependencies=['python-virtualenv'])

    def get_set_up_script(self, workspace, deploy):
        install_venv = create_venv_paths(
            workspace.install_location, self._get_venv_name(deploy))
        frozen_requirements = os.path.join(
            workspace.install_location, '%s-requirements.pip' % deploy.name)

        return """# Create and activate the virtualenv
if [ ! -f {venv.python} ]; then
    /usr/bin/virtualenv {venv.venv}
fi
VENV={venv.venv}
source {venv.activate}

# Upgrade pip and re-install pip requirements
{venv.pip} install --upgrade pip
{venv.pip} install --upgrade -r {frozen_requirements}""".format(
            venv=install_venv, frozen_requirements=frozen_requirements)

    def _get_venv_name(self, deploy):
        if deploy.virtualenv_prefix is not None:
            # TODO: Strip '/' to avoid path shenanigans?
            return '%s-python' % deploy.virtualenv_prefix
        else:
            return 'python'

    def get_tear_down_script(self):
        return 'deactivate'
