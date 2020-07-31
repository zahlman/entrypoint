from .examples import _OMITTED, empty, example, to_rename
from .examples import tricky, hard, defaults, positional_by_keyword
import pytest


def commandline(func, s):
    return func.invoke(s.split())


def test_original_funcs():
    assert example(1, 2, 3) == 'foo=1, bar=2, baz=3'
    assert example.entrypoint_name == 'example'
    assert example.entrypoint_desc == 'An example entry point for testing.'
    assert to_rename(1, 2, 3) == 'foo=1, bar=2, baz=3'
    assert to_rename.entrypoint_name == 'renamed'
    assert to_rename.entrypoint_desc == 'An example with custom labels.'
    assert tricky.entrypoint_name == 'tricky'
    assert tricky.entrypoint_desc == ''
    assert empty.entrypoint_name is not None
    assert empty.entrypoint_desc is not None


@pytest.mark.parametrize('func', [example, to_rename])
def test_good_commandline(func):
    assert commandline(func, '4 5 6') == 'foo=4, bar=5, baz=6'


@pytest.mark.parametrize('func', [example, to_rename])
@pytest.mark.parametrize('s', ['', '1', '1 2', '1 2 3 4'])
def test_bad_commandlines(capsys, func, s):
    with pytest.raises(SystemExit):
        commandline(func, s)
    output = capsys.readouterr().err.splitlines()
    assert output[0].startswith(f'usage: {func.entrypoint_name}')
    assert output[1].startswith(f'{func.entrypoint_name}: error:')


@pytest.mark.parametrize('func', [example, to_rename])
@pytest.mark.parametrize('s', ['-h', '--help'])
def test_help_commandlines(capsys, func, s):
    with pytest.raises(SystemExit):
        commandline(func, s)
    output = capsys.readouterr().out.splitlines()
    assert output[0].startswith(f'usage: {func.entrypoint_name}')
    assert not output[1] # should be a blank line
    assert output[2] == func.entrypoint_desc


def test_hard():
    first, args, x, kwargs = commandline(hard, 'first 1 2 3 -x y --spam=lovely')
    assert first == 'first'
    assert args == (1, 2, 3)
    assert x == 'y'
    assert kwargs == {'bacon': _OMITTED, 'eggs': _OMITTED, 'spam': 'lovely'}


def test_defaults():
    # `second` and `third` should be optional.
    # `second` should get its default from the function signature.
    # TODO: for string param-specs, also get type from annotation,
    # and make it use flags if it isn't a non-VAR_KEYWORD param.
    first, second, third = commandline(defaults, 'first')
    assert first == 'first'
    assert second == 'default'
    assert third == 'overridden'


@pytest.mark.parametrize('s', [
    '-f 1 -s 2', '-s 2 -f 1',
    '--first 1 -s 2', '-s 2 --first 1',
    '-f 1 --second 2', '--second 2 -f 1',
    '--first 1 --second 2', '--second 2 --first 1'
])
def test_positional_by_keyword(s):
    assert commandline(positional_by_keyword, s) == (1, 2)
