#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

choose_python() {
    if [ -n "${PYTHON_BIN:-}" ]; then
        printf '%s\n' "${PYTHON_BIN}"
        return 0
    fi

    local candidate
    for candidate in \
        /opt/homebrew/bin/python3.13 \
        /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 \
        /opt/homebrew/bin/python3.12 \
        /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 \
        python3.13 \
        python3.12 \
        python3
    do
        if command -v "${candidate}" >/dev/null 2>&1; then
            printf '%s\n' "$(command -v "${candidate}")"
            return 0
        fi
    done

    return 1
}

PYTHON_BIN="$(choose_python)"

if [ -z "${PYTHON_BIN}" ]; then
    echo "error: could not find a usable Python interpreter." >&2
    exit 1
fi

if "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if "Anaconda" in sys.version or "conda" in sys.executable.lower() else 1)
PY
then
    echo "warning: ${PYTHON_BIN} is backed by Anaconda/conda." >&2
    echo "warning: prefer a non-Conda Python 3.13 or 3.12 if available." >&2
fi

echo "Project root: ${ROOT_DIR}"
echo "Python: ${PYTHON_BIN}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "error: ${PYTHON_BIN} was not found." >&2
    echo "Install Python 3.12 and rerun, or override with PYTHON_BIN=python3." >&2
    exit 1
fi

if [ -d "${VENV_DIR}" ]; then
    echo "Removing existing virtual environment at ${VENV_DIR}"
    VENV_DIR_TO_REMOVE="${VENV_DIR}" "${PYTHON_BIN}" - <<'PY'
import os
from pathlib import Path
import shutil
import sys

venv_dir = Path(os.environ["VENV_DIR_TO_REMOVE"])
shutil.rmtree(venv_dir, ignore_errors=True)

if venv_dir.exists():
    for path in sorted(venv_dir.rglob("*"), reverse=True):
        try:
            if path.is_file() or path.is_symlink():
                path.unlink()
            else:
                path.rmdir()
        except FileNotFoundError:
            pass
        except OSError:
            pass
    try:
        venv_dir.rmdir()
    except OSError as exc:
        print(f"error: could not fully remove {venv_dir}: {exc}", file=sys.stderr)
        sys.exit(1)
PY
fi

echo "Creating fresh virtual environment..."
"${PYTHON_BIN}" -m venv "${VENV_DIR}"

echo "Upgrading packaging tools..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

echo "Installing project dependencies..."
"${VENV_DIR}/bin/pip" install -r "${ROOT_DIR}/requirements.txt"

export MPLCONFIGDIR="${TMPDIR:-/tmp}/eeg_analyse_mpl"
export XDG_CACHE_HOME="${TMPDIR:-/tmp}/eeg_analyse_cache"
mkdir -p "${MPLCONFIGDIR}"
mkdir -p "${XDG_CACHE_HOME}"

echo "Running import smoke test..."
"${VENV_DIR}/bin/python" -c "
import importlib.util

print(f'numpy OK: {importlib.util.find_spec(\"numpy\").origin}')
print(f'scipy OK: {importlib.util.find_spec(\"scipy\").origin}')
print(f'mne_lsl OK: {importlib.util.find_spec(\"mne_lsl\").origin}')
print(f'muselsl OK: {importlib.util.find_spec(\"muselsl\").origin}')
print(f'WEB_APP OK: {importlib.util.find_spec(\"WEB_APP\").origin}')
"

cat <<'EOF'

Fresh environment created successfully.

Use it with:
  source .venv/bin/activate
  python main.py
EOF
