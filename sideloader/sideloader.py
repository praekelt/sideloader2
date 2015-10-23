import os
import shutil
import yaml

from collections import namedtuple
from urlparse import urlparse

import deploy_types

from config_files import ConfigFiles
from utils import cmd, create_venv_paths, listdir_abs, log, rmtree_if_exists


class Workspace(object):
    """
    Keeps track of the various file paths in the workspace and downloads the
    source from github.
    """

    debug = False
    _cmd = lambda self, *args, **kwargs: cmd(*args, debug=self.debug, **kwargs)

    def __init__(self, workspace_id, workspace_base, install_location, repo):
        self.install_location = install_location
        self.repo = repo

        self._init_paths(workspace_id, workspace_base, install_location)

    def _init_paths(self, workspace_id, workspace_base, install_location):
        """ Initialise the paths to various directories in the workspace. """
        self._dir = os.path.abspath(os.path.join(workspace_base, workspace_id))

        package_path = os.path.join(self._dir, 'package')
        dirs = {
            'repo': os.path.join(self._dir, self.repo.name),
            'build': os.path.join(self._dir, 'build'),
            'package': package_path,
            'install': os.path.join(package_path,
                                    install_location.lstrip('/'))
        }
        self._dirs = namedtuple('WorkspaceDirs', dirs.keys())(**dirs)

    def set_up(self):
        """
        Create the workspace and fetch the repo.
        """
        self.create_clean_workspace()
        self.fetch_repo()

    def create_clean_workspace(self):
        """
        Create the workspace directory if it doesn't exist or clean it out.
        """
        if os.path.exists(self._dir):
            self.clean_workspace()
        else:
            os.makedirs(self._dir)

    def clean_workspace(self):
        """ Clean up the workspace directory (but not the virtualenv). """
        for path in self._dirs:
            rmtree_if_exists(path)

    def fetch_repo(self):
        """ Clone the repo and checkout the desired branch. """
        log('Fetching github repo')
        self._cmd(['git', 'clone', self.repo.url, self._dirs.repo])
        self._cmd(['git', '-C', self._dirs.repo, 'checkout', self.repo.branch])

    def load_deploy(self, deploy_file='.deploy.yaml'):
        """
        Load the .deploy.yaml file in the repo or fallback to the default
        settings if one could not be found. Merge any overrides.
        """
        if not os.path.exists(self._dirs.repo):
            log('WARNING: Repo directory not found. Has it been fetched yet?')

        deploy_file_path = self.get_repo_path(deploy_file)
        if os.path.exists(deploy_file_path):
            return Deploy.from_deploy_file(deploy_file_path)
        else:
            log('No deploy file found, continuing with defaults')
            return Deploy()

    def make_build_dir(self):
        """
        Create the build directory (the workspace directory should already
        exist).
        """
        os.mkdir(self._dirs.build)

    def make_package_dir(self):
        """
        Create the package directory (the workspace directory should already
        exist).
        """
        os.mkdir(self._dirs.package)

    def make_install_dir(self):
        """
        Create the install directory (the package directory should already
        exist).
        """
        package_relpath = os.path.relpath(self._dirs.install,
                                          self._dirs.package)
        parts = package_relpath.split(os.sep)
        subpath = self._dirs.package
        for part in parts:
            subpath = os.path.join(subpath, part)
            os.mkdir(subpath)

    def get_path(self, *paths):
        """ Get a path within the workspace directory. """
        return os.path.join(self._dir, *paths)

    def get_package_path(self, *paths):
        """ Get a path within the package directory. """
        return os.path.join(self._dirs.package, *paths)

    def get_build_path(self, *paths):
        """ Get a path within the build directory. """
        return os.path.join(self._dirs.build, *paths)

    def get_repo_path(self, *paths):
        """ Get a path within the repo directory. """
        return os.path.join(self._dirs.repo, *paths)

    def get_install_path(self, *paths):
        """ Get a path within the install directory. """
        return os.path.join(self._dirs.install, *paths)


class Build(object):

    debug = False
    _cmd = lambda self, *args, **kwargs: cmd(*args, debug=self.debug, **kwargs)

    def __init__(self, workspace, deploy, deploy_type):
        """
        :param: workspace:
        The workspace to build in.

        :param: deploy:
        The definition of the deployment as loaded from the project's deploy
        file.

        :param: deploy_type:
        The deploy type object describing the type of the deploy.
        """
        self.workspace = workspace
        self.deploy = deploy
        self.deploy_type = deploy_type

        self.venv_paths = create_venv_paths(workspace.get_path())

    def build(self):
        """
        Build the workspace. Gets everything into a state that is ready for
        packaging.
        """
        self.prepare_environment()
        self.run_buildscript()
        self.copy_files()
        self.freeze_virtualenv()
        self.create_postinstall_script()

    def prepare_environment(self):
        """
        Prepare the workspace so that everything is ready to run the
        buildscript including the virtualenv, build directory, and environment
        variables.
        """
        self.create_build_virtualenv()
        self.workspace.make_build_dir()
        self.put_env_variables()

    def create_build_virtualenv(self):
        """ Create a virtualenv for the build and install the dependencies. """
        log('Creating virtualenv')

        # Create clean virtualenv
        if not os.path.exists(self.venv_paths.python):
            self._cmd(['virtualenv', self.venv_paths.venv])

        log('Upgrading pip')
        self._cmd([self.venv_paths.pip, 'install', '--upgrade', 'pip'])

        log('Installing pip dependencies')
        # Install things
        for dep in self.deploy.pip:
            log('Installing %s' % (dep))
            self._cmd([self.venv_paths.pip, 'install', '--upgrade', dep])

    def put_env_variables(self):
        """ Initialises the current working environment. """
        env = {
            'VENV': self.venv_paths.venv,
            'PIP': self.venv_paths.pip,
            'REPO': self.workspace.repo.name,
            'BRANCH': self.workspace.repo.branch,
            'WORKSPACE': self.workspace.get_path(),
            'BUILDDIR': self.workspace.get_build_path(),
            'INSTALLDIR': self.workspace.get_install_path(),
            'NAME': self.deploy.name,
            'PATH': ':'.join([self.venv_paths.bin, os.getenv('PATH')])
        }
        for k, v in env.items():
            os.environ[k] = v

    def run_buildscript(self):
        """
        Run the buildscript for the project if one has been specified.
        """
        if not self.deploy.buildscript:
            return

        buildscript_path = self.workspace.get_repo_path(
            self.deploy.buildscript)
        self._cmd(['chmod', 'a+x', buildscript_path])

        # Push package directory before running build script
        old_cwd = os.getcwd()
        os.chdir(self.workspace.get_path())

        self._cmd([buildscript_path])

        # Pop directory
        os.chdir(old_cwd)

    def copy_files(self):
        """ Copy the build and nginx/supervisor config files. """
        log('Preparing package')
        self.workspace.make_package_dir()

        self.copy_build()
        self.copy_config_files()

    def copy_build(self):
        """ Copy build contents to install location. """
        self.workspace.make_install_dir()

        for directory in os.listdir(self.workspace.get_build_path()):
            shutil.copytree(self.workspace.get_build_path(directory),
                            self.workspace.get_install_path(directory))

    def copy_config_files(self):
        """
        Copy the config files specified in the deploy over to the relevant
        config directory within the package.
        """
        for config_files in self.deploy.config_files:
            config_dir_path = self.workspace.get_package_path(
                config_files.config_dir_path)
            os.makedirs(config_dir_path)

            for config_file in config_files.files:
                shutil.copy(self.workspace.get_build_path(config_file),
                            config_dir_path)

    def freeze_virtualenv(self):
        """ Freeze post build requirements. """
        freeze_output = self._cmd([self.venv_paths.pip, 'freeze'])

        requirements_path = self.workspace.get_install_path(
            '%s-requirements.pip' % self.deploy.name)
        with open(requirements_path, 'w') as requirements_file:
            requirements_file.write(freeze_output)

    def create_postinstall_script(self):
        """ Generate the postinstall script and write it to disk. """
        content = self.generate_postinstall_script()
        if self.debug:
            log(content)

        self.write_postinstall_script(content)

    def generate_postinstall_script(self):
        """ Generate the contents of the postinstall script. """
        log('Constructing postinstall script')

        # Insert some scripting before the user's script to set up...
        set_up = self.deploy_type.get_set_up_script(
            self.workspace, self.deploy)

        # ...and afterwards to tear down.
        tear_down = self.deploy_type.get_tear_down_script()

        user_postinstall = ''
        if self.deploy.postinstall:
            user_postinstall = self.read_postinstall_file()

        return """#!/bin/bash

{set_up}

INSTALLDIR={installdir}
REPO={repo}
BRANCH={branch}
NAME={name}

{user_postinstall}

{tear_down}
""".format(
            set_up=set_up,
            tear_down=tear_down,
            installdir=self.workspace.get_install_path(),
            repo=self.workspace.repo.name,
            branch=self.workspace.repo.branch,
            name=self.deploy.name,
            user_postinstall=user_postinstall)

    def read_postinstall_file(self):
        """ Read the user's postinstall file. """
        postinstall_path = self.workspace.get_repo_path(
            self.deploy.postinstall)
        with open(postinstall_path) as postinstall_file:
            return postinstall_file.read()

    def write_postinstall_script(self, content):
        """ Write the final postinstall script. """
        postinstall_path = self.workspace.get_path('postinstall.sh')
        with open(postinstall_path, 'w') as postinstall_file:
            postinstall_file.write(content)
        os.chmod(postinstall_path, 0755)


class Package(object):

    debug = False
    sign = True
    _cmd = lambda self, *args, **kwargs: cmd(*args, debug=self.debug, **kwargs)

    def __init__(self, workspace, deploy, deploy_type, target='deb',
                 gpg_key=None):
        self.workspace = workspace
        self.deploy = deploy
        self.deploy_type = deploy_type
        self.target = target
        self.gpg_key = gpg_key

    def package(self):
        self.run_fpm()
        self.sign_debs()

    def run_fpm(self):
        """ Run the fpm command that builds the package. """
        log('Building .%s package' % self.target)

        fpm = [
            'fpm',
            '-C', self.workspace.get_package_path(),
            '-p', self.workspace.get_package_path(),
            '-s', self.deploy_type.fpm_deploy_type,
            '-t', self.target,
            '-a', 'amd64',
            '-n', self.deploy.name,
            '--after-install', self.workspace.get_path('postinstall.sh'),
        ]

        if not self.deploy_type.provides_version:
            fpm += ['-v', self.deploy.version]

        fpm += sum([['-d', dep] for dep in self.list_all_dependencies()], [])

        if self.deploy.user:
            fpm += ['--%s-user' % self.target, self.deploy.user]

        if self.debug:
            fpm.append('--debug')

        fpm += self.deploy_type.get_fpm_args(self.workspace._dirs)

        self._cmd(fpm)

        log('Build completed successfully')

    def list_all_dependencies(self):
        """ Get a list of all the package dependencies. """
        deps = []
        # Dependencies defined in the deploy file
        deps += self.deploy.dependencies

        # Dependencies from the deployment type
        deps += self.deploy_type.dependencies

        # Dependencies from the config files
        for config_files in self.deploy.config_files:
            deps += config_files.dependencies

        return deps

    def sign_debs(self):
        """ Sign the .deb file with the configured gpg key. """
        if self.gpg_key is None:
            log('No GPG key configured, skipping signing')
            return
        log('Signing package')
        # Find all the .debs in the directory and indiscriminately sign them
        # (there should only be 1)
        # TODO: Get the actual package name from fpm
        debs = [path for path in listdir_abs(self.workspace.get_package_path())
                if os.path.splitext(path)[1] == '.deb']
        for deb in debs:
            self._cmd(
                ['dpkg-sig', '-k', self.gpg_key, '--sign', 'builder', deb])


class Sideloader(object):

    def __init__(self, config_path, github_url, branch=None, workspace_id=None,
                 debug=False):
        self.config = Config.from_config_file(config_path)
        self.repo = self._create_git_repo(github_url, branch)
        self.workspace_id = (workspace_id if workspace_id is not None
                             else self.repo.name)
        self.debug = debug

    def _create_git_repo(self, github_url, branch):
        branch = branch if branch is not None else self.config.default_branch
        return GitRepo.from_github_url(github_url, branch)

    def run(self, deploy_file='.deploy.yaml', dtype='virtualenv', target='deb',
            build_num=None, sign=True, **deploy_overrides):
        workspace = self._create_workspace()
        workspace.set_up()

        deploy = self._load_deploy(workspace, deploy_file, build_num,
                                   **deploy_overrides)
        deploy_type = self._get_deploy_type(dtype)

        build = self._create_build(workspace, deploy, deploy_type)
        build.build()

        package = self._create_package(workspace, deploy, deploy_type, target,
                                       sign)
        package.package()

    def _create_workspace(self):
        workspace = Workspace(self.workspace_id, self.config.workspace_base,
                              self.config.install_location, self.repo)
        workspace.debug = self.debug
        return workspace

    def _load_deploy(self, workspace, deploy_file, build_num,
                     **deploy_overrides):
        if 'version' not in deploy_overrides:
            if build_num is None:
                build_num = 1
            deploy_overrides['version'] = '0.%s' % build_num

        deploy = workspace.load_deploy(deploy_file)
        deploy = deploy.override(**deploy_overrides)
        return deploy

    def _get_deploy_type(self, deploy_type_str):
        if deploy_type_str == 'python':
            return deploy_types.Python()
        elif deploy_type_str == 'virtualenv':
            return deploy_types.VirtualEnv()

        return deploy_types.DeployType()

    def _create_build(self, workspace, deploy, deploy_type):
        build = Build(workspace, deploy, deploy_type)
        build.debug = self.debug

        return build

    def _create_package(self, workspace, deploy, deploy_type, target, sign):
        package = Package(workspace, deploy, deploy_type, target,
                          self.config.gpg_key)
        package.sign = sign
        package.debug = self.debug

        return package


class Config(object):
    """
    Container class for Sideloader config, typically loaded from 'config.yaml'.
    """
    def __init__(self, install_location, default_branch, workspace_base,
                 gpg_key):
        self.install_location = install_location
        self.default_branch = default_branch
        self.workspace_base = workspace_base
        self.gpg_key = gpg_key

    @classmethod
    def from_config_file(cls, config_file_path):
        with open(config_file_path) as config_file:
            config_yaml = yaml.load(config_file)

        return Config(
            config_yaml['install_location'],
            config_yaml.get('default_branch', 'develop'),
            config_yaml.get('workspace_base', '/workspace'),
            config_yaml.get('gpg_key')
        )


class GitRepo(object):
    def __init__(self, url, branch, name):
        self.url = url
        self.branch = branch
        self.name = name

    @classmethod
    def from_github_url(cls, github_url, branch):
        parse_result = urlparse(github_url)
        path_segments = parse_result.path.strip('/').split('/')

        name = path_segments[1].rstrip('.git')

        return GitRepo(github_url, branch, name)


class Deploy(object):
    def __init__(self, name=None, buildscript=None, postinstall=None,
                 config_files=[], pip=[], dependencies=[],
                 virtualenv_prefix=None, allow_broken_build=False, user=None,
                 version=None):
        """
        Container class for deploy prefernces, typically loaded from the
        project's '.deploy.yaml' file.
        """
        self.name = name
        self.buildscript = buildscript
        self.postinstall = postinstall
        self.config_files = config_files
        self.pip = pip
        self.dependencies = dependencies
        self.virtualenv_prefix = virtualenv_prefix
        self.allow_broken_build = allow_broken_build
        self.user = user
        self.version = version

    @classmethod
    def from_deploy_file(cls, deploy_file_path):
        with open(deploy_file_path) as deploy_file:
            deploy_yaml = yaml.load(deploy_file)

        config_files = []
        nginx_files = deploy_yaml.get('nginx')
        if nginx_files:
            config_files.append(ConfigFiles.nginx(nginx_files))

        supervisor_files = deploy_yaml.get('supervisor')
        if supervisor_files:
            config_files.append(ConfigFiles.supervisor(supervisor_files))

        return Deploy(
            deploy_yaml.get('name'),
            deploy_yaml.get('buildscript'),
            deploy_yaml.get('postinstall'),
            config_files,
            deploy_yaml.get('pip', []),
            deploy_yaml.get('dependencies'),
            deploy_yaml.get('virtualenv_prefix'),
            deploy_yaml.get('allow_broken_build', False),
            deploy_yaml.get('user'),
            deploy_yaml.get('version')
        )

    def override(self, **overrides):
        """
        Override attributes in this Deploy instance and return a new instance
        with the values given. Overrides with a None value will be ignored.
        """
        attrs = ['name', 'buildscript', 'postinstall', 'config_files', 'pip',
                 'dependencies', 'virtualenv_prefix', 'allow_broken_build',
                 'user', 'version']
        for override in overrides.keys():
            if override not in attrs:
                raise ValueError('Deploy has no attribute \'%s\'' % override)
        kwargs = {}
        for attr in attrs:
            kwargs[attr] = getattr(self, attr)
            if attr in overrides:
                value = overrides[attr]
                if value is not None:
                    kwargs[attr] = value

        return Deploy(**kwargs)
