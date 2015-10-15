import click

from sideloader import Sideloader


@click.command()
@click.argument('git-url')
@click.option('--branch', help='Git branch')
@click.option('--build', help='Build version', default=0)
@click.option('--id', help='Workspace ID')
@click.option('--deploy-file', help='Deploy YAML file', default='.deploy.yaml')
@click.option('--name', help='Package name')
@click.option('--build-script', help='Build script relative path')
@click.option('--postinst-script', help='Post-install script relative path')
@click.option('--dtype', help='Deploy type', default='virtualenv',
              type=click.Choice(['dir', 'python', 'virtualenv']))
@click.option('--packman', help='Package manager', default='deb',
              type=click.Choice(['deb', 'rpm']))
@click.option('--config', help='Sideloader config', default='config.yaml',
              type=click.Path())
@click.option('--debug/--no-debug', help='Log additional debug information',
              default=False)
@click.option('--sign/--no-sign',
              help='Enable GPG signing of .deb packages (requires a key to be '
                   'configured)',
              default=True)
def main(git_url, branch, build, id, deploy_file, name,
         build_script, postinst_script, dtype, packman, config, debug, sign):
    sideloader = Sideloader(config, git_url, branch, id, debug)
    sideloader.run(deploy_file, dtype, packman, build, sign, name=name,
                   buildscript=build_script, postinstall=postinst_script)
