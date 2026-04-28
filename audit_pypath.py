import json
import re
import subprocess
import sys
from pathlib import Path

REPOS = ["pykern", "sirepo", "rsconf", "rsbeams", "rsdockerspawner", "rshellweg", "rslume"]
BASE = Path.home() / "src/radiasoft"

PYPATH_METHODS = [
    "join", "check", "ensure", "ensure_dir", "dirpath", "purebasename",
    "new", "relto", "visit", "listdir", "isfile", "isdir", "islink",
    "mtime", "setmtime", "size", "realpath", "bestrelpath", "remove",
    "mksymlinkto", "mklinkto", "read_binary", "write_binary", "read",
    "write", "readlines", "copy", "move", "rename", "parts", "fnmatch",
    "pyimport", "dump", "load", "chdir", "sysexec", "computehash",
    "chown", "basename", "dirname", "ext",
]

SKIP_PATH_RE = re.compile(
    r"/(build|dist|\.git|__pycache__|node_modules"
    r"|run/user/|tests/[^/]+_work/|tests/[^/]+_data/"
    r"|package_data/sphinx|/examples/)"
)

FALSE_POS = {
    "join": [
        re.compile(r'["\'].*\.join\('),
        re.compile(r'\.join\([^)]*["\']'),
        re.compile(r'(thread|process|pool|task)\.join\b'),
        re.compile(r'\.join\(\s*timeout'),
        re.compile(r'os\.path\.join'),
    ],
    "remove": [
        re.compile(r'os\.remove\b'),
        re.compile(r'os\.path\.remove'),
        # list.remove(element) — element is a variable or self
        re.compile(r'\.remove\(\s*(self|op|m|h|s|i|case|process|handler|key|value|item|elem|node|edge|line|col|row|name|kind)\s*\)'),
        re.compile(r'\b(instances|ops|cmds|cases|slots|hosts|labels|headers|signal_cascade|pending_msgs|params|args|items|keys|values|columns|rows|processes|handlers)\s*\.remove\('),
        re.compile(r'ax\.\w+\.remove\('),
        re.compile(r'#.*ZipFile.*remove|#.*remove.*method'),
    ],
    "copy": [
        re.compile(r'\.copy\(\s*\)'),
        re.compile(r'import copy\b|copy\.copy\b|copy\.deepcopy'),
        re.compile(r'shutil\.copy\b'),
        re.compile(r'(environ|http_config|edits)\.copy\('),
    ],
    "read": [
        re.compile(r'\b(f\d*|fp|fh|fd|reader|stream|socket|conn|self\.openf|response|resp|stdin|p\.stdout|p\.stderr|open_file|read_particle_data)\s*\.read\('),
        re.compile(r'sys\.(stdin|stdout|stderr)\.read'),
        re.compile(r'open\(.*\)\.read'),
        re.compile(r'hasattr\(.*"read"\)'),
        re.compile(r'zip_obj\.read|zipped.*\.read'),
        re.compile(r'\bobj\.read\('),
        re.compile(r'\.read\([^)]*pages='),
        re.compile(r'\.read\([^)]*["\'][a-z]'),   # read('elegant'), read('opal'), etc.
    ],
    "write": [
        re.compile(r'sys\.(stdin|stdout|stderr)\.write'),
        re.compile(r'await \w+\.write\('),
        re.compile(r'\bz\b\.write\(|zf\.write\(|zipped\['),
        re.compile(r'\.write\(.*\.encode\('),
        re.compile(r'\b(f\d+|fp|fh|fd|ff|outputFile|stream|writer|resp\b|result_file|self\.f\b)\s*\.write\('),
        re.compile(r'open\(.*\)\.write'),
        re.compile(r'sys\.\w+\.write'),
        # file handle named just 'f' followed by write with a string expression
        re.compile(r'\bf\s*\.write\('),
    ],
    "load": [
        re.compile(r'(json|yaml|pickle|numpy|np|yt|joblib|torch|h5py|scipy|toml|pyyaml|ruamel)\s*\.\s*load\b'),
        re.compile(r'importlib.*load|pkgutil.*load'),
        re.compile(r'json_load\b'),
    ],
    "dump": [
        re.compile(r'(json|yaml|pickle|numpy|np|joblib|torch|h5py|scipy|toml|pkyaml|pkjson)\s*\.\s*dump\b'),
    ],
    "ext": [
        re.compile(r'sphinx\.ext\.|extensions\s*=\s*\[|sphinx_ext'),
        re.compile(r'\bext\s*=\s*[\"\[{(]|ext_modules|file_ext|img_ext'),
        re.compile(r'#.*\.ext\b'),
    ],
    "parts":    [re.compile(r'["\'].*\.parts\(|body_parts|msg_parts|url_parts|form_parts')],
    "isdir":    [re.compile(r'os\.path\.isdir|os\.isdir')],
    "isfile":   [re.compile(r'os\.path\.isfile|os\.isfile')],
    "dirname":  [re.compile(r'os\.path\.dirname|os\.dirname')],
    "basename": [re.compile(r'os\.path\.basename|os\.basename')],
    "realpath": [re.compile(r'os\.path\.realpath')],
    "rename":   [re.compile(r'os\.rename\b')],
    "size": [
        re.compile(r'(font|batch|chunk|block|page|window|step|cell|grid|buf|buffer|max|min|map|key|data|input|output|sample|img|image)_?\.?size\b'),
        re.compile(r'\.size\s*[=\+\-\*]'),
        re.compile(r'\bnp\b.*\.size\b|numpy.*\.size\b'),
        re.compile(r'\bpayload\.size\(|client\(\)\.size\('),
    ],
    "chdir":    [re.compile(r'os\.chdir')],
    "readlines":[
        re.compile(r'\b(f\d*|fp|fh|fd|open_file|self\.\w*file)\s*\.readlines\('),
        re.compile(r'zip\(.*\.readlines\('),
    ],
}

def is_false_positive(method, code, filepath):
    if SKIP_PATH_RE.search(filepath):
        return True
    # rsbeams has no py.path usage — skip generic IO methods there
    if "rsbeams" in filepath and method in ("read", "write", "readlines", "dump", "load"):
        return True
    for pat in FALSE_POS.get(method, []):
        if pat.search(code):
            return True
    return False

results = []

for repo in REPOS:
    repo_dir = BASE / repo
    if not repo_dir.exists():
        continue

    method_pat = r"\.(" + "|".join(PYPATH_METHODS) + r")\("
    prop_pat = r"\.(purebasename|basename|dirname|ext)\b"

    for pat, is_prop in [(method_pat, False), (prop_pat, True)]:
        proc = subprocess.run(
            ["grep", "-r", "-n", "-P", "--include=*.py", pat, str(repo_dir)],
            capture_output=True, text=True
        )
        for raw in proc.stdout.splitlines():
            parts = raw.split(":", 2)
            if len(parts) < 3:
                continue
            filepath, lineno, code = parts[0], parts[1], parts[2]

            if re.search(r'os\.path\.(join|dirname|basename|realpath|isfile|isdir)', code):
                continue

            if is_prop:
                m = re.search(r'\.(purebasename|basename|dirname|ext)\b', code)
            else:
                m = re.search(r'\.(' + "|".join(PYPATH_METHODS) + r')\(', code)
            if not m:
                continue
            method = m.group(1)

            if is_false_positive(method, code, filepath):
                continue

            rel_file = str(Path(filepath).relative_to(BASE))
            results.append({
                "repo": repo,
                "file": rel_file,
                "line": int(lineno),
                "method": method,
                "code": code.rstrip(),
            })

results.sort(key=lambda r: (r["repo"], r["file"], r["line"]))

output = {
    "_note": (
        "py.path method usage audit across RadiaSoft repos. "
        "Methods 'read', 'write', 'remove', 'size', 'basename', 'dirname', 'ext' "
        "may contain residual false positives due to name collision with file handles "
        "and other Python objects. All other methods are high-confidence py.path calls."
    ),
    "_repos": REPOS,
    "_total": len(results),
    "entries": results,
}

out = BASE / "pykern/pypath_audit.json"
out.write_text(json.dumps(output, indent=2))
print(f"Written {len(results)} entries to {out}", file=sys.stderr)

from collections import Counter
by_repo_method = Counter((r["repo"], r["method"]) for r in results)
for (repo, method), count in sorted(by_repo_method.items()):
    print(f"  {repo:20s} {method:20s} {count}")
