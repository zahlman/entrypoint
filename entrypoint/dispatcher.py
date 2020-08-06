from inspect import Parameter, _empty


def _get_arg(code, args_dict):
    literal, value = code
    try:
        return value if literal else args_dict[value]
    except KeyError:
        assert False, f'decorator failed to provide value for `{value}` arg'


class Dispatcher:
    def __init__(self, param_specs):
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
            # This should only get set on the last iteration, if at all.
            assert self._var_keywords is None
            assert param.name == name
            self._setup(name, param.kind, param.default)


    def _setup(self, name, kind, default):
        if kind == Parameter.POSITIONAL_OR_KEYWORD:
            self._param_mapping[name] = len(self._positional)
            self._positional.append((True, default))
        elif kind == Parameter.VAR_POSITIONAL:
            # There is at most one parameter of this type.
            assert -1 not in self._param_mapping.values()
            assert default is _empty
            self._param_mapping[name] = -1
        elif kind == Parameter.KEYWORD_ONLY:
            self._param_mapping[name] = None
            self._keywords[name] = (True, default)
        elif kind == Parameter.VAR_KEYWORD:
            # We don't refer to this parameter by name;
            # instead, extra parameters get dumped here.
            # Since these are never supplied from a default, we use
            # a set of names, and ignore cases where they aren't found.
            self._var_keywords = set() # this should be the last parameter.
        else:
            # POSITIONAL_ONLY (C interface stuff) is disallowed for now.
            assert False, \
            f'`{kind!s}` parameter in function signature not allowed'


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


    def invoke(self, func, args_dict:dict):
        """Transform parsed argument dict into function-call args."""
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
        return func(*positional, **keywords)
