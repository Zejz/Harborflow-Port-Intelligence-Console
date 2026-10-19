"""File loading and path-handling functions for HarborFlow.

All file access lives here. Paths are relative to the project root, so the
console must be started from the project root with: python main.py
"""
import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path

DATASET_DIR = Path("dataset")
VESSELS_DIR = DATASET_DIR / "vessels"
MANIFESTS_DIR = DATASET_DIR / "manifests"
SHIPMENTS_DIR = DATASET_DIR / "shipments"
INCIDENTS_DIR = DATASET_DIR / "incidents"
PORT_CALLS_FILE = DATASET_DIR / "port_calls.csv"

EXPORTS_DIR = Path("exports")
CUSTOMER_PROFILES_FILE = EXPORTS_DIR / "customer-profiles.csv"
SANITIZED_DIR = EXPORTS_DIR / "sanitized"

VESSEL_FIELDS = {"vessel_id", "name", "imo", "capacity_teu"}
SHIPMENT_FIELDS = {"shipment_id", "customer", "destination", "weight_kg", "priority"}
MANIFEST_FIELDS = {"call_id", "vessel_id", "shipment_ids", "event_codes"}
INCIDENT_FIELDS = {"incident_id", "call_id", "title", "report"}
PORT_CALL_COLUMNS = ["call_id", "vessel_id", "port_code", "arrival_date"]
PROFILE_COLUMNS = [
    "customer",
    "shipment_count",
    "total_weight_kg",
    "express_count",
    "destinations",
]


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def load_json(path):
    """Load and return the parsed content of one JSON file."""
    with open(path, "r", encoding="utf-8-sig") as file:
        return json.load(file)


def parse_iso_date(text):
    """Convert a strict YYYY-MM-DD string to a date. Raises ValueError."""
    text = text.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError("Date must use YYYY-MM-DD")
    return datetime.strptime(text, "%Y-%m-%d").date()


def _require_fields(record, required):
    """Raise ValueError unless record is an object holding every required field."""
    if not isinstance(record, dict):
        raise ValueError("Expected a JSON object")
    missing = required - record.keys()
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def load_json_records(directory, validate):
    """Load every .json file in a directory and validate each record.

    Returns (records, rejected). rejected holds (filename, reason) pairs.
    One bad file never stops the others from loading. A missing directory
    gives an empty result.
    """
    records = []
    rejected = []
    try:
        paths = sorted(
            path for path in Path(directory).iterdir()
            if path.is_file() and path.suffix.lower() == ".json"
        )
    except FileNotFoundError:
        return records, rejected

    for path in paths:
        try:
            record = load_json(path)
            validate(record)
            records.append(record)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            # JSONDecodeError and UnicodeDecodeError are ValueErrors; the
            # explicit name documents the malformed-JSON case.
            rejected.append((path.name, str(error)))
    return records, rejected


# ---------------------------------------------------------------------------
# Validators (raise ValueError for a bad record)
# ---------------------------------------------------------------------------

def validate_vessel(record):
    _require_fields(record, VESSEL_FIELDS)
    if not isinstance(record["name"], str):
        raise ValueError("name must be a string")
    if not isinstance(record["capacity_teu"], int) or isinstance(record["capacity_teu"], bool):
        raise ValueError("capacity_teu must be an integer")


def validate_shipment(record):
    _require_fields(record, SHIPMENT_FIELDS)
    for field in ("shipment_id", "customer", "destination", "priority"):
        if not isinstance(record[field], str):
            raise ValueError(f"{field} must be a string")
    if not _is_number(record["weight_kg"]):
        raise ValueError("weight_kg must be a number")


def validate_manifest(record):
    _require_fields(record, MANIFEST_FIELDS)
    if not isinstance(record["call_id"], str):
        raise ValueError("call_id must be a string")
    shipment_ids = record["shipment_ids"]
    if not isinstance(shipment_ids, list) or not all(isinstance(s, str) for s in shipment_ids):
        raise ValueError("shipment_ids must be a list of strings")
    if not isinstance(record["event_codes"], list):
        raise ValueError("event_codes must be a list")


def validate_incident(record):
    _require_fields(record, INCIDENT_FIELDS)
    for field in INCIDENT_FIELDS:
        if not isinstance(record[field], str):
            raise ValueError(f"{field} must be a string")


# ---------------------------------------------------------------------------
# Collection loaders
# ---------------------------------------------------------------------------

def load_vessels(directory):
    """Return (valid vessels sorted by name case-insensitively, rejected files)."""
    vessels, rejected = load_json_records(directory, validate_vessel)
    vessels.sort(key=lambda vessel: vessel["name"].casefold())
    return vessels, rejected


def load_shipments(directory):
    """Return (list of valid shipment records, rejected files)."""
    return load_json_records(directory, validate_shipment)


def load_manifests(directory):
    """Return ({casefolded call_id: manifest}, rejected files).

    The business identifier inside the file is used, never the filename.
    """
    records, rejected = load_json_records(directory, validate_manifest)
    manifests = {}
    for record in records:
        manifests.setdefault(record["call_id"].strip().casefold(), record)
    return manifests, rejected


def load_incidents(directory):
    """Return (list of valid incident records, rejected files)."""
    return load_json_records(directory, validate_incident)


def load_port_calls(path=PORT_CALLS_FILE):
    """Read port_calls.csv into a list of dicts with stripped string values.

    Dates are NOT validated here: each service decides how to report a bad
    date. Raises FileNotFoundError, csv.Error or ValueError (bad header).
    """
    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = set(PORT_CALL_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
        calls = []
        for row in reader:
            call = {name: (row.get(name) or "").strip() for name in PORT_CALL_COLUMNS}
            if any(call.values()):
                calls.append(call)
    return calls


# ---------------------------------------------------------------------------
# Generated outputs
# ---------------------------------------------------------------------------

def load_customer_profiles(path=CUSTOMER_PROFILES_FILE):
    """Return existing profile rows, or [] when the export does not exist yet.

    Raises ValueError when the header is not the agreed one, and csv.Error
    for unreadable CSV, so the caller never overwrites a file it cannot read.
    """
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != PROFILE_COLUMNS:
                raise ValueError("Unexpected header in customer profile export")
            return [dict(row) for row in reader]
    except FileNotFoundError:
        return []


def save_customer_profiles(rows, path=CUSTOMER_PROFILES_FILE):
    """Rewrite the whole export safely: temp file first, then replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    with open(temp_path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=PROFILE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_path, path)


def save_text_file(path, text):
    """Write text exactly as given (line breaks preserved), creating folders."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(text)