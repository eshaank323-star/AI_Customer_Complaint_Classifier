"""
data_manager.py
===============
Everything that reads or writes the complaints CSV file (using Pandas).

Safety rules used in this file:
  * New complaints are APPENDED. The whole file is loaded, the new row is added,
    and everything is saved again, so old records are never overwritten.
  * The file is saved to a temporary file first and then swapped in, so a crash
    in the middle of saving cannot leave a half-written CSV.
  * Missing values are replaced with safe text, and duplicate IDs are repaired.
"""

import os
import re
import shutil
import threading
from datetime import datetime

import numpy as np
import pandas as pd

from classifier import CATEGORIES

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

COLUMNS = [
    "Complaint ID",
    "Customer Name",
    "Complaint Title",
    "Complaint Description",
    "Predicted Category",
    "Priority",
    "Assigned Team",
    "Status",
    "Submission Date",
    "Source",            # "Sample" = demo record, "User" = submitted through the form
]

STATUSES = ["Pending", "In Progress", "Resolved"]
PRIORITIES = ["High", "Medium", "Low"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, "data", "complaints.csv")

# Stops two requests from writing the file at the same moment.
_file_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Loading and cleaning
# ---------------------------------------------------------------------------

def create_empty_dataframe():
    """An empty table that already has the correct columns."""
    return pd.DataFrame(columns=COLUMNS)


def ensure_csv_exists(csv_path=DEFAULT_CSV_PATH):
    """Create the data folder and an empty CSV (header only) if missing."""
    folder = os.path.dirname(csv_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    if not os.path.exists(csv_path):
        create_empty_dataframe().to_csv(csv_path, index=False, encoding="utf-8-sig")


def _id_number(complaint_id):
    """'CMP-0007' -> 7. Returns None for IDs in any other format."""
    match = re.fullmatch(r"CMP-(\d+)", str(complaint_id).strip().upper())
    return int(match.group(1)) if match else None


def generate_complaint_id(df):
    """Make a new unique ID such as CMP-0021 (highest existing number + 1)."""
    numbers = [n for n in (_id_number(i) for i in df["Complaint ID"]) if n is not None]
    next_number = int(np.max(numbers)) + 1 if numbers else 1
    return f"CMP-{next_number:04d}"


def fix_duplicate_ids(df):
    """Give a new ID to any row whose ID is blank or already used above it."""
    seen = set()
    for index in df.index:
        complaint_id = df.at[index, "Complaint ID"]
        if complaint_id == "" or complaint_id in seen:
            complaint_id = generate_complaint_id(df)
            df.at[index, "Complaint ID"] = complaint_id
        seen.add(complaint_id)
    return df


def clean_dataframe(df):
    """Make sure the table has every column and no missing or invalid values."""
    for column in COLUMNS:
        if column not in df.columns:
            df[column] = ""
    df = df[COLUMNS].copy()

    for column in COLUMNS:
        df[column] = df[column].fillna("").astype(str).str.strip()

    df["Customer Name"] = df["Customer Name"].replace("", "Anonymous")
    df["Complaint Title"] = df["Complaint Title"].replace("", "Untitled complaint")
    df["Source"] = df["Source"].replace("", "User")
    df.loc[~df["Status"].isin(STATUSES), "Status"] = "Pending"
    df.loc[~df["Priority"].isin(PRIORITIES), "Priority"] = "Medium"

    df = df.reset_index(drop=True)
    return fix_duplicate_ids(df)


def load_complaints(csv_path=DEFAULT_CSV_PATH):
    """Read the CSV file safely and return a clean DataFrame."""
    ensure_csv_exists(csv_path)
    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:          # completely empty file
        df = create_empty_dataframe()
    except (pd.errors.ParserError, UnicodeDecodeError):
        # Damaged file: keep a backup copy so nothing is lost, then start fresh.
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(csv_path, f"{csv_path}.damaged_{stamp}.bak")
        df = create_empty_dataframe()
    return clean_dataframe(df)


def save_complaints(df, csv_path=DEFAULT_CSV_PATH):
    """Save the whole table safely (temporary file first, then replace)."""
    temp_path = csv_path + ".tmp"
    df[COLUMNS].to_csv(temp_path, index=False, encoding="utf-8-sig")
    os.replace(temp_path, csv_path)


# ---------------------------------------------------------------------------
# Adding, finding and updating complaints
# ---------------------------------------------------------------------------

def add_complaint(customer_name, title, description, analysis,
                  csv_path=DEFAULT_CSV_PATH, source="User", submission_date=None):
    """
    Add one new complaint to the CSV file and return the saved record.
    `analysis` is the dictionary returned by classifier.analyze_complaint().
    """
    with _file_lock:
        df = load_complaints(csv_path)             # keep every old record

        new_id = generate_complaint_id(df)
        while new_id in set(df["Complaint ID"]):   # extra safety against duplicates
            new_id = f"CMP-{int(new_id[4:]) + 1:04d}"

        record = {
            "Complaint ID": new_id,
            "Customer Name": (customer_name or "").strip() or "Anonymous",
            "Complaint Title": (title or "").strip() or "Untitled complaint",
            "Complaint Description": (description or "").strip(),
            "Predicted Category": analysis["category"],
            "Priority": analysis["priority"],
            "Assigned Team": analysis["team"],
            "Status": "Pending",
            "Submission Date": submission_date or datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Source": source,
        }

        df.loc[len(df)] = [record[column] for column in COLUMNS]   # append a row
        save_complaints(df, csv_path)
    return record


def get_complaint_by_id(complaint_id, csv_path=DEFAULT_CSV_PATH):
    """Return one complaint as a dictionary, or None if it does not exist."""
    df = load_complaints(csv_path)
    match = df[df["Complaint ID"] == str(complaint_id).strip()]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def update_status(complaint_id, new_status, csv_path=DEFAULT_CSV_PATH):
    """
    Change the status of one complaint.
    Returns True if updated, False if the ID was not found.
    Raises ValueError if the status is not Pending / In Progress / Resolved.
    """
    if new_status not in STATUSES:
        raise ValueError(f"Invalid status: {new_status!r}")

    with _file_lock:
        df = load_complaints(csv_path)
        rows = df["Complaint ID"] == str(complaint_id).strip()
        if not rows.any():
            return False
        df.loc[rows, "Status"] = new_status
        save_complaints(df, csv_path)
    return True


# ---------------------------------------------------------------------------
# Searching, filtering and statistics
# ---------------------------------------------------------------------------

def sort_newest_first(df):
    """Newest complaints first."""
    dates = pd.to_datetime(df["Submission Date"], errors="coerce")
    ordered = df.assign(_date=dates).sort_values(
        ["_date", "Complaint ID"], ascending=[False, False])
    return ordered.drop(columns="_date")


def filter_complaints(df, search="", category="All", priority="All", status="All"):
    """
    Filter by category, priority and status, and search in ID, name, title
    and description (not case-sensitive). 'All' means no filter.
    """
    result = df.copy()
    if category in CATEGORIES:
        result = result[result["Predicted Category"] == category]
    if priority in PRIORITIES:
        result = result[result["Priority"] == priority]
    if status in STATUSES:
        result = result[result["Status"] == status]

    search = (search or "").strip()
    if search and not result.empty:
        text = (result["Complaint ID"] + " " + result["Customer Name"] + " "
                + result["Complaint Title"] + " " + result["Complaint Description"])
        result = result[text.str.contains(search, case=False, regex=False)]
    return result


def _count_by(df, column, order):
    """Count rows per value, always listing every value (0 if none)."""
    counts = df[column].value_counts().reindex(order, fill_value=0)
    return {name: int(counts[name]) for name in order}


def get_statistics(df):
    """Numbers used by the dashboard and the charts. Works with an empty table."""
    total = len(df)
    status_counts = _count_by(df, "Status", STATUSES)
    resolved_percent = 0.0
    if total > 0:
        resolved_percent = float(np.round(status_counts["Resolved"] / total * 100, 1))

    return {
        "total": total,
        "high_priority": int((df["Priority"] == "High").sum()),
        "pending": status_counts["Pending"],
        "in_progress": status_counts["In Progress"],
        "resolved": status_counts["Resolved"],
        "resolved_percent": resolved_percent,
        "category_counts": _count_by(df, "Predicted Category", CATEGORIES),
        "priority_counts": _count_by(df, "Priority", PRIORITIES),
        "status_counts": status_counts,
    }


def get_recent_complaints(df, how_many=5):
    """The newest complaints as a list of dictionaries."""
    return sort_newest_first(df).head(how_many).to_dict("records")
