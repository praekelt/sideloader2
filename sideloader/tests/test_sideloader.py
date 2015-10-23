import os

import pytest

from sideloader import Build, Deploy, GitRepo, Package, Workspace
from sideloader.config_files import ConfigFiles
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


class TestWorkspace(CommandLineTest):

    def _create_workspace(self, tmpdir):
        repo = GitRepo('https://github.com/praekelt/sideloader2.git',
                       'develop', 'sideloader2')

        workspace = Workspace('test_id', str(tmpdir), '/var/praekelt', repo)
        workspace._cmd = self.cmd
        return workspace

    def test_get_path(self, tmpdir):
        """
        Getting a path in the workspace directory returns the correct path.
        """
        workspace = self._create_workspace(tmpdir)
        assert (workspace.get_path('test') ==
                str(tmpdir) + '/test_id/test')

    def test_get_package_path(self, tmpdir):
        """
        Getting a path in the package directory returns the correct path.
        """
        workspace = self._create_workspace(tmpdir)
        assert (workspace.get_package_path('test') ==
                str(tmpdir) + '/test_id/package/test')

    def test_get_build_path(self, tmpdir):
        """
        Getting a path in the build directory returns the correct path.
        """
        workspace = self._create_workspace(tmpdir)
        assert (workspace.get_build_path('test') ==
                str(tmpdir) + '/test_id/build/test')

    def test_get_repo_path(self, tmpdir):
        """
        Getting a path in the repo directory returns the correct path.
        """
        workspace = self._create_workspace(tmpdir)
        assert (workspace.get_repo_path('test') ==
                str(tmpdir) + '/test_id/sideloader2/test')

    def test_get_install_path(self, tmpdir):
        """
        Getting a path in the install directory returns the correct path.
        """
        workspace = self._create_workspace(tmpdir)
        assert (workspace.get_install_path('test') ==
                str(tmpdir) + '/test_id/package/var/praekelt/test')

    def test_create_clean_workspace_creates_dir(self, tmpdir):
        """
        When a new clean workspace is created, an empty workspace directory
        is created.
        """
        workspace = self._create_workspace(tmpdir)
        workspace.create_clean_workspace()

        ws_dir = tmpdir.join('test_id')

        assert ws_dir.check()
        assert ws_dir.listdir() == []

    def test_create_clean_workspace_cleans_dir(self, tmpdir):
        """
        When a workspace is cleaned, the build, package and repo directories
        should be deleted. Other files should remain.
        """
        workspace = self._create_workspace(tmpdir)

        # Create some mess
        ws_dir = tmpdir.mkdir('test_id')
        package_dir = ws_dir.mkdir('package')
        build_dir = ws_dir.mkdir('build')
        repo_dir = ws_dir.mkdir('sideloader2')
        other_file = ws_dir.ensure('test-file')

        workspace.create_clean_workspace()

        # The workspace still exists
        assert ws_dir.check()

        # The package, build and repo directories are deleted
        assert not package_dir.check()
        assert not build_dir.check()
        assert not repo_dir.check()

        # Other files are not deleted
        assert other_file.check()

    def test_make_build_dir(self, tmpdir):
        """
        When the build directory is made, the directory exists.
        """
        workspace = self._create_workspace(tmpdir)
        workspace.create_clean_workspace()

        workspace.make_build_dir()

        assert tmpdir.join('test_id', 'build').check()

    def test_make_package_dir(self, tmpdir):
        """
        When the package directory is made, the directory exists.
        """
        workspace = self._create_workspace(tmpdir)
        workspace.create_clean_workspace()

        workspace.make_package_dir()

        assert tmpdir.join('test_id', 'package').check()

    def test_make_install_dir(self, tmpdir):
        """
        When the install directory is made (after creating the package
        directory), the directory exists.
        """
        workspace = self._create_workspace(tmpdir)
        workspace.create_clean_workspace()
        workspace.make_package_dir()

        workspace.make_install_dir()

        assert tmpdir.join('test_id', 'package', 'var', 'praekelt').check()

    def test_create_workspace_dirs_without_root_dir_fails(self, tmpdir):
        """
        When any of the workspace directories are created but the workspace
        hasn't yet been created, an error should be raised.
        """
        workspace = self._create_workspace(tmpdir)

        # Try create the directories without creating the workspace
        with pytest.raises(OSError) as error:
            workspace.make_build_dir()

        assert error.value.errno == 2
        assert error.value.strerror == 'No such file or directory'

        # Try create the directories without creating the workspace
        with pytest.raises(OSError) as error:
            workspace.make_package_dir()

        assert error.value.errno == 2
        assert error.value.strerror == 'No such file or directory'

        # Try create the directories without creating the workspace
        with pytest.raises(OSError) as error:
            workspace.make_install_dir()

        assert error.value.errno == 2
        assert error.value.strerror == 'No such file or directory'

    def test_fetch_repo(self, tmpdir):
        """
        When the repo is fetched in the workspace, git is called with the
        correct commands.
        """
        workspace = self._create_workspace(tmpdir)
        workspace.fetch_repo()

        assert len(self.cmds) == 2

        assert (
            self.cmds[0] ==
            ['git', 'clone', 'https://github.com/praekelt/sideloader2.git',
             str(tmpdir) + '/test_id/sideloader2']
        )

        assert (
            self.cmds[1] ==
            ['git', '-C', str(tmpdir) + '/test_id/sideloader2',
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

    def _create_build(self, tmpdir):
        repo = GitRepo('https://github.com/praekelt/sideloader2.git',
                       'develop', 'sideloader2')

        workspace = Workspace('test_id', str(tmpdir), '/opt', repo)
        workspace.create_clean_workspace()

        deploy = Deploy(name='test_deploy', pip=['django', 'pytest'],
                        buildscript='sideloader/build.sh')
        deploy_type = DeployType()

        build = Build(workspace, deploy, deploy_type)
        build._cmd = self.cmd
        return build

    def test_create_build_virtualenv(self, tmpdir):
        """
        When creating a build virtualenv, the virtualenv directory is created,
        pip is upgraded, and the pip dependencies from the Deploy are
        installed.
        """
        build = self._create_build(tmpdir)
        build.create_build_virtualenv()

        assert len(self.cmds) == 4
        assert (
            self.cmds[0] ==
            ['virtualenv', str(tmpdir) + '/test_id/ve']
        )

        assert (
            self.cmds[1] ==
            [str(tmpdir) + '/test_id/ve/bin/pip', 'install',
             '--upgrade', 'pip']
        )

        assert (
            self.cmds[2] ==
            [str(tmpdir) + '/test_id/ve/bin/pip', 'install',
             '--upgrade', 'django']
        )

        assert (
            self.cmds[3] ==
            [str(tmpdir) + '/test_id/ve/bin/pip', 'install',
             '--upgrade', 'pytest']
        )

    def test_put_env_variables(self, tmpdir):
        """
        When placing the enviornment variables, all the variables are set
        correctly.
        """
        build = self._create_build(tmpdir)
        build.put_env_variables()

        assert os.getenv('VENV') == str(tmpdir) + '/test_id/ve'
        assert (os.getenv('PIP') ==
                str(tmpdir) + '/test_id/ve/bin/pip')
        assert os.getenv('REPO') == 'sideloader2'
        assert os.getenv('BRANCH') == 'develop'
        assert os.getenv('WORKSPACE') == str(tmpdir) + '/test_id'
        assert (os.getenv('BUILDDIR') ==
                str(tmpdir) + '/test_id/build')
        assert (os.getenv('INSTALLDIR') ==
                str(tmpdir) + '/test_id/package/opt')
        assert os.getenv('NAME') == 'test_deploy'

    def test_put_env_variables_path(self, tmpdir):
        """
        When placing the environment variables, PATH is prefixed with the
        virtualenv executables (bin) directory.
        """
        build = self._create_build(tmpdir)
        build.put_env_variables()

        assert os.getenv('PATH').startswith(
            str(tmpdir) + '/test_id/ve/bin')

    def test_run_buildscript(self, tmpdir):
        """
        When running the buildscript, the buildscript is first made executable
        and then executed.
        """
        build = self._create_build(tmpdir)

        build.run_buildscript()

        buildscript = tmpdir.join('test_id', 'sideloader2', 'sideloader',
                                  'build.sh')
        assert self.cmds[0] == ['chmod', 'a+x', buildscript]
        assert self.cmds[1] == [buildscript]

    def test_run_buildscript_no_file(self, tmpdir):
        """
        If there is no buildscript specified, no action is taken.
        """
        build = self._create_build(tmpdir)
        build.deploy = build.deploy.override(buildscript='')

        build.run_buildscript()

        assert len(self.cmds) == 0

    def test_copy_build(self, tmpdir):
        """
        When the build is copied, the directories in the build folder are
        copied over to the install location within the package folder.
        """
        build = self._create_build(tmpdir)

        build.workspace.make_build_dir()
        build.workspace.make_package_dir()

        # Set up some dummy files
        build_dir = tmpdir.join('test_id', 'build')
        fake_dir = build_dir.mkdir('fake')
        dummy_dir = build_dir.mkdir('fake', 'dummy')
        open(str(fake_dir.join('test1.txt')), 'a').close()
        open(str(dummy_dir.join('test2.txt')), 'a').close()

        build.copy_build()

        install_dir = tmpdir.join('test_id', 'package', 'opt')
        assert install_dir.join('fake', 'test1.txt').check()
        assert install_dir.join('fake', 'dummy', 'test2.txt').check()

    def test_copy_config_files(self, tmpdir):
        """
        When the config files are copied, the correct config directory is
        created and the files are copied there.
        """
        build = self._create_build(tmpdir)

        build.workspace.make_build_dir()
        build.workspace.make_package_dir()

        nginx = ConfigFiles.nginx(['config/nginx.conf'])
        supervisor = ConfigFiles.supervisor(['config/my-app.conf'])
        build.deploy = build.deploy.override(config_files=[nginx, supervisor])

        # Make some pretend config files
        build_config_path = tmpdir.mkdir('test_id', 'build', 'config')
        open(str(build_config_path.join('nginx.conf')), 'a').close()
        open(str(build_config_path.join('my-app.conf')), 'a').close()

        build.copy_config_files()

        package_path = tmpdir.join('test_id', 'package')
        assert package_path.join('etc', 'nginx', 'sites-enabled',
                                 'nginx.conf').check()
        assert package_path.join('etc', 'supervisor', 'conf.d',
                                 'my-app.conf').check()

    def test_generate_postinstall(self, tmpdir):
        """
        When the postinstall script is generated, its content is correct.
        """
        build = self._create_build(tmpdir)

        # Set up a fake postinstall script
        script = """lorem ipsum
this is a test"""
        postinstall_path = tmpdir.ensure(
            'test_id', 'sideloader2', 'sideloader', dir=True).join(
                'postinstall.sh')
        postinstall_path.write(script)

        build.deploy = build.deploy.override(postinstall=str(postinstall_path))

        postinstall_script = build.generate_postinstall_script()
        print(postinstall_script)
        assert postinstall_script == """#!/bin/bash



INSTALLDIR={tmpdir}/test_id/package/opt
REPO=sideloader2
BRANCH=develop
NAME=test_deploy

lorem ipsum
this is a test


""".format(tmpdir=str(tmpdir))


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
