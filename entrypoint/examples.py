from argparse import SUPPRESS
from . import entrypoint


@entrypoint(arg='an argument')
def doc_example_1(arg:int):
    return f'arg={arg} of type {type(arg)}'


@entrypoint(arg='a normal argument', kwargs='a tricky argument')
def doc_example_2(**kwargs):
    return f"kwargs['arg']={kwargs['arg']}, kwargs['kwargs']={kwargs['kwargs']}"


@entrypoint(_fancy={'help': 'fancy help', 'type': int})
def doc_example_3(fancy):
    return f'This is a fancy way to end up with {fancy} (of type {type(fancy)})'


@entrypoint(args={'nargs': '*', 'type': int, 'help': 'values'})
def doc_example_4(*args):
    return f'Finally, a test of variable positional arguments: {args}'


# The computed description should always be a string, not None.
@entrypoint()
def empty():
    pass


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
    description='An example with custom labels.',
    name='renamed',
    foo='the value for foo',
    bar='the value for bar',
    baz='the value for baz'
)
def to_rename(foo, bar, baz):
    """This text should be replaced explicitly."""
    return f'foo={foo}, bar={bar}, baz={baz}'


@entrypoint(
    description='Overridden description', name='renamed_1',
    specs={'description': 'description', 'name': 'name'}
)
def tricky_1(description, name):
    """Test the use of `param_specs` to disambiguate decorator arguments."""
    pass


# TODO: set up a test with a custom Parser that expects args with special
# names, to verify that `parser_args` works properly.


@entrypoint(
    first='an ordinary argument defaulting to a placeholder string',
    args={'help': 'additional string arguments', 'nargs': '+', 'type': int},
    _x={'help': 'a keyword-only argument with no default'},
    _spam={'default': SUPPRESS, 'help': 'spam value'},
    _bacon={'default': SUPPRESS, 'help': 'bacon value'},
    _eggs={'default': SUPPRESS, 'help': 'eggs value'}
)
def hard(first, *args, x, **kwargs):
    """A harder test of how command-line args are mapped to parameters."""
    return first, args, x, sorted(kwargs.items()) 


@entrypoint(
    first='an ordinary argument defaulting to a placeholder string',
    second='an argument with a default value',
    third={'nargs': '?', 'help': 'explicitly optional', 'default': 'overridden'}
)
def defaults(first, second='default', third='also default'):
    """A harder test of how command-line args are mapped to parameters."""
    return first, second, third


@entrypoint(
    _first={'help': 'first argument', 'type': int},
    _second={'help': 'second argument', 'type': int}
)
def positional_by_keyword(first, second):
    return first, second


@entrypoint(
    _renamed_and_inverted={'action': 'store_false', 'dest': 'original_name'}
)
def inverse_flag(original_name=True):
    """Test of advanced functionality, inspired by the discovery interface."""
    return original_name
