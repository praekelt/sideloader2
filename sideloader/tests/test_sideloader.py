import os

from sideloader import Build, Deploy, GitRepo, Workspace
from sideloader.deploy_types import DeployType


class TestGitRepo(object):
    pass


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
    pass


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


class TestPackage(object):
    pass
