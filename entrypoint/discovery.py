import importlib, os
import toml
from . import main


def _is_module_or_package(path, name, ignore):
    if os.path.isdir(os.path.join(path, name)):
        return None if name in ignore else name
    else:
        name, ext = os.path.splitext(name)
        return name if ext == '.py' else None


def _load_everything(qualname, ignore):
    module_or_package = importlib.import_module(qualname)
    if hasattr(module_or_package, '__path__'):
        for path in module_or_package.__path__:
            for name in os.listdir(path):
                fixed_name = _is_module_or_package(path, name, ignore)
                if fixed_name is not None:
                    _load_everything(f'{qualname}.{fixed_name}', ignore)


# This only works properly on a fresh run, where nothing has been cached yet.
def _discover_entrypoints(qualname, convert, prefix, ignore=('__pycache__',)):
    _load_everything(qualname, ignore)
    return {
        prefix + (k.replace('_', '-') if convert else k): v
        for k, v in main._REGISTRY.items()
    }


@main.entrypoint(
    name='update-metadata',
    _keep_underscores={
        'help': 'preserve underscores instead of converting to hyphens',
        'action': 'store_false', 'dest': 'convert'
    },
    _prefix='text prefixed to all executable names'
)
def write_all(convert=True, prefix=''):
    """Discover entry points in all source files and update pyproject.toml."""
    with open('pyproject.toml') as f:
        data = toml.load(f)
    poetry = data['tool']['poetry']
    poetry['scripts'] = _discover_entrypoints(poetry['name'], convert, prefix)
    with open('pyproject.toml', 'w') as f:
        toml.dump(data, f)


@main.entrypoint(name='wrapper', cmd='name of command to wrap')
def make_wrapper_script(cmd):
    """Create a wrapper that runs the specified command locally and pauses."""
    if os.name == 'nt':
        template, ext = '@{exe}\n@pause', '.bat'
    else:
        # https://stackoverflow.com/questions/24016046/
        # Needs testing!
        template = '{exe}\necho "Press any key to continue . . ."\nread -rsn1'
        ext = ''
    try:
        pythonroot = os.environ['VIRTUAL_ENV']
    except KeyError:
        print('WARNING: No active virtualenv; using main Python installation.')
        pythonroot, _ = os.path.split(sys.executable)
    exe = os.path.join(pythonroot, 'Scripts', cmd)
    with open(f'{cmd}{ext}', 'w') as f:
        f.write(template.format(exe=exe))
