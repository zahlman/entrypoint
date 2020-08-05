from argparse import ArgumentParser


class Parser:
    """Abstract base class for Parsers.

    A Parser implements the core logic for an entrypoint decorator."""
    def __init__(self, dispatcher:callable, func: callable, config:dict):
        """Contructor.
        dispatcher -> maps parsed arguments onto the decorated function.
        func -> the decorated function.
        config -> additional configuration options."""
        self._dispatcher = dispatcher
        self._func = func


    @classmethod
    def config_keys(cls) -> set:
        """Names of keyword arguments used for initialization.
        The decorator will pass these to the constructor rather than using
        them for add_option or add_argument calls."""
        return {'name', 'description'}


    def add_option(self, name:str, decorator_spec:dict, param_spec:dict):
        """Specify a command-line option.
        name -> name of the intended recipient parameter.
        decorator_spec -> parsing options from the decorator.
        Format and interpretation is up to the concrete parser.
        param_spec -> may contain 'default' and/or 'type' specifications."""
        raise NotImplementedError


    def add_argument(self, name:str, decorator_spec:dict, param_spec:dict):
        """Specify a command-line option.
        name -> name of the intended recipient parameter.
        decorator_spec -> parsing options from the decorator.
        Format and interpretation is up to the concrete parser.
        param_spec -> may contain 'default' and/or 'type' specifications."""
        raise NotImplementedError


    def parse(self, command_line) -> dict:
        """Parse the command-line contents.
        command_line -> list of tokens to parse, or None (use `sys.argv`).
        Returns a mapping of parameter names to the values they'll receive."""
        raise NotImplementedError


    def invoke(self, command_line=None):
        """Call the decorated function using parsed arguments.
        This should not be overridden - replace the dispatcher instead.
        command_line -> list of tokens to parse, or None (use `sys.argv`)."""
        return self._dispatcher(self._func, self.parse(command_line))



class DefaultParser(Parser):
    """Default implementation of a Parser.
    
    Delegates to an `argparse.ArgumentParser` to do the work."""
    def __init__(self, dispatcher:callable, func:callable, config:dict):
        super().__init__(dispatcher, func, config)
        self._impl = ArgumentParser(
            prog=config.get('name', ''),
            description=config.get('description', '')
        )


    def _merge_spec(self, decorator_spec, param_spec):
        # We handle the parameter spec by letting it provide defaults
        # for the spec that will be passed to `.add_argument`.
        spec = param_spec.copy()
        if 'default' in spec:
            spec['nargs'] = '?'
        # Explicitly specified values take precedence.
        spec.update(decorator_spec)
        return spec


    def add_option(self, name, decorator_spec, param_spec):
        self._impl.add_argument(
            f'-{name[0]}', f'--{name.replace("_", "-")}',
            **self._merge_spec(decorator_spec, param_spec)
        )


    def add_argument(self, name, decorator_spec, param_spec):
        self._impl.add_argument(
            name, **self._merge_spec(decorator_spec, param_spec)
        )


    def parse(self, command_line):
        return vars(self._impl.parse_args(command_line))
