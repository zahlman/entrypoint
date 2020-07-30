from entrypoint import __version__, entrypoint
import pytest


@entrypoint(
    foo='the value for foo',
    bar='the value for bar',
    baz='the value for baz'
)
def example(foo, bar, baz):
    """An example entry point for testing.

    The rest of the function __doc__ is ignored by the entrypoint library.
    foo -> a foo value.
    bar -> a bar value.
    baz -> a baz value.

    Returns a string indicating what was passed in."""
    return f'foo={foo}, bar={bar}, baz={baz}'


@entrypoint(
    description='An example with custom name and description.',
    name='renamed',
    foo='the value for foo',
    bar='the value for bar',
    baz='the value for baz'
)
def to_rename(foo, bar, baz):
    """This text should be replaced explicitly."""
    return f'foo={foo}, bar={bar}, baz={baz}'


@entrypoint(
    params={'description': 'description', 'name': 'name'}
)
def tricky(description, name):
    pass


def commandline(func, s):
    return func.invoke(s.split())


def test_original_funcs():
    assert example(1, 2, 3) == 'foo=1, bar=2, baz=3'
    assert example.entrypoint_name == 'example'
    assert example.entrypoint_desc == 'An example entry point for testing.'
    assert to_rename(1, 2, 3) == 'foo=1, bar=2, baz=3'
    assert to_rename.entrypoint_name == 'renamed'
    assert to_rename.entrypoint_desc == 'An example with custom name and description.'
    assert tricky.entrypoint_name == 'tricky'
    assert tricky.entrypoint_desc is None


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
