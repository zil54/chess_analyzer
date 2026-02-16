cd "$(dirname "$0")/.."
python3 -mvenv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python -m backend.main
