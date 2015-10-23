import os
import shutil
import subprocess
import sys
import time

from collections import namedtuple


def log(message):
    """ Log a timestamped message to stdout. """
    sys.stdout.write('[%s] %s\n' % (time.ctime(), message))
    sys.stdout.flush()


def args_str(args):
    """ Convert a list of arguments to a string. """
    if isinstance(args, list):
        return ' '.join([str(arg) for arg in args])

    return str(args)


def cmd(args, debug=False):
    """ Run the given command. """
    if debug:
        log(args_str(args))

    output = subprocess.check_output(args, shell=False)

    if debug:
        log(output)

    return output


def rmtree_if_exists(tree_path):
    """
    Delete a directory and its contents if the directory exists.

    :param: tree_path:
    The path to the directory.

    :returns:
    True if the directory existed and was deleted. False otherwise.
    """
    if os.path.exists(tree_path):
        shutil.rmtree(tree_path)
        return True
    return False


def listdir_abs(path):
    """
    List the contents of a directory returning the absolute paths to the child
    files/folders.

    :param: path:
    The relative or absolute path to the directory.

    :returns:
    A list of absolute paths to the child files/folders.
    """
    abspath = os.path.abspath(path)
    return [os.path.join(abspath, child) for child in os.listdir(abspath)]

""" A tuple of common virtualenv paths. """
VenvPaths = namedtuple('VenvPath',
                       ['venv', 'bin', 'activate', 'pip', 'python'])


def create_venv_paths(root_path, name='ve'):
    """
    Create a VenvPaths named tuple of common virtualenv paths.

    :param: root_path:
    The path in which to create the virtualenv directory.

    :param: name:
    The name of the virtualenv. Defaults to 've'.

    :returns:
    The VenvPaths named tuple containing the path to the virtualenv, the bin
    directory, the activate script, pip, and python.
    """
    venv_path = os.path.join(root_path, name)
    venv_bin_path = os.path.join(venv_path, 'bin')
    return VenvPaths(
        venv=venv_path,
        bin=venv_bin_path,
        activate=os.path.join(venv_bin_path, 'activate'),
        pip=os.path.join(venv_bin_path, 'pip'),
        python=os.path.join(venv_bin_path, 'python')
    )
