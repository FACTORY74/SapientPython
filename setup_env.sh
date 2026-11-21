#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    PATH="$HOME/.local/bin:$PATH"
    export PATH
fi

sapient_venv="${SAPIENT_VENV:-.venv}"

if [ ! -x "$sapient_venv/bin/python" ]; then
    uv venv --python 3.15 "$sapient_venv"
fi
uv pip install --python "$sapient_venv/bin/python" -r requirements.txt -e .
"$sapient_venv/bin/python" scripts/quick_test.py
"$sapient_venv/bin/python" -m pytest

echo "SAPIENT environment is ready."
echo "Activate it with: . $sapient_venv/bin/activate"
