# `entrypoint` - quick and easy entry points for Python packages

## Basic usage

`from entrypoint import entrypoint`, and then use the `@entrypoint` decorator on the function that should serve as the entry point to your code. The decorator adds an `.invoke` member to the function, which is the actual entry point that should be referenced in your `pyproject.toml` (or `setup.py`).

### The `@entrypoint` decorator

The decorator accepts only keyword arguments, and cannot be used in no-argument form. It can, however, be used with zero arguments (particularly useful if the decorated function also takes zero arguments).

These keyword arguments are treated specially:

* `invoke` - a callable that overrides the default logic for passing the parsed arguments to the function. The default `invoke` function is available as `entrypoint.invoke` to do the heavy lifting in custom implementations.

* `make_parser` - a callable that creates a *parser function* (see "Custom parser functions" and "The default `make_parser`").

* `name` - the (string) name of the entry point. This will be assigned to the `.entrypoint_name` attribute of the function for introspection purposes, and is used by the default parser function to create a command-line usage message for the entry point. It is also used for automatic update of `pyproject.toml` (see *"Entrypoint discovery"*). By default, the function's `__name__` attribute is used.

* `description` - a description string for the entry point. This will be assigned to the `.entrypoint_desc` attribute of the function for introspection purposes, and is used by the default parser function to create a command-line usage message for the entry point. By default, the first line of the function's `__doc__` is used, or failing that, an empty string.

* `params` - if provided, this should be a dict that provides *parameter specifications* used by the `make_parser` callable. Otherwise, you can provide these as `**kwargs`. (This system allows you to have command-line arguments with names that would otherwise conflict, while still allowing the convenience of `**kwargs` in ordinary cases.)

The decorator does not wrap or replace the function, but instead registers it in a private registry and adds three attributes:

* `entrypoint_name` - described above
* `entrypoint_desc` - described above
* `invoke` - as mentioned in the introduction, this is the true entrypoint to the code that will be referenced in `pyproject.toml` or `setup.py`. This setup ensures that the original function can function normally as a part of your package's API when imported.

## Customization

### Custom parser functions

A parser function needs to accept a string (representing the command line, minus the program name) and return a dict of parsed arguments (mapping from string names to arbitrary objects). It will be created by a `make_parser` implementation, which returns a parser function and accepts four arguments:

* `name` - the (string) name of the entrypoint
* `desc` - the (string) description for the entrypoint
* `signature` - the signature of the function being decorated (an `inspect.Signature` object)
* `param_specs` - the parameter specifications (provided in the `params` or `**kwargs` of the decorator; a dict mapping strings to arbitrary objects)

The parser function dictates what values are allowed in the `param_specs` dictionary, and determines their interpretation. It should use the `name` and `desc` to create the "usage" message shown by the entry point (either by a "help" option, if supported, or as an error message). It may use the `signature` to help interpret the `param_specs`.

### The default `make_parser`

The default `make_parser` implementation creates an `argparse.ArgumentParser` with the supplied `name` and `desc`. The `param_specs` values may either be strings or dicts, interpreted as follows:

* If a dict is provided, it mainly contains keyword arguments for the call to the `.add_argument` method of the `ArgumentParser`. There is one exception: if a `keyword` pair is present and has a true-ish value, the parser argument will be a "flags" argument (see below).

* If a string is provided, that string is used as the help text for the parameter. Then the `signature` is checked:
  * If there is no parameter corresponding to the string (i.e., the `param_specs` key doesn't match any parameter of the function being decorated), or if the corresponding parameter is a `**kwargs` parameter, then this parser argument will be treated as an optional "flags" argument (see below) that is always passed in the `**kwargs`.
  * If there is a matching parameter that has a default value, the parser argument will be marked as optional, and the function parameter's default value will be used as the parser's default value for the argument.
  * Finally, if the parameter has a type annotation, that annotation will be used as the `type` for the argument.

By default, the key from the `param_specs` entry will provide the name for the `ArgumentParser` argument. However, if a "flags" argument is being generated, this will be replaced by short and long forms of the flag syntax.

For example, if the `param_specs` dict maps `'flags'` to `'a flags argument'`, and there is no `flags` parameter for the function being decorated, then a flags argument is created. The call to `.add_argument` looks like `.add_argument(['-f', '--flags'], help='a flags argument')`. That is to say: when `-f foo` or `--flags foo` is specified on the command line, the parser will add `{'flags': 'foo'}` to the arguments dict used to invoke the entrypoint function.

### Custom invocation logic

Whatever function is supplied as `invoke` will receive a dict of parsed command-line arguments, and call the decorated function. It has two parameters:

* `func` - the decorated function itself.
* `args` - a dict of parsed command-line arguments.

The `.invoke` attribute attached to the decorated function is a wrapper that calls the `parser` created at decoration time on the supplied command line, and then uses that result to call `invoke`.

If you implement your own `invoke` function, you should use `entrypoints.invoke` to do the heavy lifting. See the last example in the "Examples" section to understand the main difficulty involved. You could however use this to preprocess the `args` or to add exception handling. 

### The default invoke function

The default implementation, after calling `parser(command_line)` to get a dict of parsed command-line arguments, does a little more than naively splatting them out. It will inspect the function's signature (again) to:

1. Do sanity checks - any failure of these arguments to satisfy the function's parameters is upgraded to an assertion failure, because it is a programming error - it indicates that the decorator is improperly configured.

2. Pass `*args` properly, if the function has a named `VAR_POSITIONAL` ("\*args") parameter. Basically, the corresponding value in the arguments dict will be iterated over to supply additional position arguments (an assertion failure occurs if the value is not iterable). Note that, if you write a custom `invoke` that makes use of the default `invoke`, you can be sure that any `TypeError` or `ValueError` raised came from your original function, since any incompatibility in arguments will become an assertion instead. (You could, of course, catch `AssertionError` here and tell the user to file a bug report.)

## Examples

There are a lot of layers to this, so examples are instructive. More examples can be seen in `examples.py`, and their behaviour is illustrated by the corresponding tests.

```python
@entrypoint(arg='documentation')
def my_entrypoint(arg:int):
    pass
```

This is the simplest usage. The argument parser that is generated will read a single, positional parameter from the command line. The entrypoint will be named `my_entrypoint`, so the command-line usage will look like `my_entrypoint <arg>`. The value supplied for `arg` on the command line will be converted to integer before the function is called (the `make_parser` implementation inspected the function signature to make this decision). The `invoke` function will receive a dict like `{'arg': <some integer value>}`, and use it to call `my_entrypoint`.

```python
@entrypoint(arg='documentation')
def my_entrypoint(**kwargs):
    pass
```

This time, there is no parameter named `arg`, so the argument parser will generate a flags argument that is passed in the `**kwargs`. The command-line usage will look like `my_entrypoint -a <arg>`, or `my_entrypoint --arg <arg>`, or `my_entrypoint` (the argument is optional). The `invoke` function will receive a dict that may or may not contain an `'arg'` key with a *string* value (since no type was specified). The default `invoke` function will call `my_entrypoint` such that `'arg'`, if specified, will be a key in `kwargs`.

```python
@entrypoint(tricky='documentation')
def my_entrypoint(**tricky):
    pass
```

This is an edge case. When called like `my_entrypoint -t example` (or `my_entrypoint --tricky example`), the string `'example'` will be the value of the *key* `'tricky'` within the `tricky` keyword arguments - it will not be parsed into a keyword arguments dict.

```python
@entrypoint(fancy={'help': 'fancy help', 'type': int, 'keyword': True})
def my_entrypoint(fancy):
    pass
```

This time, a dict is used to configure the parsing for `fancy`. The help text now must be explicitly labelled in the `'help'` key of the dict. No introspection is done (FIXME?), so we specify that the command-line argument will be converted to integer with the `'type'` key. These are both forwarded directly to `argparse.ArgumentParser.add_argument`. The `'keyword'` key requests a flags argument, so the call looks like `.add_argument(['-f', '--fancy'], help='fancy help', type=int)`. The command-line usage will look like `my_entrypoint -f 3`; the argument is mandatory even though it's provided by a flag.

```python
@entrypoints(args={nargs: '+', 'type': 'int', 'help': 'values'})
def my_entrypoint(*args):
    pass
```

This entrypoint expects one or more (per `argparse`'s syntax for `nargs`) integer values to be supplied: `my_entrypoint <x> [<y> [<z> ...]]`. The default `invoke` setup is capable of handling this seamlessly. Note that a naive implementation (like `return func(**parser(command_line))`) would fail, since a keyword argument cannot actually be used to supply values for variable-length positional parameters, even if the name matches.
