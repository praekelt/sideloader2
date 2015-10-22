import os

import pytest

from sideloader import Build, Deploy, GitRepo, Package, Workspace
from sideloader.deploy_types import DeployType


class TestGitRepo(object):
    def test_from_github_url(self):
        repo = GitRepo.from_github_url(
            'https://github.com/praekelt/sideloader2.git', 'develop')

        assert repo.url == 'https://github.com/praekelt/sideloader2.git'
        assert repo.name == 'sideloader2'
        assert repo.branch == 'develop'


class CommandLineTest(object):
    def setup_method(self, test_method):
        self.cmds = []

    def cmd(self, args, *_args, **kwargs):
        self.cmds.append(args)

    def prefix_cwd(self, path):
        return '%s/%s' % (os.getcwd(), path)


class TestWorkspace(CommandLineTest):
    def setup_method(self, test_method):
        super(TestWorkspace, self).setup_method(test_method)

        repo = GitRepo('https://github.com/praekelt/sideloader2.git',
                       'develop', 'sideloader2')
        self.workspace = Workspace('test_id', 'test_base', '/opt', repo)
        self.workspace._cmd = self.cmd

    def test_get_path(self):
        """
        Getting a path in the workspace directory returns the correct path.
        """
        assert (self.workspace.get_path('test') ==
                self.prefix_cwd('test_base/test_id/test'))

    def test_get_package_path(self):
        """
        Getting a path in the package directory returns the correct path.
        """
        assert (self.workspace.get_package_path('test') ==
                self.prefix_cwd('test_base/test_id/package/test'))

    def test_get_build_path(self):
        """
        Getting a path in the build directory returns the correct path.
        """
        assert (self.workspace.get_build_path('test') ==
                self.prefix_cwd('test_base/test_id/build/test'))

    def test_get_repo_path(self):
        """
        Getting a path in the repo directory returns the correct path.
        """
        assert (self.workspace.get_repo_path('test') ==
                self.prefix_cwd('test_base/test_id/sideloader2/test'))

    def test_get_install_path(self):
        """
        Getting a path in the install directory returns the correct path.
        """
        assert (self.workspace.get_install_path('test') ==
                self.prefix_cwd('test_base/test_id/package/opt/test'))

    def test_fetch_repo(self):
        """
        When the repo is fetched in the workspace, git is called with the
        correct commands.
        """
        self.workspace.fetch_repo()

        assert len(self.cmds) == 2

        assert (
            self.cmds[0] ==
            ['git', 'clone', 'https://github.com/praekelt/sideloader2.git',
             self.prefix_cwd('test_base/test_id/sideloader2')]
        )

        assert (
            self.cmds[1] ==
            ['git', '-C', self.prefix_cwd('test_base/test_id/sideloader2'),
             'checkout', 'develop']
        )


class TestDeploy(object):
    def setup_method(self, test_method):
        self.deploy = Deploy(
            name='test', buildscript='scripts/build.sh',
            postinstall='scripts/postinst.sh', config_files=[],
            pip=['requests'], dependencies=['g++'], virtualenv_prefix='test',
            allow_broken_build=False, user='ubuntu', version='1.0')

    def test_override(self):
        """
        When a Deploy is overridden, a new Deploy object is returned with the
        overridden fields set with the new values while the other fields
        remain the same.
        """
        overridden = self.deploy.override(name='name',
                                          pip=['django', 'pytest'])

        # Check that the new values are present
        assert overridden.name == 'name'
        assert overridden.pip == ['django', 'pytest']

        # Check that the old values for the other fields remain
        assert overridden.buildscript == 'scripts/build.sh'
        assert overridden.postinstall == 'scripts/postinst.sh'
        assert overridden.config_files == []
        assert overridden.dependencies == ['g++']
        assert overridden.virtualenv_prefix == 'test'
        assert not overridden.allow_broken_build
        assert overridden.user == 'ubuntu'
        assert overridden.version == '1.0'

    def test_override_unknown_attribute_fails(self):
        """
        Overriding fields that don't exist in the deploy should throw an
        exception.
        """
        with pytest.raises(ValueError) as error:
            self.deploy.override(blah='blah')

        assert (error.value.message ==
                'Deploy has no attribute \'blah\'')


class TestBuild(CommandLineTest):
    def setup_method(self, test_method):
        """
        Create the Build and a backing workspace.
        """
        super(TestBuild, self).setup_method(test_method)

        repo = GitRepo('https://github.com/praekelt/sideloader2.git',
                       'develop', 'sideloader2')
        workspace = Workspace('test_id', 'test_base', '/opt', repo)
        deploy = Deploy(name='test_deploy', pip=['django', 'pytest'])
        deploy_type = DeployType()

        self.build = Build(workspace, deploy, deploy_type)
        self.build._cmd = self.cmd

    def test_create_build_virtualenv(self):
        """
        When creating a build virtualenv, the virtualenv directory is created,
        pip is upgraded, and the pip dependencies from the Deploy are
        installed.
        """
        self.build.create_build_virtualenv()

        assert len(self.cmds) == 4
        assert (
            self.cmds[0] ==
            ['virtualenv', self.prefix_cwd('test_base/test_id/ve')]
        )

        assert (
            self.cmds[1] ==
            [self.prefix_cwd('test_base/test_id/ve/bin/pip'), 'install',
             '--upgrade', 'pip']
        )

        assert (
            self.cmds[2] ==
            [self.prefix_cwd('test_base/test_id/ve/bin/pip'), 'install',
             '--upgrade', 'django']
        )

        assert (
            self.cmds[3] ==
            [self.prefix_cwd('test_base/test_id/ve/bin/pip'), 'install',
             '--upgrade', 'pytest']
        )

    def test_put_env_variables(self):
        """
        When placing the enviornment variables, all the variables are set
        correctly.
        """
        self.build.put_env_variables()

        assert os.getenv('VENV') == self.prefix_cwd('test_base/test_id/ve')
        assert (os.getenv('PIP') ==
                self.prefix_cwd('test_base/test_id/ve/bin/pip'))
        assert os.getenv('REPO') == 'sideloader2'
        assert os.getenv('BRANCH') == 'develop'
        assert os.getenv('WORKSPACE') == self.prefix_cwd('test_base/test_id')
        assert (os.getenv('BUILDDIR') ==
                self.prefix_cwd('test_base/test_id/build'))
        assert (os.getenv('INSTALLDIR') ==
                self.prefix_cwd('test_base/test_id/package/opt'))
        assert os.getenv('NAME') == 'test_deploy'

    def test_put_env_variables_path(self):
        """
        When placing the environment variables, PATH is prefixed with the
        virtualenv executables (bin) directory.
        """
        self.build.put_env_variables()

        assert os.getenv('PATH').startswith(
            self.prefix_cwd('test_base/test_id/ve/bin'))


class TestPackage(CommandLineTest):

    def _create_package(self, tmpdir):
        repo = GitRepo('https://github.com/praekelt/sideloader2.git',
                       'develop', 'sideloader2')

        # Set up the workspace
        workspace = Workspace('test_id', str(tmpdir), '/opt', repo)
        workspace.create_clean_workspace()
        workspace.make_package_dir()

        deploy = Deploy(name='test_deploy', pip=['django', 'pytest'],
                        version='1.0', user='ubuntu')
        deploy_type = DeployType()

        package = Package(workspace, deploy, deploy_type)
        package._cmd = self.cmd
        return package

    def test_run_fpm(self, tmpdir):
        """
        When running the fpm package command, the command is properly
        constructed.
        """
        package = self._create_package(tmpdir)

        # Create some fake project files
        open(package.workspace.get_package_path('my-file1.txt'), 'a').close()
        open(package.workspace.get_package_path('my-file2.txt'), 'a').close()

        package.run_fpm()

        assert (
            self.cmds[0] == [
                'fpm',
                '-C', str(tmpdir) + '/test_id/package',
                '-p', str(tmpdir) + '/test_id/package',
                '-s', 'dir',
                '-t', 'deb',
                '-a', 'amd64',
                '-n', 'test_deploy',
                '--after-install', str(tmpdir) + '/test_id/postinstall.sh',
                '-v', '1.0',
                '--deb-user', 'ubuntu',
                'my-file1.txt', 'my-file2.txt'
            ]
        )

    def test_sign_debs(self, tmpdir):
        """
        When signing .deb files, only the .deb files in the package directory
        should be signed.
        """
        package = self._create_package(tmpdir)

        # Create a fake .deb and another random file
        open(package.workspace.get_package_path('my-deb.deb'), 'a').close()
        open(package.workspace.get_package_path('my-file2.txt'), 'a').close()

        package.gpg_key = 'GPGKEY23'
        package.sign_debs()

        assert (
            self.cmds[0] == [
                'dpkg-sig',
                '-k', 'GPGKEY23',
                '--sign', 'builder',
                str(tmpdir) + '/test_id/package/my-deb.deb'
            ]
        )

    def test_sign_debs_skipped_if_no_gpg_key(self, tmpdir):
        """
        When trying to sign the .deb files and no GPG key has been configured
        for the Package, signing should be skipped.
        """
        package = self._create_package(tmpdir)

        # Create a fake .deb and another random file
        open(package.workspace.get_package_path('my-deb.deb'), 'a').close()
        open(package.workspace.get_package_path('my-file2.txt'), 'a').close()

        package.sign_debs()

        assert len(self.cmds) == 0
