from abc import ABC, abstractmethod
from argparse import ArgumentParser
from inspect import Parameter, signature as signature_of, _empty
import sys


class Parser(ABC):
    """Abstract base class for Parsers.

    A Parser implements the core logic for an entrypoint decorator."""
    def __init__(self, func: callable, config:dict):
        """Contructor.
        dispatcher -> maps parsed arguments onto the decorated function.
        func -> the decorated function.
        config -> additional configuration options."""
        self._func = func


    @classmethod
    def config_keys(cls) -> set:
        """Names of keyword arguments used for initialization.
        The decorator will pass these to the constructor rather than using
        them for add_option or add_argument calls."""
        return set() 


    @abstractmethod
    def add_option(self, name:str, decorator_spec:dict, param_spec:dict):
        """Specify a command-line option.
        name -> name of the intended recipient parameter.
        decorator_spec -> parsing options from the decorator.
        Format and interpretation is up to the concrete parser.
        param_spec -> may contain 'default' and/or 'type' specifications."""
        raise NotImplementedError


    @abstractmethod
    def add_argument(self, name:str, decorator_spec:dict, param_spec:dict):
        """Specify a command-line argument.
        name -> name of the intended recipient parameter.
        decorator_spec -> parsing options from the decorator.
        Format and interpretation is up to the concrete parser.
        param_spec -> may contain 'default' and/or 'type' specifications."""
        raise NotImplementedError


    @abstractmethod
    def parse(self, command_line) -> dict:
        """Parse the command-line contents.
        command_line -> list of tokens to parse, or None (use `sys.argv`).
        Returns a mapping of parameter names to the values they'll receive."""
        raise NotImplementedError


    def _get_dispatched_args(self, parsed_args):
        """Default invoker."""
        # Any errors that occur here should be treated as programming errors,
        # because they indicate that the interface created through the
        # entrypoint decorator is broken (does not reliably map to the
        # underlying function's parameters). So we use assertions.
        positional = []
        # `parsed_args` were created locally, so we don't need a copy
        # even though we delete keys.
        keywords = parsed_args
        has_kwargs_param = False
        explicit_keywords = {}
        for name, param in signature_of(self._func).parameters.items():
            assert not has_kwargs_param # just a sanity check.
            if param.kind == Parameter.VAR_KEYWORD:
                has_kwargs_param = True # this should be the last parameter.
                continue
            if name in keywords:
                arg = keywords[name]
                del keywords[name]
            else:
                assert param.default != _empty, \
                f'command-line args missing necessary value for `{name}`'
                arg = keywords.get(name, param.default)
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
        if not has_kwargs_param:
            k = set(keywords.keys())
            assert not k, f'extra unusable command-line arguments found: {k}'
        assert not set(explicit_keywords.keys()) & set(keywords.keys())
        return positional, explicit_keywords, keywords


    def call_with(self, positional:list, explicit:dict, keywords:dict):
        """Default hook for calling the decorated function.
        Displays the return value (on stdout) or exception message (on stderr)
        and exits with an appropriate return code.
        
        positional -> positional arguments for the call.
        explicit -> keyword-only arguments for the call.
        keywords -> `**kwargs` arguments for the call.
        Modify any of these prior to calling at your own risk.
        You can access the function to call as `self._func`.
        """
        return self._func(*positional, **explicit, **keywords)


    def invoke(self, command_line=None):
        """Call the decorated function using parsed arguments.

        command_line -> list of tokens to parse, or None (use `sys.argv`).
        
        This should not be overridden - `call_with` is the hook you want.
        This will ordinarily not return; `call_with` should use `sys.exit`
        to give a return value back to the OS."""
        return self.call_with(
            *self._get_dispatched_args(self.parse(command_line))
        )


class DefaultParser(Parser):
    """Default implementation of a Parser.
    
    Delegates to an `argparse.ArgumentParser` to do the work."""
    def __init__(self, func:callable, config:dict):
        super().__init__(func, config)
        self._impl = ArgumentParser(
            prog=config.get('name', ''),
            description=config.get('description', '')
        )


    def add_option(self, name, decorator_spec, param_spec):
        self._impl.add_argument(
            f'-{name[0]}', f'--{name.replace("_", "-")}',
            **{**param_spec, **decorator_spec}
        )


    def add_argument(self, name, decorator_spec, param_spec):
        extra_spec = {'nargs': '?'} if 'default' in param_spec else {}
        self._impl.add_argument(
            name, **{**param_spec, **extra_spec, **decorator_spec}
        )


    def parse(self, command_line):
        return vars(self._impl.parse_args(command_line))
