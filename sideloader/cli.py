import click

from sideloader import Build, Config, GitRepo, Sideloader


@click.command()
@click.argument('git-url')
@click.option('--branch', help='Git branch')
@click.option('--build', help='Build version', default=0)
@click.option('--id', help='Workspace ID')
@click.option('--deploy-file', help='Deploy YAML file', default='.deploy.yaml')
@click.option('--name', help='Package name')
@click.option('--build-script', help='Build script relative path')
@click.option('--postinst-script', help='Post-install script relative path')
@click.option('--dtype', help='Deploy type', default='virtualenv')
@click.option('--packman', help='Package manager', default='deb',
              type=click.Choice(['deb', 'rpm']))
@click.option('--config', help='Sideloader config', default='config.yaml',
              type=click.Path())
@click.option('--debug/--no-debug', help='Log additional debug information',
              default=False)
def main(git_url, branch, build, id, deploy_file, name,
         build_script, postinst_script, dtype, packman, config, debug):
    config = Config.from_config_file(config)
    repo = GitRepo.from_github_url(git_url, branch)
    build_def = Build(id, dtype, packman)

    sideloader = Sideloader(config, repo, build_def)
    sideloader.debug = debug
    sideloader.deploy_file = deploy_file
    sideloader.set_deploy_overrides(
        name=name, buildscript=build_script, postinstall=postinst_script,
        version='0.%s' % build)

    sideloader.create_workspace()
    sideloader.run_buildscript()
    sideloader.create_package()
