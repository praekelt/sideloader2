from sideloader.utils import args_str, create_venv_paths


def test_args_str_string_list():
    """ args_str should join a list of strings. """
    assert args_str(['a', 'b']) == 'a b'


def test_args_str_mixed_list():
    """
    args_str should join a list of objects, converting each to a string.
    """
    assert args_str(['a', 1, None]) == 'a 1 None'


def test_args_str_empty_list():
    """ args_str should join return an empty string for an empty list. """
    assert args_str([]) == ''


def test_args_str_string():
    """ args_str should leave string arguments as strings. """
    assert args_str('abc def') == 'abc def'


def test_args_str_none():
    """ args_str should return the string form of non-string arguments. """
    assert args_str(None) == 'None'


def test_create_venv_paths():
    """
    create_venv_paths should return the correct set of paths for a virtualenv
    at the specified location.
    """
    venv_paths = create_venv_paths('/mypath', 'myvenv')

    assert venv_paths.venv == '/mypath/myvenv'
    assert venv_paths.bin == '/mypath/myvenv/bin'
    assert venv_paths.activate == '/mypath/myvenv/bin/activate'
    assert venv_paths.pip == '/mypath/myvenv/bin/pip'
    assert venv_paths.python == '/mypath/myvenv/bin/python'
