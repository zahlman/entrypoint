from epmanager.examples import (
    epmanager_example_1, epmanager_example_2, epmanager_example_3,
    epmanager_example_4, empty, un_documented, example, tricky_1,
    custom_parser, hard, defaults, positional_by_keyword, inverse_flag
)
import pytest


def _displayed(capsys, func, s):
    with pytest.raises(SystemExit) as e:
        func.invoke(s.split())
        code = e.args[0]
        assert isinstance(code, int) and code == 0
    return capsys.readouterr().out.splitlines()


def _failed_with(capsys, func, s):
    with pytest.raises(SystemExit) as e:
        func.invoke(s.split())
        code = e.args[0]
        assert isinstance(code, int) and code != 0
    return capsys.readouterr().err.splitlines()


def test_from_python():
    """Verify that the functions still work normally
    and that they have the correct attributes set."""
    assert example(1, 2, 3) == 'foo=1, bar=2, baz=3'
    assert example.entrypoint_name == 'epmanager-example'
    assert example.entrypoint_desc == 'An example entry point for testing.'
    assert tricky_1.entrypoint_name == 'epmanager-renamed-1'
    assert tricky_1.entrypoint_desc == 'Overridden description'
    assert empty() is None
    assert empty.entrypoint_name == 'epmanager-empty'
    assert empty.entrypoint_desc == ''
    assert un_documented() is None
    assert un_documented.entrypoint_name == 'epmanager-un-documented'
    assert un_documented.entrypoint_desc == ''


def test_doc_examples(capsys):
    """Verify the examples given in the documentation, with proper input.
    We don't bother checking the printed output, just the returned values."""
    assert _displayed(capsys, epmanager_example_1, '1') == [
        "arg=1 of type <class 'int'>"
    ]
    assert _displayed(capsys, epmanager_example_2, '--fancy=1') == [
        "This is a fancy way to end up with 1 (of type <class 'int'>)"
    ]
    assert _displayed(capsys, epmanager_example_2, '') == [
        "This is a fancy way to end up with None (of type <class 'NoneType'>)"
    ]
    assert _displayed(
        capsys, epmanager_example_3, '--arg=normal -k tricky'
    ) == [
        "kwargs['arg']=normal, kwargs['kwargs']=tricky"
    ]
    assert _displayed(capsys, epmanager_example_4, '1 2 3') == [
        'Finally, a test of variable positional arguments: (1, 2, 3)'
    ]
    assert _displayed(capsys, epmanager_example_4, '') == [
        'Finally, a test of variable positional arguments: ()'
    ]


def test_empty_no_input(capsys):
    assert not _displayed(capsys, empty, '')


def test_good_commandline(capsys):
    """Verify the CLI for some valid command lines.
    We call the .invoke methods directly for all testing."""
    assert _displayed(capsys, example, '4 5 6') == ['foo=4, bar=5, baz=6']


@pytest.mark.parametrize('s', ['', '1', '1 2', '1 2 3 4'])
def test_bad_commandlines(capsys, s):
    """Verify that an invalid command line causes the program to exit
    and print correct information in a 'usage' message."""
    output = _failed_with(capsys, example, s)
    assert output[0].startswith(f'usage: {example.entrypoint_name}')
    assert output[1].startswith(f'{example.entrypoint_name}: error:')


@pytest.mark.parametrize('s', ['-h', '--help'])
def test_help_commandlines(capsys, s):
    """Verify that automatic 'help' options work correctly."""
    output = _displayed(capsys, example, s)
    assert output[0].startswith(f'usage: {example.entrypoint_name}')
    assert output[1] == ''
    assert output[2] == example.entrypoint_desc


def test_custom_parser(capsys):
    assert _displayed(capsys, custom_parser, '') == ['hacked result']


def test_hard(capsys):
    """Test for a relatively complex case."""
    assert _displayed(
        capsys, hard, 'first 1 2 3 -x y --spam=lovely'
    ) == ["('first', (1, 2, 3), 'y', [('spam', 'lovely')])"]
    # `bacon` and `eggs` should be suppressed by argparse.


def test_defaults(capsys):
    """Test that default values can be provided both implicitly and explicitly,
    and that explicit settings (via the decorator) override implicit ones
    (via the function's signature)."""
    assert _displayed(capsys, defaults, 'first') == [
        "('first', 'default', 'overridden')"
    ]


@pytest.mark.parametrize('s', [
    '-f 1 -s 2', '-s 2 -f 1',
    '--first 1 -s 2', '-s 2 --first 1',
    '-f 1 --second 2', '--second 2 -f 1',
    '--first 1 --second 2', '--second 2 --first 1'
])
def test_positional_by_keyword(capsys, s):
    """Test that keyword/flags arguments work and can be passed out of order."""
    assert _displayed(capsys, positional_by_keyword, s) == ['(1, 2)']


def test_inverse_flag(capsys):
    func = inverse_flag
    assert _displayed(capsys, func, '') == ['True']
    assert _displayed(capsys, func, '-r') == ['False']
    assert _displayed(capsys, func, '--renamed-and-inverted') == ['False']
    # Make sure it doesn't also work with underscores.
    bad_arg = '--renamed_and_inverted'
    assert bad_arg in _failed_with(capsys, func, bad_arg)[1]
