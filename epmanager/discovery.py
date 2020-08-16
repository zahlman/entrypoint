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


@main.entrypoint(
    name='epmanager-update-metadata',
    _ignore={
        'help': 'list of folder names not to recurse into',
        'nargs': '*'
    }
)
def write_all(ignore=('__pycache__',)):
    """Discover entry points in all source files and update pyproject.toml."""
    with open('pyproject.toml') as f:
        data = toml.load(f)
    poetry = data['tool']['poetry']
    main._REGISTRY = {}
    _load_everything(poetry['name'], ignore)
    poetry['scripts'] = main._REGISTRY
    with open('pyproject.toml', 'w') as f:
        toml.dump(data, f)


@main.entrypoint(name='epmanager-wrapper', cmd='name of command to wrap')
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
