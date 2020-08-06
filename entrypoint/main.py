from functools import partial
from inspect import Parameter, signature as signature_of, _empty
from .parser import DefaultParser


_REGISTRY = {}


def _setup_entrypoint(
    parser_class, parser_args, specs, func
):
    # set defaults if missing or empty
    name = parser_args.get('name', '') or func.__name__
    doc_top = func.__doc__.splitlines()[0] if func.__doc__ else ''
    description = parser_args.get('description', '') or doc_top
    parser_args['name'], parser_args['description'] = name, description
    func.invoke = parser_class(func, parser_args, specs).invoke
    # Make this info accessible later, for generating pyproject.toml content
    # and for testing purposes.
    func.entrypoint_name = name
    func.entrypoint_desc = description
    _REGISTRY[name] = f'{func.__module__}:{func.__name__}.invoke'
    return func


def entrypoint(
    *, parser_class=DefaultParser, parser_args=None, specs=None, **kwargs
):
    parser_args = {} if parser_args is None else parser_args.copy()
    specs = {} if specs is None else specs.copy()
    to_parser = parser_class.config_keys() | {'name', 'description'}
    for key, value in kwargs.items():
        (parser_args if key in to_parser else specs)[key] = value
    return partial(
        _setup_entrypoint, parser_class, parser_args, specs
    )
