from entrypoint.examples import (
    doc_example_1, doc_example_2, doc_example_3, doc_example_4,
    empty, example, to_rename, tricky, hard, defaults, positional_by_keyword
)
import pytest


def _commandline(func, s):
    return func.invoke(s.split())


def _exited(capsys, func, s):
    with pytest.raises(SystemExit):
        func.invoke(s.split())
    return capsys.readouterr()


def test_from_python():
    """Verify that the functions still work normally
    and that they have the correct attributes set."""
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


def test_doc_examples():
    """Verify the examples given in the documentation, with proper input.
    We don't bother checking the printed output, just the returned values."""
    assert _commandline(doc_example_1, '1') == 1
    assert _commandline(doc_example_2, '--arg=normal -k tricky') == {
        'arg': 'normal', 'kwargs': 'tricky'
    }
    assert _commandline(doc_example_3, '--fancy=1') == 1
    assert _commandline(doc_example_3, '') is None
    assert _commandline(doc_example_4, '1 2 3') == (1, 2, 3)
    assert _commandline(doc_example_4, '') == ()


@pytest.mark.parametrize('func', [example, to_rename])
def test_good_commandline(func):
    """Verify the CLI for some valid command lines.
    We call the .invoke methods directly for all testing."""
    assert _commandline(func, '4 5 6') == 'foo=4, bar=5, baz=6'


@pytest.mark.parametrize('func', [example, to_rename])
@pytest.mark.parametrize('s', ['', '1', '1 2', '1 2 3 4'])
def test_bad_commandlines(capsys, func, s):
    """Verify that an invalid command line causes the program to exit
    and print correct information in a 'usage' message."""
    output = _exited(capsys, func, s).err.splitlines()
    assert output[0].startswith(f'usage: {func.entrypoint_name}')
    assert output[1].startswith(f'{func.entrypoint_name}: error:')


@pytest.mark.parametrize('func', [example, to_rename])
@pytest.mark.parametrize('s', ['-h', '--help'])
def test_help_commandlines(capsys, func, s):
    """Verify that automatic 'help' options work correctly."""
    output = _exited(capsys, func, s).out.splitlines()
    assert output[0].startswith(f'usage: {func.entrypoint_name}')
    assert not output[1] # should be a blank line
    assert output[2] == func.entrypoint_desc


def test_hard():
    """Test for a relatively complex case."""
    first, args, x, kwargs = _commandline(
        hard, 'first 1 2 3 -x y --spam=lovely'
    )
    assert first == 'first'
    assert args == (1, 2, 3)
    assert x == 'y'
    # `bacon` and `eggs` should be suppressed by argparse.
    assert kwargs == {'spam': 'lovely'}


def test_defaults():
    """Test that default values can be provided both implicitly and explicitly,
    and that explicit settings (via the decorator) override implicit ones
    (via the function's signature)."""
    first, second, third = _commandline(defaults, 'first')
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
    """Test that keyword/flags arguments work and can be passed out of order."""
    assert _commandline(positional_by_keyword, s) == (1, 2)
