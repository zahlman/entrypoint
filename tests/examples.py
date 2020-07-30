from entrypoint import entrypoint


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
