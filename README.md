# `epmanager` - quick and easy entry points for Python packages

## Purpose and contents

This package provides tools to help you create entry points for your Python code. Unlike other tools, the focus is on packages prepared and distributed in the modern way, rather than on replacing the `if __name__=='__main__':` block in one-off scripts. To this end, `epmanager` provides:

* A function decorator that creates a wrapper suitable for use as an entry point to your program, and attaches it as an attribute to the function. The intent is that your original API is untouched, while still producing an effective way to start using your code right from the command line.

* A command-line tool for scanning your project for such entry point wrappers and updating your `pyproject.toml` accordingly.

* A command-line tool to create shortcut scripts for the entry point executables created during installation. This makes it easier to run your code, for example, from the desktop in a graphical environment, by providing something double-clickable that runs with the desktop as working directory.

* A full suite of examples. In particular, the code examples in the documentation are made available as command-line entry points, as if you had set them up yourself. For example, the function `epmanager_example_1` below is available to use on the command line as `epmanager-example-1`. The `examples` module contains these examples and more; the corresponding command-line names for other functions (aside from the ones explicitly discussed here) are prefixed with `epmanager-`.

## The `@entrypoint` decorator - Basic Usage

To create an entry point to your code, simply import the decorator (`from epmanager import entrypoint`), and then decorate the function that should serve as the entry point to your code. A simple example:

```python
@entrypoint(arg='an argument')
def epmanager_example_1(arg:int):
    return f'arg={arg} of type {type(arg)}'
```

The decorator creates a wrapper that will parse the command line expecting a single, integer argument aside from the program name, like: `epmanager-example-1 3`. It knows that the parameter should be an integer because it inspects the signature of `doc_example_1` and uses the type annotation. When invalid input is received, `doc_example_1` will not be called, and an error message will be displayed.

By default, the decorator makes use of `argparse` default settings, so you also can use `epmanager-example-1 -h` to see a help message. The text `'an argument'` will be used to describe the `arg` command-line argument in error and help messages.

When valid input is received, the function will be called; the returned string will be printed; and the process will exit successfully. If the function were to raise an exception somehow, the exception (not a traceback) would be displayed on stderr, and the process would exit with a non-zero status code.

### Decorator arguments

The decorator requires parentheses and accepts only keyword arguments. In the basic usage, each keyword argument corresponds to one of the parameters of the function. We'll call these arguments *parameter specifications*. Such an argument can be either a string or a dict; a given string `s` is treated equivalently to a dict `{'help': s}`.

With the default settings, an `argparse.ArgumentParser` is created to parse the command-line arguments, and each parameter specification is used for an `.add_argument` call. This allows you to specify arguments explicitly, but the `@entrypoint` decorator will also make some inferences for you:

* As described above, type annotations can be used to determine parameter type. Specifically, if an annotation exists and is callable, it is used as a `type` parameter for the `.add_argument` call.

* If the specification corresponds to a parameter with a default value, that gets used as a `default` parameter for the `.add_argument` call - i.e., a default value for the command-line argument - and the command-line argument will be treated as optional (sets `nargs='?'` for non-flag arguments).

* If the name of the parameter specification starts with an underscore, a command-line option (or "flags" argument) is created, with names based off the provided name. Underscores are converted to hyphens; so for example, a specification like `_arg_test='an argument'` results in a command-line option with short name `-a` and long name `-arg-test`. This also happens if the specification doesn't correspond to any parameter, or corresponds to a \*\*kwargs parameter, of the decorated function.

* Otherwise, the name is just used as the name for that command-line argument in the syntax shown in the command help.

Anything specified explicitly will override the inferred values.

Here is an example showing the use of a dict as a parameter specification, and a leading underscore on the name:

```python
@entrypoint(_fancy={'help': 'fancy help', 'type': int})
def epmanager_example_2(fancy):
    return f'This is a fancy way to end up with {fancy} (of type {type(fancy)})'
```

The `'help'` key specifies the description of the `fancy` command-line argument that will appear in the usage message.  Since the parameter specification name starts with an underscore, the command has a `-f` or `--fancy` option. Since the underlying parameter has no default value and none was explicitly specified, the option is mandatory on the command line: `epmanager-example-2 -f 1`. Although there is no type annotation on the `fancy` parameter, the explicitly provided `'type'` setting will mandate an integer value.

### Effect of the decorator

The decorator assigns three attributes to the function:

* `.invoke` - the wrapper described above.

* `.entrypoint_name` - normally a copy of the `.__name__` of the function, but it can be overridden.

* `.entrypoint_desc` - documentation for the entry point. By default, this is taken from the first line of the function's `.__doc__`, if any; but it can also be overridden. It will be set to an empty string when no documentation is available; it will *not* be `None`.

### Using the parsed values in the function

The default configuration will do some sanity checks when the decorator is applied, and then create a wrapper that parses the command line (delegating to the `ArgumentParser`, maps the resulting parsed command-line arguments into function-call arguments, calls the function, and captures the output. If an exception is raised, the exception (not the stack trace) is printed to stderr and the process exits with nonzero status. If the call executes normally, the return value is printed to stdout and the process exits with zero status.

Each command-line argument that doesn't match a non-`**kwargs` function parameter will be passed in the \*\*kwargs, if available (otherwise, the potential for this occurring is detected in the above sanity checks and an exception is raised).

For example:

```python
@entrypoint(arg='a normal argument', kwargs='a tricky argument')
def epmanager_example_3(**kwargs):
    return f"kwargs['arg']={kwargs['arg']}, kwargs['kwargs']={kwargs['kwargs']}"
```

The format string here should be fairly self-explanatory - but to be explicit: the parameter specification for `arg` doesn't match a function parameter, and the one for `kwargs` only matches the `**kwargs` parameter itself. As a result, the function will be called with both values passed in the `**kwargs`.

A command-line argument having the same name as a `*args` function parameter will be splatted out (an exception occurs if it isn't iterable). For example:

```python
@entrypoint(args={'nargs': '*', 'type': int, 'help': 'values'})
def epmanager_example_4(*args):
    return f'Finally, a test of variable positional arguments: {args}'
```

The `args` command-line argument will read zero or more integer values and store them in a list, which is then splatted out to the `*args` function parameter. We might for example run `epmanager-example-4 1 2 3` and see a result `Finally, a test of variable positional arguments: (1, 2, 3)`. A call like `epmanager_example_4(**{'args': [1, 2, 3]})` would fail with a TypeError, so the implementation has to do some more processing to make this work - and in the process, it adds several sanity checks.

## Advanced usage

### Hooks for customization

While the decorator generally treats keyword arguments as parameter specifications, the following names are treated specially:

* `parser_class` - specifies a class that will be instantiated to create a *parser* responsible for parsing the command line. An abstract base class `Parser` is provided, along with the default implementation `DefaultParser` which delegates to `argparse.ArgumentParser` (as described above).

* `dispatch_class` - specifies a class that will be instantiated (really, any callable to be called) to create a *dispatcher* used to call the function given the parsed command-line arguments. An abstract base class `Dispatcher` is provided, along with the default implementation `DefaultDispatcher`

* `specs` - a dict used for disambiguation; key-value pairs here will be treated as parameter specifications, regardless of their names. This allows you to, for example, pass arguments properly to a decorated function with a parameter called `name`.

* `parser_args` - a dict used for disambiguation; key-value pairs here will be treated as configuration arguments for the parser class, regardless of their names. This allows you to, for example, have a custom parser class that expects a configuration argument called `specs` (although it's unclear why you'd want to do this).

* `name` - a replacement name for the command (overriding the default, which is to use the function's name).

* `description` - a replacement description for the command (overriding the default, which is to use the first line of the function's doc, or an empty string).

Any other keywords are treated as configuration arguments if they appear in a whitelist provided by the parser class, and parameter specifications otherwise.

### The Parser API

Sometimes you may wish to customize how arguments are parsed from the command line. To do this, you should subclass the `Parser` abstract base class.

**You will need to implement:**

```python
@abstractmethod
def setup(self, config:dict):
```

This is a hook for any setup work needed when constructing the instance. You should **not** override `__init__`, because the base class `__init__` needs to do things in a specific order, both before and after it calls the `setup` hook.

The `config` dict will contain at least `'name'` and `'description'` keys, as well as any others you specify, as described in the previous section.

```python
@abstractmethod
def add_option(self, name:str, deco_spec:dict, param_spec:dict) -> str:

@abstractmethod
def add_argument(self, name:str, deco_spec:dict, param_spec:dict) -> str:
```

After `setup`, these will be called repeatedly with each of the parameter specifications (passed as `deco_spec`; the corresponding keyword used in the decorator call is passed as `name`). `add_option` is called for command-line options (flags), and `add_argument` is called for normal command-line arguments.

The `param_spec` may contain `'type'` and/or `'default'` values that were inferred from the signature of the decorated function; they are kept separate in case you need to treat them differently from explicitly specified configuration.

These methods must return a string that gives the corresponding key that will appear in the dict returned by `.parse`. This will normally just be `name`; but for example the default implementation can override this if a `'dest'` is provided in `deco_spec`.

```python
@abstractmethod
def parse(self, command_line) -> dict:
```

This should parse the provided command line (provided as a list of tokens, such as from `sys.argv[1:]`) and return a dict mapping from parameter names to values.

**You may also wish to implement:**

```python
@classmethod
def config_keys(cls) -> set
```

If you override this, it provides keyword names that the `@entrypoint` decorator will use for configuration options, rather than for parameter specifications. By default, it returns an empty set; but note that `name` and `description` are hard-coded to appear in the configuration options anyway.

```python
def call_with(self, parsed_args:dict):
```

This is a hook method for calling the underlying decorated function, allowing you to add setup and tear-down behaviour that can be shared between entry points and which shouldn't be part of the function's logic (remember, a design goal here is that you can still use the function as part of your package's API).

The `parsed_args` will be the `dict` produced by your `parse` method. Use `self.raw_call(parsed_args)` to call the underlying function; this will ensure that the Dispatcher is used correctly to map the parsed arguments into function-call arguments.

The Parser API works this way - rather than, say, providing "setup" and "teardown" hooks and hard-coding the underlying call - because it's more flexible; for example, it lets you specify custom error handling in a natural way.

### The Dispatcher API

You will probably not need to implement your own Dispatcher class, but an API is provided just in case you want to customize the logic that maps from the Parser's `.parse` output into the actual function call.

The Dispatcher instance is passed to the Parser constructor, and the Parser will do all the communication with the Dispatcher.

**You will need to implement:**

```python
@abstractmethod
def __init__(self, param_specs:dict):
```

The constructor will accept a dict that maps from names of the decorated function's parameters, to `inspect.Parameter` instances characterizing them. You can use this to determine parameter kinds and annotations.

```python
@abstractmethod
def guarantee(self, signature_name:str):
```

The Parser will call this to indicate that it will parse a `signature_name` parameter and include it in the `args_dict` passed to `.invoke` (see below).

```python
@abstractmethod
def validate(self):
```

The parser will call this after it has finished `guarantee`ing all its parameters during construction. Use this to ensure that the parameters described are appropriate for calling the function; raise an exception otherwise.

```python
@abstractmethod
def invoke(self, func, args_dict:dict):
```

This should call the original decorated function (passed as `func`) using arguments provided by the Parser in the `args_dict`. This is where you implement the logic to map those values onto the function parameters.

## Command-line utilities

As described at the top, there are several command-line entry points provided by this package. In addition to the runnable examples, there is a discovery tool and a shortcut maker.

### Discovery tool for entry points

In your main project directory, run `epmanager-update-metadata` (no arguments). It discovers uses of the `@entrypoint` decorator by recursively searching for `.py` files, dynamically importing each of them separately, and then seeing what ens up in the private registry of decorated functions. For each entry point, an appropriate line is written in the `tool.poetry.scripts` section of your `pyproject.toml` (TODO: support build systems other than Poetry).

The tool is, of course, used to maintain this package's own `pyproject.toml`.

### Wrapper creation

After installing your package (probably in editable mode), run `epmanager-wrapper <name of entry point>` to create a wrapper .bat file or shell script (NOTE: while the platform is detected using `os.name`, this has not been tested on a non-Windows system) in the current directory. This is useful because it:

* provides a double-clickable shortcut;
* which opens a terminal window when double-clicked and keeps it open after the program has finished running (waiting for one more keypress);
* and which runs in the current directory rather than the Scripts directory (like a shortcut or symlink normally would).

You can use this for your own convenience with any package's entry points, not just ones created using this library. You could also run this as part of a post-install script to give your clients a desktop shortcut for your programs.
