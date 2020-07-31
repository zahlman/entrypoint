from entrypoint import entrypoint


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
    description='', # explicit override - can't use `None`
    params={'description': 'description', 'name': 'name'}
)
def tricky(description, name):
    """Test the use of `params` to allow parameters with special names."""
    pass


_OMITTED = object()
@entrypoint(
    first='an ordinary argument defaulting to a placeholder string',
    args={'help': 'additional string arguments', 'nargs': '+', 'type': int},
    x={'keyword': True, 'help': 'a keyword-only argument with no default'},
    spam={'keyword': True, 'default': _OMITTED, 'help': 'spam value'},
    bacon={'keyword': True, 'default': _OMITTED, 'help': 'bacon value'},
    eggs={'keyword': True, 'default': _OMITTED, 'help': 'eggs value'}
)
def hard(first, *args, x, **kwargs):
    """A harder test of how command-line args are mapped to parameters."""
    print('debug:', first, args, x, kwargs)
    return first, args, x, kwargs


@entrypoint(
    first='an ordinary argument defaulting to a placeholder string',
    second='an argument with a default value',
    third={'nargs': '?', 'help': 'explicitly optional', 'default': 'overridden'}
)
def defaults(first, second='default', third='also default'):
    """A harder test of how command-line args are mapped to parameters."""
    return first, second, third


@entrypoint(
    first={'keyword': True, 'help': 'first argument', 'type': int},
    second={'keyword': True, 'help': 'second argument', 'type': int}
)
def positional_by_keyword(first, second):
    return first, second
