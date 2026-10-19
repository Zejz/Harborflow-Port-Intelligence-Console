"""HarborFlow operational business rules.

No input() or print() here and no file access: functions take data and return
data, so they can be tested and explained on their own.
"""
from data_access import parse_iso_date

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

CATEGORY_ORDER = ["CONTROLLED", "COLD CHAIN", "EXPEDITE", "STANDARD"]
HEAVY_WEIGHT_KG = 5000


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def format_date(day):
    """Present a date as 'DD Month YYYY' (independent of the OS locale)."""
    return f"{day.day:02d} {MONTH_NAMES[day.month - 1]} {day.year}"


def find_vessel_by_name(vessels, name):
    """Return the vessel whose name matches (trimmed, case-insensitive), else None."""
    wanted = name.strip().casefold()
    for vessel in vessels:
        if vessel["name"].strip().casefold() == wanted:
            return vessel
    return None


def find_call(port_calls, call_id):
    """Return the port call whose call_id matches (trimmed, case-insensitive)."""
    wanted = call_id.strip().casefold()
    for call in port_calls:
        if call["call_id"].casefold() == wanted:
            return call
    return None


def index_shipments(shipments):
    """Map shipment_id -> shipment record (first record wins on duplicates)."""
    by_id = {}
    for shipment in shipments:
        by_id.setdefault(shipment["shipment_id"], shipment)
    return by_id


def _is_true(shipment, flag):
    """Optional boolean flags count as false when absent."""
    return shipment.get(flag, False) is True


# ---------------------------------------------------------------------------
# Task 2: manifest inspection
# ---------------------------------------------------------------------------

def select_next_call(port_calls, vessel_id, reference_date):
    """Earliest call of a vessel on/after reference_date; ties -> smallest call_id.

    Rows with an unreadable arrival_date cannot qualify and are skipped.
    """
    best_key = None
    best_call = None
    for call in port_calls:
        if call["vessel_id"] != vessel_id:
            continue
        try:
            arrival = parse_iso_date(call["arrival_date"])
        except ValueError:
            continue
        if arrival < reference_date:
            continue
        key = (arrival, call["call_id"])
        if best_key is None or key < best_key:
            best_key = key
            best_call = call
    return best_call


def build_manifest_report(vessel_name, call, manifest, shipments_by_id):
    """Return the printable lines for Task 2, cargo lines in manifest order."""
    arrival = format_date(parse_iso_date(call["arrival_date"]))
    lines = [f"Manifest for {vessel_name} | Call {call['call_id']} | {arrival}"]

    resolved_weight = 0.0
    missing = 0
    for number, shipment_id in enumerate(manifest["shipment_ids"], start=1):
        shipment = shipments_by_id.get(shipment_id)
        if shipment is None:
            missing += 1
            lines.append(f"{number}. {shipment_id} | MISSING RECORD")
            continue
        weight = float(shipment["weight_kg"])
        resolved_weight += weight
        cargo_type = shipment.get("cargo_type") or "NOT PROVIDED"
        lines.append(
            f"{number}. {shipment_id} | {shipment['customer']} | {weight} kg | {cargo_type}"
        )

    lines.append(f"Declared shipments: {len(manifest['shipment_ids'])}")
    lines.append(f"Resolved weight: {resolved_weight:.2f} kg")
    lines.append(f"Missing shipment records: {missing}")
    return lines


# ---------------------------------------------------------------------------
# Task 3: priority cargo
# ---------------------------------------------------------------------------

def classify_shipment(shipment):
    """Return (category, reason) using the FIRST matching rule.

    The order of the rules below is business policy - do not reorder.
    """
    if _is_true(shipment, "hazardous"):
        return "CONTROLLED", "hazardous cargo"
    if _is_true(shipment, "temperature_controlled"):
        return "COLD CHAIN", "temperature controlled cargo"
    if str(shipment["priority"]).strip().upper() == "EXPRESS":
        return "EXPEDITE", "express service"
    if shipment["weight_kg"] >= HEAVY_WEIGHT_KG:
        return "EXPEDITE", "heavy cargo"
    return "STANDARD", "standard handling"


def classify_manifest(manifest, shipments_by_id):
    """Classify every resolved shipment in manifest order.

    Returns (rows, totals): rows are (shipment_id, category, reason) and
    totals maps each category to its count. Missing shipments are skipped.
    """
    rows = []
    totals = {category: 0 for category in CATEGORY_ORDER}
    for shipment_id in manifest["shipment_ids"]:
        shipment = shipments_by_id.get(shipment_id)
        if shipment is None:
            continue
        category, reason = classify_shipment(shipment)
        rows.append((shipment_id, category, reason))
        totals[category] += 1
    return rows, totals


def format_category_totals(totals):
    parts = [f"{category}={totals[category]}" for category in CATEGORY_ORDER]
    return "Category totals: " + ", ".join(parts)


# ---------------------------------------------------------------------------
# Task 4: customer profile
# ---------------------------------------------------------------------------

def build_customer_profile(customer_name, shipments):
    """Aggregate all shipments of one customer into a profile row, or None."""
    wanted = customer_name.strip().casefold()
    matches = [s for s in shipments if s["customer"].strip().casefold() == wanted]
    if not matches:
        return None

    total_weight = sum(float(s["weight_kg"]) for s in matches)
    express_count = sum(
        1 for s in matches if str(s["priority"]).strip().upper() == "EXPRESS"
    )
    destinations = sorted({s["destination"].strip() for s in matches if s["destination"].strip()})
    return {
        "customer": matches[0]["customer"].strip(),
        "shipment_count": str(len(matches)),
        "total_weight_kg": f"{total_weight:.2f}",
        "express_count": str(express_count),
        "destinations": "|".join(destinations),
    }


def upsert_profile(rows, profile):
    """Replace the existing row for the customer or append a new one.

    Works on an in-memory copy; other customers' rows are untouched.
    """
    wanted = profile["customer"].casefold()
    updated = []
    replaced = False
    for row in rows:
        if row["customer"].strip().casefold() == wanted:
            if not replaced:
                updated.append(profile)
                replaced = True
            # any accidental duplicate of this customer is dropped
        else:
            updated.append(row)
    if not replaced:
        updated.append(profile)
    return updated


# ---------------------------------------------------------------------------
# Task 5: calls by month
# ---------------------------------------------------------------------------

def calls_in_month(port_calls, vessels, month):
    """Return (calls, problems) for a month number 1-12.

    calls: (date, vessel_name, port_code, call_id) sorted by date, vessel name.
    problems: messages about rows that were skipped.
    """
    names = {vessel["vessel_id"]: vessel["name"] for vessel in vessels}
    calls = []
    problems = []
    for call in port_calls:
        try:
            arrival = parse_iso_date(call["arrival_date"])
        except ValueError:
            problems.append(
                f"Skipped port call {call['call_id']}: invalid arrival date "
                f"'{call['arrival_date']}'"
            )
            continue
        if arrival.month != month:
            continue
        vessel_name = names.get(call["vessel_id"])
        if vessel_name is None:
            problems.append(
                f"Skipped port call {call['call_id']}: unknown vessel_id "
                f"'{call['vessel_id']}'"
            )
            continue
        calls.append((arrival, vessel_name, call["port_code"], call["call_id"]))

    calls.sort(key=lambda item: (item[0], item[1].casefold(), item[3]))
    return calls, problems