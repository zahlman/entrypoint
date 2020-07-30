from argparse import ArgumentParser
from functools import partial


__version__ = '0.1.0'


def _invoke_wrapper(invoke, func, parser, command_line=None):
    return invoke(func, vars(parser.parse_args(command_line)))


def _add_argument(parser, name, spec):
    if isinstance(spec, str):
        parser.add_argument(name, help=spec)
        return
    if not isinstance(spec, dict):
        raise TypeError(
            f'spec for parameter `{name}` must be either string or dict'
        )
    if spec.get('keyword', False):
        del spec['keyword']
        names = [f'-{name[0]}', f'--{name.replace("_", "-")}']
    else:
        names = [name]
    parser.add_argument(*names, **spec)


def _setup_entrypoint(invoker, description, name, param_specs, func):
    name = name or func.__name__
    desc = description or (func.__doc__ and func.__doc__.splitlines()[0])
    parser = ArgumentParser(prog=name, description=desc)
    for param_name, param_spec in param_specs.items():
        _add_argument(parser, param_name, param_spec)
    func.invoke = partial(_invoke_wrapper, invoker, func, parser)
    # Make this info accessible later, for generating pyproject.toml content
    # and for testing purposes.
    func.entrypoint_name = name
    func.entrypoint_desc = desc
    return func


def _entrypoint(invoker, *, description=None, name=None, params=None, **kwargs):
    return partial(
        _setup_entrypoint, invoker, description, name, params or kwargs
    )


def make_entrypoint(invoker):
    """Create an entrypoint decorator from an invoker function."""
    return partial(_entrypoint, invoker)


def invoke(func, args):
    """Default invoker."""
    return func(**args)


# We don't just apply the decorator because we want clients to be able to use
# the default `invoke` to help implement their own invokers.
entrypoint = make_entrypoint(invoke)