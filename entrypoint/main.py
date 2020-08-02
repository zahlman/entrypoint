from argparse import ArgumentParser
from functools import partial
from inspect import Parameter, signature, _empty


_REQUIRED = _empty
_UNSPECIFIED = _empty
_REGISTRY = {}


def _flag_names(name):
    return [f'-{name[0]}', f'--{name.replace("_", "-")}']


def _str_arg_data(name, parser_spec, func_spec):
    spec = {'help': parser_spec}
    if func_spec is None:
        names = _flag_names(name)
    else:
        is_keyword = func_spec.kind == Parameter.VAR_KEYWORD
        names = _flag_names(name) if is_keyword else [name]
        if is_keyword:
            spec['nargs'] = '?'
        if func_spec.default != _REQUIRED:
            spec['default'] = func_spec.default
            spec['nargs'] = '?'
        if func_spec.annotation != _UNSPECIFIED:
            spec['type'] = func_spec.annotation
    return names, spec


def _dict_arg_data(name, parser_spec, func_spec):
    spec = parser_spec.copy()
    if spec.get('keyword', False):
        del spec['keyword']
        names = _flag_names(name)
    else:
        names = [name]
    return names, spec


def _arg_data(name, parser_spec, func_spec):
    try:
        handler = {str: _str_arg_data, dict: _dict_arg_data}[type(parser_spec)]
    except KeyError:
        raise TypeError(
            f'spec for parameter `{name}` must be either string or dict'
        )
    return handler(name, parser_spec, func_spec)


def _make_parser(name, desc, signature, param_specs):
    impl = ArgumentParser(prog=name, description=desc)
    for param_name, param_spec in param_specs.items():
        names, spec = _arg_data(
            param_name, param_spec, signature.parameters.get(param_name, None)
        )
        impl.add_argument(*names, **spec)
    return lambda command_line: vars(impl.parse_args(command_line))


def _setup_entrypoint(
    invoke, make_parser, name, description, param_specs, func
):
    name = name or func.__name__
    desc = description
    if desc is None: # but allow desc == ''
        desc = func.__doc__.splitlines()[0] if func.__doc__ else ''
    parser = _make_parser(name, desc, signature(func), param_specs)
    func.invoke = lambda command_line=None: invoke(func, parser(command_line))
    # Make this info accessible later, for generating pyproject.toml content
    # and for testing purposes.
    func.entrypoint_name = name
    func.entrypoint_desc = desc
    _REGISTRY[name] = f'{func.__module__}:{func.__name__}.invoke'
    return func


def invoke(func, args):
    """Default invoker."""
    # Any errors that occur here should be treated as programming errors,
    # because they indicate that the interface created through the
    # entrypoint decorator is broken (does not reliably map to the underlying
    # function's parameters). So we use assertions.
    positional = []
    # `args` come from the wrapper function and are not externally accessible,
    # so there is no need to make a copy even though we delete keys.
    keywords = args
    kwarg_name = None
    seen_kwargs = False
    explicit_keywords = {}
    for name, param in signature(func).parameters.items():
        assert not seen_kwargs # just a sanity check.
        if param.kind == Parameter.VAR_KEYWORD:
            seen_kwargs = True # this should be the last one.
            kwarg_name = name
            continue
        if name in keywords:
            arg = keywords[name]
            del keywords[name]
        else:
            assert param.default != _REQUIRED, \
            f'command-line args missing necessary value for `{name}`'
            arg = keyword.get(name, param.default)
        if param.kind == Parameter.VAR_POSITIONAL:
            try:
                iter(arg)
            except TypeError:
                assert False, \
                'command-line arg for VAR_POSITIONAL parameter must be iterable'
            positional.extend(arg)
        elif param.kind == Parameter.POSITIONAL_OR_KEYWORD:
            positional.append(arg)
        elif param.kind == Parameter.KEYWORD_ONLY:
            explicit_keywords[name] = arg
        else:
            # POSITIONAL_ONLY (C interface stuff) is disallowed for now.
            assert False, \
            f'`{param.kind!s}` parameter in function signature not allowed'
    if kwarg_name is None:
        assert not keywords, 'extra unusuable command-line arguments found'
    elif kwarg_name in keywords:
        # the **kwargs parameter name was explicitly specified in the
        # interface. Make sure there are no extra values, then unpack.
        assert set(keywords.keys()) == {kwarg_name}, \
        'extra unusable command-line arguments found'
        keywords = keywords[kwarg_name]
    return func(*positional, **explicit_keywords, **keywords)


def entrypoint(
    invoke=invoke, make_parser=_make_parser, name=None, description=None,
    params=None, **kwargs
):
    return partial(
        _setup_entrypoint, invoke, make_parser,
        name, description, params or kwargs
    )
