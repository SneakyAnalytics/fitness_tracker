"""Deprecated: use `python -m src.utils.reanalyze --start ... --end ...`.

Kept so existing commands keep working; delegates to the shared re-analysis path,
which honors manual workout matches.
"""
from src.utils.reanalyze import main

if __name__ == "__main__":
    main()
