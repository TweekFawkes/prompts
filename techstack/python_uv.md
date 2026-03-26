# Tech Stack: Python with uv

<tech_stack>
<python version="3.11" package_manager="uv">
Use Python 3.11 managed entirely through uv (https://github.com/astral-sh/uv).

Standard commands:
- Install Python: `uv python install 3.11`
- Create virtualenv: `uv venv --python 3.11`
- Install dependencies: `uv pip install -r requirements.txt`

Always use `uv` instead of `pip`, `venv`, `pyenv`, or `conda`. This keeps the toolchain consistent across all environments.
</python>
</tech_stack>
