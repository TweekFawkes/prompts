# Tech Stack: PyCrucible Single-File Binaries

<tech_stack>
<packaging tool="PyCrucible" targets="Windows x64, macOS Apple Silicon, Linux x64 (Ubuntu LTS)">
Use PyCrucible (https://github.com/razorblade23/PyCrucible) to package the Python application into a single, self-contained executable per target platform. PyCrucible is a Rust-based builder that fuses the project source with `uv` so end users can run the app with **no pre-installed Python** and **no virtualenv setup** — just a single binary.

Choose PyCrucible (not PyInstaller, py2exe, cx_Freeze, or Nuitka) because:
- Output is ~2 MB of runner overhead plus project files (vs. 50–200 MB for PyInstaller)
- Dependency resolution is delegated to `uv`, so installs are fast and reproducible
- The same toolchain produces binaries for Windows, macOS, and Linux from one config
- It pairs naturally with the `uv`-managed Python toolchain already in use (see `python_uv.md`)

<project_layout>
Lay the project out so PyCrucible can find the entrypoint and resolve dependencies through `uv`:

```
project_root/
├── pyproject.toml          # uv-managed; includes [tool.pycrucible]
├── src/
│   └── main.py             # default entrypoint
└── dist/                   # build output (gitignored)
```

A `pyproject.toml` with `uv`-resolved dependencies is the **preferred** dependency source. PyCrucible also accepts `requirements.txt`, `pylock.toml`, `setup.py`, or `setup.cfg`, but new projects should use `pyproject.toml`.
</project_layout>

<configuration>
Define PyCrucible behavior in `pyproject.toml` under `[tool.pycrucible]`. Keep configuration in this file (not a separate `pycrucible.toml`) so all project metadata lives in one place.

```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # list project dependencies here; uv will resolve them
]

[tool.pycrucible]
entrypoint = "src/main.py"

[tool.pycrucible.options]
debug = false
extract_to_temp = false      # set true if the app should leave no trace on disk
delete_after_run = false     # set true to wipe extracted files after each run

[tool.pycrucible.patterns]
include = [
    "**/*.py",
    # add non-Python assets here, e.g. "src/templates/*.html", "src/static/**/*"
]
exclude = [
    "**/__pycache__/**",
    "**/*.pyc",
    ".venv/**/*",
    ".git/**/*",
]
```

Only `entrypoint` is required. Every other key has a sensible default; omit keys you do not need to override rather than restating defaults.
</configuration>

<install>
Install PyCrucible with `uv` (matches the rest of the toolchain — do not use `pip` directly):

```bash
uv tool install pycrucible
```

Verify the install:

```bash
pycrucible --version
```
</install>

<build_commands>
PyCrucible builds a binary for **the platform it is run on**. To produce binaries for all three target platforms, build on each platform natively (locally or via CI — see the `<github_actions_ci>` section below).

Build the binary from the project root:

```bash
# Linux x64 (run on Ubuntu LTS) → produces ./dist/myapp-linux-x64
pycrucible -e . -o ./dist/myapp-linux-x64

# macOS Apple Silicon (run on an arm64 Mac) → produces ./dist/myapp-macos-arm64
pycrucible -e . -o ./dist/myapp-macos-arm64

# Windows x64 (run on Windows) → produces .\dist\myapp-windows-x64.exe
pycrucible -e . -o .\dist\myapp-windows-x64.exe
```

Useful flags:
- `-e <dir>` — directory containing the Python project to embed (use `.` for the project root)
- `-o <path>` — output path for the resulting binary (include `.exe` on Windows)
- `--no-uv-embed` — skip embedding `uv` in the binary; the binary will download `uv` on first run (smaller binary, requires network on first run)
- `--debug` — emit verbose build output for troubleshooting

The first run of the produced binary on an end-user machine resolves and caches dependencies via `uv`. Subsequent runs start instantly.
</build_commands>

<github_actions_ci>
Producing binaries for all three target platforms from a single workflow requires a matrix build. Use the official PyCrucible action and a runner per target. Place this at `.github/workflows/release.yml`:

```yaml
name: Build cross-platform binaries

on:
  push:
    tags: ['v*']

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-latest
            artifact: myapp-linux-x64
            ext: ''
          - os: macos-latest          # Apple Silicon (arm64)
            artifact: myapp-macos-arm64
            ext: ''
          - os: windows-latest
            artifact: myapp-windows-x64
            ext: '.exe'
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - name: Build with PyCrucible
        uses: razorblade23/pycrucible-action@v1
        with:
          source: .
          output: dist/${{ matrix.artifact }}${{ matrix.ext }}
      - uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: dist/${{ matrix.artifact }}${{ matrix.ext }}
```

Notes:
- `macos-latest` on GitHub Actions is Apple Silicon (arm64); do not use `macos-13` or earlier x86 runners
- `ubuntu-latest` produces a glibc-linked binary compatible with Ubuntu LTS (22.04+) and equivalents
- After the matrix completes, attach the three artifacts to the GitHub Release in a follow-up job using `softprops/action-gh-release` if needed
</github_actions_ci>

<distribution_checklist>
Before shipping a built binary to end users, complete these steps in order:

1. Test the binary on a clean VM (no Python, no `uv` installed) for each target platform to confirm the no-Python-required guarantee holds
2. Code-sign the binary **after** PyCrucible has embedded the project — signing before embedding invalidates the signature:
   - macOS: `codesign --deep --force --sign "<Developer ID>" ./dist/myapp-macos-arm64`
   - Windows: `signtool sign /fd SHA256 /a .\dist\myapp-windows-x64.exe`
   - Linux: signing is not standard; publish a detached GPG signature alongside the binary
3. Pin `requires-python` and all dependencies in `pyproject.toml` to specific versions so builds are reproducible
4. Record the SHA-256 of each released binary in the GitHub Release notes so users can verify integrity
</distribution_checklist>

</packaging>
</tech_stack>
