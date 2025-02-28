# Fitness Tracker Development Guide

## Commands
- Run API: `uvicorn src.api.app:app --reload`
- Run UI: `streamlit run src/ui/streamlit_app.py`
- Run main app: `python main.py`
- Debug database: `sqlite3 data/fitness_data.db`

## Code Style
- **Imports**: Standard library → Third-party → Local modules
- **Typing**: Use type hints consistently (List, Dict, Optional, Any)
- **Formatting**: 4-space indentation, 100 character line limit
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Docstrings**: For all functions and classes
- **Error handling**: Use specific exceptions with meaningful error messages
- **Models**: Use dataclasses for data models
- **Logging**: Use the logging module instead of print statements

## Project Structure
- `src/api`: FastAPI endpoints
- `src/models`: Data models
- `src/storage`: Database interaction
- `src/ui`: Streamlit interface
- `src/utils`: Helper functions