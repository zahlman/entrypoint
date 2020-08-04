from . import entrypoint

@entrypoint(arg='an argument')
def doc_example_1(arg:int):
    print(f'Doc example 1: arg={arg} of type {type(arg)}')


@entrypoint(arg='an argument')
def doc_example_2(**kwargs):
    print(f'Doc example 2: kwargs={kwargs}')


@entrypoint(tricky='a tricky argument')
def doc_example_3(**tricky):
    print(f'Doc example 3 is a bit tricky: {tricky}')


@entrypoint(fancy={'help': 'fancy help', 'type': int, 'keyword': True})
def doc_example_4(fancy):
    print(f'This is a fancy way to end up with {fancy} (of type {type(fancy)})')


@entrypoint(args={'nargs': '+', 'type': int, 'help': 'values'})
def doc_example_5(*args):
    print(f'Finally, a test of variable positional arguments: {args}')
