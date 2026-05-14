"""Scan history utilities — discover, parse, and manage scan output files."""
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from dummy_root import get_app_root


# Scanner type → output directory name
SCAN_DIRS: Dict[str, str] = {
    "kingdom": "scans_kingdom",
    "alliance": "scans_alliance",
    "honor": "scans_honor",
    "seed": "scans_seed",
}

# Regex to parse the standard scan filename convention:
#   TOP300-2026-04-25-test-[qqj2tu6y].xlsx
#   NEXT296-2026-04-25-mykd-[abc12345].csv
_FILENAME_RE = re.compile(
    r"^(?P<prefix>TOP|NEXT)"
    r"(?P<count>\d+)"
    r"-(?P<date>\d{4}-\d{2}-\d{2})"
    r"-(?P<kingdom>.+?)"
    r"-\[(?P<run_id>[a-z0-9]+)\]"
    r"\.(?P<ext>xlsx|csv|jsonl)$",
    re.IGNORECASE,
)


def parse_scan_filename(filename: str, scan_type: str) -> Optional[Dict[str, Any]]:
    """Extract metadata from a scan output filename.

    Returns a dict with keys: prefix, governor_count, date, kingdom_name,
    run_id, format, scan_type.  Returns None if the filename doesn't match.
    """
    m = _FILENAME_RE.match(filename)
    if not m:
        return None
    return {
        "scan_type": scan_type,
        "prefix": m.group("prefix").upper(),
        "governor_count": int(m.group("count")),
        "date": m.group("date"),
        "kingdom_name": m.group("kingdom"),
        "run_id": m.group("run_id"),
        "format": m.group("ext").lower(),
    }


def list_all_scans() -> List[Dict[str, Any]]:
    """Discover all scan output files across all scanner types.

    Returns a list of metadata dicts sorted by modification time (newest first).
    """
    root = get_app_root()
    history: List[Dict[str, Any]] = []

    for scan_type, folder_name in SCAN_DIRS.items():
        scan_dir = root / folder_name
        if not scan_dir.is_dir():
            continue
        for entry in scan_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in (".xlsx", ".csv", ".jsonl"):
                continue

            meta = parse_scan_filename(entry.name, scan_type)
            if meta is None:
                # File doesn't match the naming convention — include with minimal info
                meta = {
                    "scan_type": scan_type,
                    "prefix": "UNKNOWN",
                    "governor_count": 0,
                    "date": "",
                    "kingdom_name": entry.stem,
                    "run_id": "",
                    "format": entry.suffix.lstrip(".").lower(),
                }

            stat = entry.stat()
            meta["path"] = str(entry)
            meta["filename"] = entry.name
            meta["size_bytes"] = stat.st_size
            meta["modified"] = stat.st_mtime

            history.append(meta)

    # Sort newest first
    history.sort(key=lambda x: x["modified"], reverse=True)
    return history


def delete_scan_file(path: str) -> bool:
    """Delete a scan output file. Returns True on success."""
    p = Path(path)
    if not p.is_file():
        return False

    # Safety: only allow deleting files inside known scan directories
    root = get_app_root()
    allowed_dirs = [root / d for d in SCAN_DIRS.values()]
    if not any(_is_subpath(p, d) for d in allowed_dirs):
        return False

    p.unlink()
    return True


def get_scan_folder(scan_type: str) -> Optional[str]:
    """Return the absolute path to a scan type's output directory."""
    folder_name = SCAN_DIRS.get(scan_type)
    if folder_name is None:
        return None
    folder = get_app_root() / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder)


def _is_subpath(child: Path, parent: Path) -> bool:
    """Check if child is inside parent directory."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _safe_val(v: Any) -> Any:
    """Convert pandas/numpy values to JSON-safe Python types."""
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    if hasattr(v, "item"):  # numpy scalar
        return v.item()
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v


def read_scan_file(path: str) -> pd.DataFrame:
    """Read a scan output file (xlsx, csv, or jsonl) into a DataFrame."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext == ".xlsx":
        df = pd.read_excel(p, engine="openpyxl")
    elif ext == ".csv":
        df = pd.read_csv(p)
    elif ext == ".jsonl":
        df = pd.read_json(p, lines=True)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    return df


def compute_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute aggregate statistics from a scan DataFrame."""

    def _col_stat(col: str, stat: str) -> Any:
        if col not in df.columns:
            return None
        series = pd.to_numeric(df[col], errors="coerce")
        if stat == "mean":
            return _safe_val(series.mean())
        elif stat == "max":
            return _safe_val(series.max())
        elif stat == "min":
            return _safe_val(series.min())
        elif stat == "sum":
            return _safe_val(series.sum())
        return None

    return {
        "total_governors": len(df),
        "avg_power": _col_stat("Power", "mean"),
        "max_power": _col_stat("Power", "max"),
        "total_power": _col_stat("Power", "sum"),
        "avg_killpoints": _col_stat("Killpoints", "mean"),
        "max_killpoints": _col_stat("Killpoints", "max"),
        "avg_deaths": _col_stat("Deads", "mean"),
        "max_deaths": _col_stat("Deads", "max"),
        "total_kills": _col_stat("Total Kills", "sum"),
        "columns": list(df.columns),
    }


def get_scan_detail(
    path: str, page: int = 1, page_size: int = 50
) -> Dict[str, Any]:
    """Read a scan file and return paginated rows + summary.

    Args:
        path: Absolute path to the scan file.
        page: 1-based page number.
        page_size: Number of rows per page.

    Returns:
        Dict with keys: path, columns, rows, summary, page, page_size, total_rows, total_pages.
    """
    df = read_scan_file(path)
    summary = compute_summary(df)

    total_rows = len(df)
    total_pages = max(1, math.ceil(total_rows / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    end = start + page_size
    page_df = df.iloc[start:end]

    # Convert rows to JSON-safe dicts
    rows = []
    for _, row in page_df.iterrows():
        rows.append({k: _safe_val(v) for k, v in row.items()})

    return {
        "path": path,
        "columns": list(df.columns),
        "rows": rows,
        "summary": summary,
        "page": page,
        "page_size": page_size,
        "total_rows": total_rows,
        "total_pages": total_pages,
    }


def compare_scans(path_a: str, path_b: str) -> Dict[str, Any]:
    """Compare two scan files and return a structured diff.

    Joins on governor ID (or Name if ID is missing). Returns:
    - summary_a / summary_b: aggregate stats for each scan
    - added: governors in B but not A
    - removed: governors in A but not B
    - changed: governors present in both with differing numeric fields
    """
    df_a = read_scan_file(path_a)
    df_b = read_scan_file(path_b)

    summary_a = compute_summary(df_a)
    summary_b = compute_summary(df_b)

    # Determine the join key: prefer ID, fall back to Name
    join_col = "ID" if "ID" in df_a.columns and "ID" in df_b.columns else "Name"

    if join_col not in df_a.columns or join_col not in df_b.columns:
        # Can't join — return summaries only
        return {
            "summary_a": summary_a,
            "summary_b": summary_b,
            "added": [],
            "removed": [],
            "changed": [],
            "join_key": None,
        }

    # Build lookup dicts keyed by join_col
    set_a = set()
    map_a: Dict[Any, Dict[str, Any]] = {}
    for _, row in df_a.iterrows():
        key = _safe_val(row.get(join_col))
        if key is not None:
            set_a.add(key)
            map_a[key] = {k: _safe_val(v) for k, v in row.items()}

    set_b = set()
    map_b: Dict[Any, Dict[str, Any]] = {}
    for _, row in df_b.iterrows():
        key = _safe_val(row.get(join_col))
        if key is not None:
            set_b.add(key)
            map_b[key] = {k: _safe_val(v) for k, v in row.items()}

    # Added = in B but not A
    added_keys = set_b - set_a
    added = [map_b[k] for k in added_keys]

    # Removed = in A but not B
    removed_keys = set_a - set_b
    removed = [map_a[k] for k in removed_keys]

    # Changed = in both, with at least one numeric field that differs
    numeric_cols = [
        c for c in df_a.columns
        if c != join_col and pd.api.types.is_numeric_dtype(df_a[c])
    ]

    changed = []
    for key in set_a & set_b:
        row_a = map_a[key]
        row_b = map_b[key]
        diffs: Dict[str, Dict[str, Any]] = {}
        for col in numeric_cols:
            val_a = row_a.get(col)
            val_b = row_b.get(col)
            if val_a is None and val_b is None:
                continue
            if val_a != val_b:
                diffs[col] = {"old": val_a, "new": val_b}

        if diffs:
            changed.append({
                join_col: key,
                "name": row_b.get("Name", row_a.get("Name", "")),
                "changes": diffs,
            })

    # Sort changed by biggest power delta (if Power column exists)
    changed.sort(
        key=lambda c: abs(
            (c["changes"].get("Power", {}).get("new") or 0)
            - (c["changes"].get("Power", {}).get("old") or 0)
        ),
        reverse=True,
    )

    return {
        "summary_a": summary_a,
        "summary_b": summary_b,
        "added": added,
        "removed": removed,
        "changed": changed,
        "join_key": join_col,
    }
