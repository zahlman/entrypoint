from argparse import SUPPRESS
import sys
from . import entrypoint, parser


@entrypoint(arg='an argument')
def epmanager_example_1(arg:int):
    return f'arg={arg} of type {type(arg)}'


@entrypoint(arg='a normal argument', kwargs='a tricky argument')
def epmanager_example_2(**kwargs):
    return f"kwargs['arg']={kwargs['arg']}, kwargs['kwargs']={kwargs['kwargs']}"


@entrypoint(_fancy={'help': 'fancy help', 'type': int})
def epmanager_example_3(fancy):
    return f'This is a fancy way to end up with {fancy} (of type {type(fancy)})'


@entrypoint(args={'nargs': '*', 'type': int, 'help': 'values'})
def epmanager_example_4(*args):
    return f'Finally, a test of variable positional arguments: {args}'


# For examples not explicitly referenced in the doc, use a special decorator
# to prefix the command names.
def my_entrypoint(**kwargs):
    kwargs.setdefault('name', 'epmanager-{name}')
    return entrypoint(**kwargs)


# The computed description should always be a string, not None.
@my_entrypoint()
def empty():
    pass


@my_entrypoint(description='')
def un_documented():
    """This text should be ignored and not used for documentation."""
    pass


@my_entrypoint(
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


@my_entrypoint(
    description='Overridden description', name='epmanager-renamed-1',
    specs={'description': 'description', 'name': 'name'}
)
def tricky_1(description, name):
    """Test the use of `specs` to disambiguate decorator arguments."""
    pass


# This test ensures that a custom parser a) isn't forced to call the
# underlying function at all; b) can receive a custom parameter. It also tests
# the decorator's setup for disambiguating names.
class TestParser(parser.DefaultParser):
    @classmethod
    def config_keys(cls):
        return {'parser_class'}


    def setup(self, config):
        super().setup(config)
        self._pc = config['parser_class']


    def call_with(self, parsed_args):
        print(self._pc)
        sys.exit(0)


@my_entrypoint(
    parser_class=TestParser, parser_args={'parser_class': 'hacked result'}
)
def custom_parser():
    raise ValueError('custom parser failed to prevent execution')


@my_entrypoint(
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


@my_entrypoint(
    first='an ordinary argument defaulting to a placeholder string',
    second='an argument with a default value',
    third={'nargs': '?', 'help': 'explicitly optional', 'default': 'overridden'}
)
def defaults(first, second='default', third='also default'):
    """A harder test of how command-line args are mapped to parameters."""
    return first, second, third


@my_entrypoint(
    _first={'help': 'first argument', 'type': int},
    _second={'help': 'second argument', 'type': int}
)
def positional_by_keyword(first, second):
    return first, second


@my_entrypoint(
    _renamed_and_inverted={'action': 'store_false', 'dest': 'original_name'}
)
def inverse_flag(original_name=True):
    """Test of advanced functionality, inspired by the discovery interface."""
    return original_name
