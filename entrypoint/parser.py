from abc import ABC, abstractmethod
from argparse import ArgumentParser
from inspect import Parameter, signature as signature_of, _empty
import sys


def _get_arg(code, args_dict):
    literal, value = code
    try:
        return value if literal else args_dict[value]
    except KeyError:
        assert False, f'decorator failed to provide value for `{value}` arg'


class _Dispatcher:
    def __init__(self, param_specs:dict):
        # Keep track of added options and arguments, and what they dispatch to.
        # Dispatch entries are tuples of (bool, value)
        # when the bool is true: the value will be passed as-is
        # when the bool is false: the named key will be looked up.
        self._positional = []
        # VAR_POSITIONAL params can't have a default value. But we can also
        # make a call with *args that are empty even if the function doesn't
        # have such a parameter.
        self._var_positional = (True, [])
        self._keywords = {}
        # If the function doesn't accept **kwargs, we need to track that fact.
        # So we start out by not providing a dict for them.
        self._var_keywords = None
        # Map from parameter name to where it is in the signature.
        # 0..N = index into positional;
        # -1 = use var_positional;
        # None = check keywords and use var_keywords otherwise.
        self._param_mapping = {}
        for name, param in param_specs:
            assert self._var_keywords is None # just a sanity check.
            if param.kind == Parameter.POSITIONAL_OR_KEYWORD:
                self._param_mapping[param.name] = len(self._positional)
                self._positional.append((True, param.default))
            elif param.kind == Parameter.VAR_POSITIONAL:
                # There is at most one parameter of this type.
                assert -1 not in self._param_mapping.values()
                assert param.default is _empty
                self._param_mapping[param.name] = -1
            elif param.kind == Parameter.KEYWORD_ONLY:
                self._param_mapping[param.name] = None
                self._keywords[param.name] = (True, param.default)
            elif param.kind == Parameter.VAR_KEYWORD:
                # We don't refer to this parameter by name;
                # instead, extra parameters get dumped here.
                # Since these are never supplied from a default, we use
                # a set of names, and ignore cases where they aren't found.
                self._var_keywords = set() # this should be the last parameter.
            else:
                # POSITIONAL_ONLY (C interface stuff) is disallowed for now.
                assert False, \
                f'`{param.kind!s}` parameter in function signature not allowed'


    def guarantee(self, signature_name:str):
        """Claim that the named parameter is supplied by the parser."""
        # Any errors that occur here are a programming error at startup,
        # since it means the decorator can't possibly work properly.
        # So we upgrade exceptions to assertions.
        dispatch_code = (False, signature_name)
        try:
            where = self._param_mapping[signature_name]
        except KeyError:
            assert self._var_keywords is not None, ''.join((
                f'decorator attempts to feed data to `{param_name}`',
                'which is not a parameter of the function',
                'and there is no **kwargs parameter'
            ))
            self._var_keywords.add(signature_name)
        else:
            # The parameter is known to exist, so locate it.
            if where is None:
                self._keywords[signature_name] = dispatch_code
            elif where == -1:
                self._var_positional = dispatch_code
            else:
                self._positional[where] = dispatch_code


    def validate(self):
        """Ensure that parameters without default values will get values
        from the parsed arguments."""
        invalid = (True, _empty)
        invalid_positions = [
            i for i, x in enumerate(self._positional) if x == invalid
        ]
        invalid_keywords = {
            k for k, v in self._keywords.items() if v == invalid
        }
        assert not (invalid_positions or invalid_keywords), ' '.join((
            f'positional parameters {invalid_positions} and/or',
            f'keyword-only parameters {invalid_keywords} have neither',
            f'a default value nor a way to be supplied by the decorator'
        ))


    def get_args(self, args_dict:dict):
        """Transform parsed arguments into data usable to call the function."""
        positional = [_get_arg(code, args_dict) for code in self._positional]
        var_args = _get_arg(self._var_positional, args_dict)
        try:
            positional.extend(var_args)
        except TypeError:
            assert False, '*args value from decorator was not iterable'
        keywords = {
            name: _get_arg(code, args_dict)
            for name, code in self._keywords.items()
        }
        if self._var_keywords is not None:
            keywords.update(
                (name, args_dict[name])
                for name in self._var_keywords
                if name in args_dict
            )
        return positional, keywords


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
        self._dispatcher = _Dispatcher(signature_of(func).parameters.items())
        self.setup(config)
        for param_name, spec in specs.items():
            self._add_from_decorator(param_name, spec)
        self._dispatcher.validate()


    @abstractmethod
    def setup(self, config:dict):
        """Prepare to interpret parameter specifications."""
        raise NotImplementedError


    @classmethod
    def config_keys(cls) -> set:
        """Names of keyword arguments used for initialization.
        The decorator will pass these to the constructor rather than using
        them for add_option or add_argument calls."""
        return set()


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


    def call_with(self, positional:list, keywords:dict):
        """Default hook for calling the decorated function.
        Displays the return value (on stdout) or exception message (on stderr)
        and exits with an appropriate return code.

        positional -> positional arguments for the call.
        explicit -> keyword arguments for the call.
        Modify any of these prior to calling at your own risk.
        You can access the function to call as `self._func`.
        """
        try:
            print(self._func(*positional, **keywords))
            sys.exit(0)
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)


    def invoke(self, command_line=None):
        """Call the decorated function using parsed arguments.

        command_line -> list of tokens to parse, or None (use `sys.argv`).

        This should not be overridden - `call_with` is the hook you want.
        This will ordinarily not return; `call_with` should use `sys.exit`
        to give a return value back to the OS."""
        # FIXME: this should happen when the decorator is applied.
        self.call_with(*self._dispatcher.get_args(self.parse(command_line)))


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
