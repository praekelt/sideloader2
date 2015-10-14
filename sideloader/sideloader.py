import os
import shutil
import subprocess
import sys
import time
import yaml

from collections import namedtuple
from urlparse import urlparse


class Sideloader(object):

    debug = False
    deploy_file = '.deploy.yaml'
    _overrides = {}

    def __init__(self, config, repo, build):
        self.config = config
        self.repo = repo
        self.build = build

        # TODO: this, nicer
        if not repo.branch:
            repo.branch = config.default_branch

        self._init_build_paths()
        self.init_env()

    def _init_build_paths(self):
        """ Initialise all the paths in the workspace and build virtualenv. """
        # Default to the repo name if no workspace ID is configured
        workspace_id = (self.build.workspace_id
                        if self.build.workspace_id else self.repo.name)
        workspace_path = os.path.join(self.config.workspace_base, workspace_id)
        ws = {
            'workspace': workspace_path,
            'repo': os.path.join(workspace_path, self.repo.name),
            'build': os.path.join(workspace_path, 'build'),
            'package': os.path.join(workspace_path, 'package')
        }
        self.ws_paths = namedtuple('WsPaths', ws.keys())(**ws)

        self.build_venv = self.create_venv_paths(workspace_path)

    def create_venv_paths(self, root_path, venv_dir='ve'):
        """
        Creates a named tuple of virtualenv paths, given that a virtualenv is
        created in ``root_path/venv_dir``.
        """
        venv_path = os.path.join(root_path, venv_dir)
        venv_bin_path = os.path.join(venv_path, 'bin')
        venv = {
            'venv': venv_path,
            'bin': venv_bin_path,
            'activate': os.path.join(venv_bin_path, 'activate'),
            'pip': os.path.join(venv_bin_path, 'pip'),
            'python': os.path.join(venv_bin_path, 'python')
        }

        return namedtuple('VenvPaths', venv.keys())(**venv)

    def init_env(self):
        """ Initialises the current working environment. """
        env = {
            'VENV': self.build_venv.venv,
            'PIP': self.build_venv.pip,
            'REPO': self.repo.name,
            'BRANCH': self.repo.branch,
            'WORKSPACE': self.ws_paths.workspace,
            'BUILDDIR': self.ws_paths.build,
            'INSTALLDIR': self.config.install_location,
            'PATH': ':'.join([self.build_venv.bin, os.getenv('PATH')])
        }
        for k, v in env.items():
            os.putenv(k, v)

    def set_deploy_overrides(self, **kwargs):
        """ Override any parameters in the deploy file. """
        self._overrides = kwargs

    def _log(self, s):
        """ Log a timestamped message to stdout. """
        sys.stdout.write('[%s] %s\n' % (time.ctime(), s))
        sys.stdout.flush()

    def _args_str(self, args):
        """ Convert a list of arguments to a string. """
        if isinstance(args, list):
            return ' '.join(args)

        return str(args)

    def _cmd(self, args):
        """ Run the given command. """
        if self.debug:
            self._log(self._args_str(args))

        output = subprocess.check_output(args, shell=False)

        if self.debug:
            self._log(output)

        return output

    def create_workspace(self):
        """
        Cleans the current workspace, fetches the repo and sets up a virtualenv
        for the install.
        """
        self.set_up_directories()
        self.fetch_repo()

        self.deploy = self.load_deploy()

        if self.build.deploy_type == 'virtualenv':
            self.create_build_virtualenv()

        os.putenv('NAME', self.deploy.name)

    def set_up_directories(self):
        """
        Create the workspace directory if it doesn't exist or clean it out.
        Create the build directory.
        """
        if os.path.exists(self.ws_paths.workspace):
            self.clean_workspace()
        else:
            os.makedirs(self.ws_paths.workspace)

        os.makedirs(self.ws_paths.build)

    def clean_workspace(self):
        """ Clean up the workspace directory (but not the virtualenv). """
        self._rmtree_if_exists(self.ws_paths.repo)
        self._rmtree_if_exists(self.ws_paths.build)
        self._rmtree_if_exists(self.ws_paths.package)

    def _rmtree_if_exists(self, path):
        if os.path.exists(path):
            shutil.rmtree(path)
            return True
        return False

    def fetch_repo(self):
        """ Clone the repo and checkout the desired branch. """
        self._log('Fetching github repo')
        self._cmd(['git', 'clone', self.repo.url, self.ws_paths.repo])
        self._cmd(['git', '-C', self.ws_paths.repo, 'checkout',
                   self.repo.branch])

    def load_deploy(self):
        """
        Load the .deploy.yaml file in the repo or fallback to the default
        settings if one could not be found. Merge any overrides.
        """
        deploy_file_path = os.path.join(self.ws_paths.repo, self.deploy_file)
        if os.path.exists(deploy_file_path):
            deploy = Deploy.from_deploy_file(deploy_file_path)
        else:
            self._log('No deploy file found, continuing with defaults')
            deploy = Deploy()

        # If no name has been specified, use the repo name
        if not self._overrides.get('name') and not deploy.name:
            self._overrides['name'] = self.repo.name

        return deploy.override(**self._overrides)

    def create_build_virtualenv(self):
        """ Create a virtualenv for the build and install the dependencies. """
        self._log('Creating virtualenv')

        # Create clean virtualenv
        if not os.path.exists(self.build_venv.python):
            self._cmd(['virtualenv', self.build_venv.venv])

        self._log('Upgrading pip')
        self._cmd([self.build_venv.pip, 'install', '--upgrade', 'pip'])

        self._log('Installing pip dependencies')
        # Install things
        for dep in self.deploy.pip:
            self._log('Installing %s' % (dep))
            self._cmd([self.build_venv.pip, 'install', '--upgrade', dep])

    def create_package(self):
        """ Create the actual package. """
        self.copy_files()
        self.create_postinstall_script()
        self.build_package()

    def run_buildscript(self):
        """
        Run the buildscript for the project if one has been specified.
        """
        if not self.deploy.buildscript:
            return

        buildscript_path = os.path.join(self.ws_paths.repo,
                                        self.deploy.buildscript)
        self._cmd(['chmod', 'a+x', buildscript_path])

        # Push package directory before running build script
        old_cwd = os.getcwd()
        os.chdir(self.ws_paths.workspace)

        self._cmd([buildscript_path])

        # Pop directory
        os.chdir(old_cwd)

    def copy_files(self):
        """ Copy the build and nginx/supervisor config files. """
        self._log('Preparing package')
        os.makedirs(self.ws_paths.package)

        self.copy_build()
        self.copy_nginx_configs()
        self.copy_supervisor_configs()

    def copy_build(self):
        """ Copy build contents to install location. """
        dest_path = os.path.join(self.ws_paths.package,
                                 self.config.install_location.lstrip('/'))
        os.makedirs(dest_path)

        for directory in os.listdir(self.ws_paths.build):
            try:
                shutil.copytree(os.path.join(self.ws_paths.build, directory),
                                os.path.join(dest_path, directory))
            except Exception as e:
                self._log('ERROR: Could not copy %s to package: %s %s' % (
                    directory, type(e), e))
                self.fail_build('Error copying files to package')

        if self.build.deploy_type == 'virtualenv':
            self._freeze_virtualenv(dest_path)

    def _freeze_virtualenv(self, dest_path):
        """ Freeze post build requirements. """
        requirements_path = os.path.join(
            dest_path, '%s-requirements.pip' % self.deploy.name)
        self._cmd([self.build_venv.pip, 'freeze', '>', requirements_path])

    def copy_nginx_configs(self):
        """ Copy any nginx configs into etc/nginx/sites-enabled. """
        if not self.deploy.nginx:
            return

        nginx_path = os.path.join(self.ws_paths.package,
                                  'etc', 'nginx', 'sites-enabled')
        os.makedirs(nginx_path)
        for conf in self.deploy.nginx:
            shutil.copy(os.path.join(self.ws_paths.build, conf), nginx_path)

    def copy_supervisor_configs(self):
        """ Copy any supervisor configs into etc/supervisor/conf.d. """
        if not self.deploy.supervisor:
            return

        supervisor_path = os.path.join(self.ws_paths.package,
                                       'etc', 'supervisor', 'conf.d')
        os.makedirs(supervisor_path)
        for conf in self.deploy.supervisor:
            shutil.copy(os.path.join(self.ws_paths.build, conf),
                        supervisor_path)

    def create_postinstall_script(self):
        """ Generate the postinstall script and write it to disk. """
        content = self.generate_postinstall_script()
        if self.debug:
            self._log(content)

        self.write_postinstall_script(content)

    def generate_postinstall_script(self):
        """ Generate the contents of the postinstall script. """
        self._log('Constructing postinstall script')

        # Insert some scripting before the user's script to set up...
        set_up = ''
        if self.build.deploy_type == 'virtualenv':
            set_up = self.generate_virtualenv_set_up()

        # ...and afterwards to tear down.
        tear_down = ''
        if self.build.deploy_type == 'virtualenv':
            tear_down = 'deactivate'

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
            installdir=self.config.install_location,
            repo=self.repo.name,
            branch=self.repo.branch,
            name=self.deploy.name,
            user_postinstall=user_postinstall)

    def generate_virtualenv_set_up(self):
        """ Generate the set up scripting for virtualenv deployments. """
        install_venv = self._create_install_venv_paths()
        return """# Create and activate the virtualenv
if [ ! -f {venv.python} ]; then
    /usr/bin/virtualenv {venv.venv}
fi
VENV={venv.venv}
source {venv.activate}

# Upgrade pip and re-install pip requirements
{venv.pip} install --upgrade pip
{venv.pip} install --upgrade -r {name}-requirements.pip""".format(
            venv=install_venv, name=self.deploy.name)

    def _create_install_venv_paths(self):
        # Paths for post-install time
        if self.deploy.virtualenv_prefix is not None:
            # TODO: Strip '/' to avoid path shenanigans?
            venv_dir = '%s-python' % self.deploy.virtualenv_prefix
        else:
            venv_dir = 'python'

        return self.create_venv_paths(self.config.install_location, venv_dir)

    def read_postinstall_file(self):
        """ Read the user's postinstall file. """
        postinstall_path = os.path.join(self.ws_paths.repo,
                                        self.deploy.postinstall)
        with open(postinstall_path) as postinstall_file:
            return postinstall_file.read()

    def write_postinstall_script(self, content):
        """ Write the final postinstall script. """
        postinstall_path = os.path.join(self.ws_paths.workspace,
                                        'postinstall.sh')
        with open(postinstall_path, 'w') as postinstall_file:
            postinstall_file.write(content)
        os.chmod(postinstall_path, 0777)

    def build_package(self):
        """ Run the fpm command that builds the package. """
        # Preserving behaviour... prefer the deploy file version
        version = self.deploy.version

        if self.build.deploy_type == 'virtualenv':
            deploy_type = 'dir'
            prefix = '/'
            args = os.listdir(self.ws_paths.package)
        elif self.build.deploy_type == 'python':
            deploy_type = 'python'
            args = [os.path.join(self.ws_paths.repo, 'setup.py')]
            version = None  # Get the version from setup.py
        else:
            deploy_type = 'dir'
            prefix = '/'
            args = os.listdir(self.ws_paths.package)

        self._log('Building .%s package' % self.build.package_target)

        postinstall_path = os.path.join(self.ws_paths.workspace,
                                        'postinstall.sh')
        fpm = [
            'fpm',
            '-C', self.ws_paths.package,
            '-p', self.ws_paths.package,
            '-s', deploy_type,
            '-t', self.build.package_target,
            '-a', 'amd64',
            '-n', self.deploy.name,
            '-v', version,
            '--after-install', postinstall_path,
        ]

        if prefix:
            fpm += ['--prefix', prefix]

        if self.deploy.dependencies:
            fpm += sum([['-d', dep] for dep in self.deploy.dependencies], [])

        if self.deploy.user:
            fpm += ['--%s-user' % self.build.package_target, self.deploy.user]

        if self.debug:
            fpm.append('--debug')

        fpm += args

        self._cmd(fpm)

        if self.build.package_target == 'deb':
            self.sign_debs()

        self._log('Build completed successfully')

    def sign_debs(self):
        """ Sign the .deb file with the configured gpg key. """
        if not self.config.gpg_key:
            self._log('No GPG key configured, skipping signing')
        self._log('Signing package')
        # Find all the .debs in the directory and indiscriminately sign them
        # (there should only be 1)
        # TODO: Get the actual package name from fpm
        debs = [os.path.join(self.ws_paths.package, f)
                for f in os.listdir(self.ws_paths.package)
                if f.endswith('.deb')]
        for deb in debs:
            self._cmd(['dpkg-sig', '-k', self.config.gpg_key, '--sign',
                       'builder', deb])


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
    def __init__(self, name=None, buildscript=None, postinstall=None, nginx=[],
                 supervisor=[], pip=[], dependencies=[],
                 virtualenv_prefix=None, allow_broken_build=False, user=None,
                 version=None):
        """
        Container class for deploy prefernces, typically loaded from the
        project's '.deploy.yaml' file.
        """
        self.name = name
        self.buildscript = buildscript
        self.postinstall = postinstall
        self.nginx = nginx
        self.supervisor = supervisor
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

        return Deploy(
            deploy_yaml.get('name'),
            deploy_yaml.get('buildscript'),
            deploy_yaml.get('postinstall'),
            deploy_yaml.get('nginx', []),
            deploy_yaml.get('supervisor', []),
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
        attrs = ['name', 'buildscript', 'postinstall', 'nginx', 'supervisor',
                 'pip', 'dependencies', 'virtualenv_prefix',
                 'allow_broken_build', 'user', 'version']
        kwargs = {}
        for attr in attrs:
            kwargs[attr] = getattr(self, attr)
            if attr in overrides:
                value = overrides[attr]
                if value:
                    kwargs[attr] = value

        return Deploy(**kwargs)


class Build(object):
    """ Container class for the build settings. """
    def __init__(self, workspace_id, deploy_type, package_target):
        self.workspace_id = workspace_id
        self.deploy_type = deploy_type
        self.package_target = package_target
