from functools import partial
from inspect import signature as signature_of
from .parser import DefaultParser
from .dispatcher import DefaultDispatcher


_REGISTRY = {}


def _prepare_name(func, parser_args):
    name = parser_args.get('name', '{name}').format(
        name=func.__name__.replace('_', '-'), _name=func.__name__
    )
    parser_args['name'] = func.entrypoint_name = name
    _REGISTRY[name] = f'{func.__module__}:{func.__name__}.invoke'


def _prepare_description(func, parser_args):
    doc_top = func.__doc__.splitlines()[0] if func.__doc__ else ''
    description = parser_args.get('description', '') or doc_top
    parser_args['description'] = func.entrypoint_desc = description


def _setup_entrypoint(
    dispatch_class, parser_class, parser_args, specs, func
):
    _prepare_name(func, parser_args)
    _prepare_description(func, parser_args)
    func.invoke = parser_class(
        dispatch_class(signature_of(func).parameters.items()),
        func, parser_args, specs
    ).invoke
    return func


def entrypoint(
    *, dispatch_class=DefaultDispatcher, parser_class=DefaultParser,
    parser_args=None, specs=None, **kwargs
):
    parser_args = {} if parser_args is None else parser_args.copy()
    specs = {} if specs is None else specs.copy()
    to_parser = parser_class.config_keys() | {'name', 'description'}
    for key, value in kwargs.items():
        (parser_args if key in to_parser else specs)[key] = value
    return partial(
        _setup_entrypoint, dispatch_class, parser_class, parser_args, specs
    )
