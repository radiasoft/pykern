# pykern — pkio.Path Backwards-Compatibility Project

## Goal

Make `pkio.py_path` return a `pkio.Path` object that is backwards
compatible with `py.path` via duck typing, while being a true
`pathlib.Path` subclass. This allows backwards compatibility with
`py.path`. Only implement those methods in py.path.local that
are used in sirepo, rsconf, and other radiasoft repos. There is not a
strong dependency on py.path.local specifically so can rely on the
platform independence of using the py.path abstraction, not py.path.local

## Background

`pkio.py_path()` currently returns a `py.path.local`, but this is not
critical. Across RadiaSoft repos (sirepo, rsconf, radia-run, etc.)
there are hundreds of call sites using `py.path` methods (`join`,
`check`, `ensure`, `read`, `write`, `dirpath`, `ext`, `new`, `relto`,
`visit`, …) that have no direct equivalent in `pathlib.Path`.

## Approach

### 1. `pkio.Path` class

The plan: create `pkio.Path` — a `pathlib.Path` subclass — that adds the missing
`py.path.local` methods and wraps the signature-incompatible ones, then change
`py_path()` to return it.

### 2. Missing `py.path.local` methods to add

These are all the py.path methods, but only add those that are
missing. We are being backward compatible with py.path not forward
compatible with new uses.

| py.path method | pathlib equivalent or implementation |
|---|---|
| `join(*args)` | `self.joinpath(*args)` |
| `check(exists=True, file=False, dir=False, link=False)` | stat-based checks |
| `ensure(*args, dir=False)` | `mkdir(parents=True, exist_ok=True)` or `touch` |
| `ensure_dir(*args)` | `mkdir(parents=True, exist_ok=True)` |
| `read(mode='r')` | `read_text()` / `read_bytes()` |
| `write(content, mode='w', ensure=False)` | `write_text()` / `write_bytes()` |
| `read_binary()` | `read_bytes()` |
| `write_binary(content)` | `write_bytes(content)` |
| `readlines(cr=False)` | `read_text().splitlines(...)` |
| `dirpath(*args)` | `self.parent.joinpath(*args)` |
| `ext` | `self.suffix` (property) |
| `purebasename` | `self.stem` (property) |
| `basename` | `self.name` (property — already exists; alias for clarity) |
| `dirname` | `str(self.parent)` (property) |
| `new(**kwargs)` | construct new path with substituted components |
| `relto(other)` | `self.relative_to(other)` |
| `visit(pattern, fil, rec)` | `rglob` or `glob` based wrapper |
| `listdir(fil=None)` | `list(self.iterdir())` filtered |
| `isdir()` | `self.is_dir()` |
| `isfile()` | `self.is_file()` |
| `islink()` | `self.is_symlink()` |
| `exists()` | already in pathlib |
| `size()` | `self.stat().st_size` |
| `mtime()` | `self.stat().st_mtime` |
| `atime()` | `self.stat().st_atime` |
| `setmtime(mtime)` | `os.utime(self, (atime, mtime))` |
| `copy(target)` | `shutil.copy2(self, target)` |
| `move(target)` | `shutil.move(self, target)` |
| `remove()` | `self.unlink()` or `shutil.rmtree` |
| `realpath()` | `self.resolve()` |
| `chdir()` | `os.chdir(self)` |
| `as_cwd()` | context manager — `os.chdir` in/out |
| `mklinkto(target)` | `target.symlink_to(self)` |
| `mksymlinkto(target)` | `self.symlink_to(target)` |
| `fnmatch(pattern)` | `self.match(pattern)` |
| `pyimport()` | `importlib` based load |
| `dump(obj)` | pickle write |
| `load()` | pickle read |
| `computehash(hashtype)` | `hashlib` |
| `chown(user, group)` | `shutil.chown` |
| `chmod(mode)` | already in pathlib (same signature) |
| `sysexec(*args)` | `subprocess.check_output` |
| `bestrelpath(dest)` | `os.path.relpath` |
| `common(other)` | `os.path.commonpath` |

### 3. Signature collisions to handle

These exist in both `py.path.local` and `pathlib.Path` with incompatible signatures.
`pkio.Path` should accept BOTH calling conventions:

| Method | py.path signature | pathlib signature |
|---|---|---|
| `mkdir` | `mkdir(mode=0o777)` — also creates parents | `mkdir(mode=0o777, parents=False, exist_ok=False)` |
| `open` | `open(mode='r', ensure=False, encoding=None)` | standard `open()` |
| `parts` | method returning list | property returning tuple |
| `read_text` | `read_text(encoding=None)` (defaults UTF-8) | `read_text(encoding=None, errors=None)` |
| `stat` | `stat(raising=True)` — returns stat or None | `stat(follow_symlinks=True)` — raises on missing |
| `write_text` | `write_text(content, mode='w', encoding=None, ensure=False)` | `write_text(data, encoding=None, errors=None, newline=None)` |
| `rename` | `rename(target)` — returns new path | same but pathlib returns `Path` |

Strategy: inspect call signature at runtime while running both the
sirepo and pykern test suite to see which parameters are being passed
or do a static analysis to find which parameters are being passed to these methods. Not all mehods are being used. If there are one or two instances of these methods, they can perhaps be replaced. First produce a report of all the uses.


Expose `py.path`-style wrapper only when called with
`py.path`-style keyword arguments. Prefer making the method accept all
valid arguments from either API and dispatch.

### 4. `new(**kwargs)` implementation

`py.path.local.new` replaces path components by keyword:

```python
# e.g.
p.new(ext='txt')      # change extension
p.new(basename='foo') # change filename without extension
p.new(dirname='/tmp') # change parent dir
```

Implement by decomposing `self` into components, applying substitutions, and
reconstructing a new `pkio.Path`.

### 5. `parts` collision

`py.path.local.parts(reverse=False)` returns a list of path components.
`pathlib.Path.parts` is a property returning a tuple.

Safest fix: rename the `py.path` method to `parts_list()` in `pkio.Path` and keep
`parts` as the standard property. Update call sites.

## Migration Plan

1. **Audit call sites** — search all `~/src/radiasoft` repos for:
   - `py.path` direct usage
   - `.join(` `.check(` `.ensure(` `.read(` `.write(` `.dirpath(` `.ext` `.new(` `.relto(` `.visit(` `.purebasename` `.basename` `.dirname`
   - `import py` / `from py.path`
   - `py_path(` return value usage

   Use: `grep -r 'py\.path\|\.join(\|\.check(\|\.ensure(\|pyimport\|\.read(\|\.write(' --include='*.py{,.jinja}' ~/src/radiasoft/`

2. **Implement `pkio.Path`** in `pykern/pkio.py` — add class before `py_path()`.

3. **Change `py_path()`** to return `pkio.Path(...)` instead of `py.path.local(...)`.

4. **Run pykern tests** — `pykern test tests/`.

5. **Iterate over sirepo, rsconf** — run their test suites, fix any remaining
   `py.path`-specific method calls that `pkio.Path` doesn't yet cover.

6. **Long-term**: replace `py.path.local` type annotations with `pkio.Path` /
   `pathlib.Path` and remove `import py` from each module.

## Key Files

- `pykern/pkio.py` — add `pkio.Path` class here; modify `py_path()`
- `tests/pkio_test.py` — existing tests; extend with `pkio.Path` tests
- `pykern/pkunit.py` — uses `py_path`; verify still works after change

## Coding Style

Follow RadiaSoft style (see pykern wiki CodingStyle and DesignHints):
- Qualified imports (`import pykern.pkio`) except PKDict/pkdebug direct imports
- Single-letter temporaries for short-scope locals
- Alphabetical ordering of functions/methods
- Guard clauses; no deep nesting
- `raise AssertionError(...)` not bare `assert`
- No `sys.exit()` or `print()` in library code

## Running Tests

```bash
# from ~/src/radiasoft/pykern
pykern test tests/pkio_test.py
```
