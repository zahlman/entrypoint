# `entrypoint` - quick and easy entry points for Python packages

This package mainly provides two things: a clever decorator called `@entrypoint` that you can use to create entry points, and a command-line tool to discover the entry points you created this way and update `pyproject.toml` to reference them properly.

## The `@entrypoint` decorator

To create an entry point to your code, simply `from entrypoint import entrypoint`, and then use the `@entrypoint` decorator on the function that should serve as the entry point to your code. The decorator adds an `.invoke` member to the function, which is the actual entry point that should be referenced in your `pyproject.toml` (or `setup.py`).

### Basic usage

The decorator accepts only keyword arguments, and cannot be used in no-argument form. It can, however, be used with zero arguments (particularly useful if the decorated function also takes zero arguments).

These keyword arguments are treated specially:

* `invoke` - a callable that overrides the default logic for passing the parsed arguments to the function. The default `invoke` function is available as `entrypoint.invoke` to do the heavy lifting in custom implementations.

* `make_parser` - a callable that creates a *parser function* (see "Custom parser functions" and "The default `make_parser`").

* `name` - the (string) name of the entry point. This will be assigned to the `.entrypoint_name` attribute of the function for introspection purposes, and is used by the default parser function to create a command-line usage message for the entry point. It is also used for automatic update of `pyproject.toml` (see *"Discovery tool for entry points"*). By default, the function's `__name__` attribute is used.

* `description` - a description string for the entry point. This will be assigned to the `.entrypoint_desc` attribute of the function for introspection purposes, and is used by the default parser function to create a command-line usage message for the entry point. By default, the first line of the function's `__doc__` is used, or failing that, an empty string.

* `params` - if provided, this should be a dict that provides *parameter specifications* used by the `make_parser` callable. Otherwise, you can provide these as `**kwargs`. (This system allows you to have command-line arguments with names that would otherwise conflict, while still allowing the convenience of `**kwargs` in ordinary cases.)

The decorator does not wrap or replace the function, but instead registers it in a private registry and adds three attributes:

* `entrypoint_name` - described above
* `entrypoint_desc` - described above
* `invoke` - as mentioned in the introduction, this is the true entry point to the code that will be referenced in `pyproject.toml` or `setup.py`. This setup ensures that the original function can function normally as a part of your package's API when imported.

## Customization

### Custom parser functions

A parser function needs to accept a string (representing the command line, minus the program name) and return a dict of parsed arguments (mapping from string names to arbitrary objects). It will be created by a `make_parser` implementation, which returns a parser function and accepts four arguments:

* `name` - the (string) name of the entry point
* `desc` - the (string) description for the entry point
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

For example, if the `param_specs` dict maps `'flags'` to `'a flags argument'`, and there is no `flags` parameter for the function being decorated, then a flags argument is created. The call to `.add_argument` looks like `.add_argument(['-f', '--flags'], help='a flags argument')`. That is to say: when `-f foo` or `--flags foo` is specified on the command line, the parser will add `{'flags': 'foo'}` to the arguments dict used to invoke the function that serves as your entry point.

### Custom invocation logic

Whatever function is supplied as `invoke` will receive a dict of parsed command-line arguments, and call the decorated function. It has two parameters:

* `func` - the decorated function itself.
* `args` - a dict of parsed command-line arguments.

The `.invoke` attribute attached to the decorated function is a wrapper that calls the `parser` created at decoration time on the supplied command line, and then uses that result to call `invoke`.

If you implement your own `invoke` function, you should use `entrypoint.invoke` to do the heavy lifting. See the last example in the "Examples" section to understand the main difficulty involved. You could however use this to preprocess the `args` or to add exception handling.

### The default invoke function

The default implementation, after calling `parser(command_line)` to get a dict of parsed command-line arguments, does a little more than naively splatting them out. It will inspect the function's signature (again) to:

1. Do sanity checks - any failure of these arguments to satisfy the function's parameters is upgraded to an assertion failure, because it is a programming error - it indicates that the decorator is improperly configured.

2. Pass `*args` properly, if the function has a named `VAR_POSITIONAL` ("\*args") parameter. Basically, the corresponding value in the arguments dict will be iterated over to supply additional position arguments (an assertion failure occurs if the value is not iterable). Note that, if you write a custom `invoke` that makes use of the default `invoke`, you can be sure that any `TypeError` or `ValueError` raised came from your original function, since any incompatibility in arguments will become an assertion instead. (You could, of course, catch `AssertionError` here and tell the user to file a bug report.)

## Example decorator usage

There are a lot of layers to this, so examples are instructive. All of these and more are available via `from entrypoint import examples`.

```python
@entrypoint(arg='an argument')
def doc_example_1(arg:int):
    print(f'Doc example 1: arg={arg} of type {type(arg)}')
    return arg
```

This is the simplest usage. The argument parser that is generated will read a single, positional parameter from the command line. The entry point will be named `doc_example_1`, so the command-line usage will look like `doc_example_1 <arg>`. The value supplied for `arg` on the command line will be converted to integer before the function is called (the `make_parser` implementation inspected the function signature to make this decision). The `invoke` function will receive a dict like `{'arg': <some integer value>}`, and use it to call `my_entrypoint`.

```python
@entrypoint(arg='a normal argument', kwargs='a tricky argument')
def doc_example_2(**kwargs):
    print(f'Doc example 2: kwargs={kwargs}')
    return kwargs
```

This time, there is no parameter named `arg`, so the argument parser will generate a flags argument that is passed in the `**kwargs`. The logic for the other argument is more subtle. The parser will also generate a flag argument for `kwargs`, because even though that name matches the `**kwargs` parameter, it is a `VAR_KEYWORD` parameter. (The behaviour is specified this way because it would make no sense to try to specify arbitrary dict keys with a single flag argument on the command line. This does mean that, in general, the command-line interface does not necessarily expose the full functionality of the original function.)

The command-line usage will look like, for example `doc_example_2 -a arg -k tricky`. The flags may appear in either order, or in long form (`--arg` and `--kwargs`), and either or both may be omitted (omitted values will default to `None`). The `invoke` function will receive a dict that will contain `'arg'` and `'kwargs'` keys, and pass them both in the `**kwargs` dict.

```python
@entrypoint(fancy={'help': 'fancy help', 'type': int, 'keyword': True})
def doc_example_3(fancy):
    print(f'This is a fancy way to end up with {fancy} (of type {type(fancy)})')
    return fancy
```

This time, a dict is used to configure the parsing for `fancy`. The help text now must be explicitly labelled in the `'help'` key of the dict. No introspection is done (FIXME?), so we specify that the command-line argument will be converted to integer with the `'type'` key. These are both forwarded directly to `argparse.ArgumentParser.add_argument`. The `'keyword'` key requests a flags argument, so the call looks like `.add_argument(['-f', '--fancy'], help='fancy help', type=int)`. The command-line usage will look like `my_entrypoint -f 3`; the argument is mandatory even though it's provided by a flag.

```python
@entrypoint(args={'nargs': '*', 'type': int, 'help': 'values'})
def doc_example_4(*args):
    print(f'Finally, a test of variable positional arguments: {args}')
    return args
```

This entry point expects zero or more (per `argparse`'s syntax for `nargs`) integer values to be supplied: `my_entrypoint [<x> [<y> [<z> ...]]]`. The default `invoke` setup is capable of handling this seamlessly. Note that a naive implementation (like `return func(**parser(command_line))`) would fail, since a keyword argument cannot actually be used to supply values for variable-length positional parameters, even if the name matches.

## Command-line utilities

The `entrypoint` package has two entry points of its own (created and discovered using its own functionality, of course):

* `entrypoint-update-metadata` - used to discover entry points and rewrite `pyproject.toml`.

* `entrypoint-wrapper` - creates a wrapper `.bat` file in the current directory.

### Discovery tool for entry points

In your main project directory, run `entrypoint-update-metadata` (no arguments). It discovers uses of the `@entrypoint` decorator by recursively searching for `.py` files, dynamically importing each of them separately, and then seeing what ens up in the private registry of decorated functions. For each entry point, an appropriate line is written in the `tool.poetry.scripts` section of your `pyproject.toml` (TODO: support build systems other than Poetry).

### Wrapper creation

After installing your package (probably in editable mode), run `entrypoint-wrapper <name of entry point>` to create a wrapper .bat file or shell script (NOTE: while the platform is detected using `os.name`, this has not been tested on a non-Windows system) in the current directory. This is useful because it:

* provides a double-clickable shortcut;
* which opens a terminal window when double-clicked and keeps it open after the program has finished running (waiting for one more keypress);
* and which runs in the current directory rather than the Scripts directory (like a shortcut or symlink normally would).

You can use this for your own convenience with any package's entry points, not just ones created using this library. You could also run this as part of a post-install script to give your clients a desktop shortcut for your programs.