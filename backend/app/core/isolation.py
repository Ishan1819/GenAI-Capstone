"""Run tests and experiments on a fresh copy of the data (paper, Section 4.7 / Table 6).

Every run copies the vector store, the SQLite logs, the demo records and the scraped pages into a temporary folder
and points DATA_DIR at it, so nothing queued or answered in one run can leak into the next or into the live app.

Must be called BEFORE any `app.*` module is imported, because config reads DATA_DIR at import time.
"""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

LIVE_DATA = Path(__file__).resolve().parents[2] / "data"


def use_fresh_copy(keep: bool = False, include_db: bool = True) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="isdic_run_"))
    dst = tmp / "data"
    if LIVE_DATA.exists():
        shutil.copytree(LIVE_DATA, dst, ignore=shutil.ignore_patterns("eval"))  # results stay in the live folder
    else:
        dst.mkdir(parents=True)
    if not include_db and (dst / "app.db").exists():
        (dst / "app.db").unlink()  # start with empty logs and an empty admin queue
    os.environ["DATA_DIR"] = str(dst)
    if not keep:
        atexit.register(shutil.rmtree, tmp, True)
    return dst
