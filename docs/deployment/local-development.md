Local dev: quick start for macOS

This project includes a small helper to make it easy to start the API (FastAPI/uvicorn)
and the Streamlit UI locally on macOS.

Prerequisites

- Python 3.11 installed (brew or system)
- Optional: use a clean virtualenv to avoid conflicts with system/conda packages

Quick commands (recommended)

1. Create and activate a venv (recommended):

   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt

2) Start app (two options):

   Option A - Double-click: `Fitness Tracker.app`

   Option B - Terminal script: `bin/start_app.sh`

   - Both will create `.venv` if missing (and instruct you how to install deps).
   - They use macOS `osascript` to open Terminal and run the API and Streamlit UI.

3) Stop app:

   bin/stop_app.sh

Notes and alternatives

- If you prefer to keep everything in one terminal, you can run in separate tabs or use tmux:
  - API: `uvicorn src.api.app:app --reload`
  - Streamlit: `streamlit run src/ui/streamlit_app.py`
- The `start_app.sh` script starts both in Terminal windows so you can view logs and stop them by closing the windows.
- If you have trouble with packages and your environment is Conda-managed, create an isolated venv as above to avoid conflicts.

If you'd like, I can also provide an Automator/AppleScript app bundle that you can double-click to start/stop the service.
