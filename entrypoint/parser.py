from abc import ABC, abstractmethod
from argparse import ArgumentParser
from inspect import Parameter, signature as signature_of, _empty
import sys

from .dispatcher import DefaultDispatcher


def _as_dict(decorator_spec):
    if isinstance(decorator_spec, str):
        return {'help': decorator_spec}
    elif isinstance(decorator_spec, dict):
        return decorator_spec.copy()
    else:
        raise TypeError(
            f'spec for parameter `{param_name}` must be either string or dict'
        )


class Parser(ABC):
    """Abstract base class for Parsers.

    A Parser implements the core logic for an entrypoint decorator."""
    def __init__(self, func: callable, config:dict, specs:dict):
        """Contructor.
        dispatcher -> maps parsed arguments onto the decorated function.
        func -> the decorated function.
        config -> additional configuration options.
        specs -> specifications for parameters to parse."""
        self._func = func
        self._dispatcher = DefaultDispatcher(signature_of(func).parameters.items())
        self.setup(config)
        for param_name, spec in specs.items():
            self._add_from_decorator(param_name, spec)
        self._dispatcher.validate()


    def _add_from_decorator(self, param_name, spec):
        # prepare two specs: one from modifying the decorator's spec, and one
        # representing additional requirements from the parameter's signature.
        signature = signature_of(self._func)
        decorator_spec = _as_dict(spec)
        add_method = self.add_argument
        if param_name.startswith('_'):
            add_method, param_name = self.add_option, param_name[1:]
        param_info = signature.parameters.get(param_name, None)
        param_spec = {}
        if param_info is None:
            add_method = self.add_option
        else:
            if param_info.kind == Parameter.VAR_KEYWORD:
                add_method = self.add_option
            if param_info.default is not _empty:
                param_spec['default'] = param_info.default
            annotation = param_info.annotation
            if callable(annotation) and annotation is not _empty:
                param_spec['type'] = annotation
        self._dispatcher.guarantee(
            add_method(param_name, decorator_spec, param_spec)
        )


    def raw_call(self, parsed_args):
        """Call the decorated function with no setup or teardown.

        parsed_args -> result from parsing the command line.
        Override `call_with` to wrap this process as desired."""
        return self._dispatcher.invoke(self._func, parsed_args)


    def invoke(self, command_line=None):
        """Call the decorated function using parsed arguments.

        command_line -> list of tokens to parse, or None (use `sys.argv`).

        This should not be overridden - `call_with` is the hook you want.
        This will ordinarily not return; `call_with` should use `sys.exit`
        to give a return value back to the OS."""
        self.call_with(self.parse(command_line))


    # Hooks for derived classes to implement.
    @classmethod
    def config_keys(cls) -> set:
        """Names of keyword arguments used for initialization.
        The decorator will pass these to the constructor rather than using
        them for add_option or add_argument calls.
        Override this with any config options needed other than `name`
        and `description` for initialization."""
        return set()


    @abstractmethod
    def setup(self, config:dict):
        """Prepare to interpret parameter specifications."""
        raise NotImplementedError


    @abstractmethod
    def add_option(self, name:str, deco_spec:dict, param_spec:dict) -> str:
        """Specify a command-line option.

        name -> name of the intended recipient parameter.
        deco_spec -> parsing options from the decorator.
        (Format and interpretation is up to the concrete parser.)
        param_spec -> may contain 'default' and/or 'type' specifications.

        Returns the name of the parameter that will be fed by this option."""
        raise NotImplementedError


    @abstractmethod
    def add_argument(self, name:str, deco_spec:dict, param_spec:dict) -> str:
        """Specify a command-line argument.

        name -> name of the intended recipient parameter.
        deco_spec -> parsing options from the decorator.
        (Format and interpretation is up to the concrete parser.)
        param_spec -> may contain 'default' and/or 'type' specifications.

        Returns the name of the parameter that will be fed by this argument."""
        raise NotImplementedError


    @abstractmethod
    def parse(self, command_line) -> dict:
        """Parse the command-line contents.
        command_line -> list of tokens to parse, or None (use `sys.argv`).
        Returns a mapping of parameter names to the values they'll receive."""
        raise NotImplementedError


    def call_with(self, parsed_args):
        """Default hook for calling the decorated function.
        Displays the return value (on stdout) or exception message (on stderr)
        and exits with an appropriate return code.

        parsed_args -> result from the .parse method.
        Override this to change the setup and teardown behaviour, for example,
        to change the top-level exception handling.
        Use `self.raw_call` to invoke the underlying decorated function."""
        try:
            print(self.raw_call(parsed_args))
            sys.exit(0)
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)


class DefaultParser(Parser):
    """Default implementation of a Parser.

    Delegates to an `argparse.ArgumentParser` to do the work."""
    def setup(self, config:dict):
        self._impl = ArgumentParser(
            prog=config.get('name', ''),
            description=config.get('description', '')
        )


    def add_option(self, name:str, deco_spec:dict, param_spec:dict) -> str:
        self._impl.add_argument(
            f'-{name[0]}', f'--{name.replace("_", "-")}',
            **{**param_spec, **deco_spec}
        )
        return deco_spec.get('dest', name)


    def add_argument(self, name:str, deco_spec:dict, param_spec:dict) -> str:
        extra_spec = {'nargs': '?'} if 'default' in param_spec else {}
        self._impl.add_argument(
            name, **{**param_spec, **extra_spec, **deco_spec}
        )
        return deco_spec.get('dest', name)


    def parse(self, command_line):
        return vars(self._impl.parse_args(command_line))
