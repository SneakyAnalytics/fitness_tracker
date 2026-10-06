"""Consistent SQLite backup inside the container; keeps the newest 10.

Shipped by deploy_to_beelink.sh so it also works against older images.
"""
import datetime
import glob
import os
import sqlite3

SRC = "/app/data/fitness_data.db"
DIR = "/app/data/backups"
os.makedirs(DIR, exist_ok=True)
dest = os.path.join(DIR, f"fitness_data_{datetime.datetime.now():%Y%m%d_%H%M%S}.db")
target = sqlite3.connect(dest)
sqlite3.connect(SRC).backup(target)
target.close()
for old in sorted(glob.glob(os.path.join(DIR, "fitness_data_*.db")))[:-10]:
    os.remove(old)
print(f"backup ok: {dest} ({os.path.getsize(dest) // 1_000_000} MB)")
