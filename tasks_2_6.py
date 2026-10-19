"""HarborFlow services for Tasks 2-6, plus the prompt helpers they share.

Task 2: inspect a vessel manifest      Task 5: find port calls by month
Task 3: identify priority cargo        Task 6: sanitize an incident report
Task 4: export a customer profile

Shared helpers (prompt_reference_date, prompt_number_in_range,
load_port_calls_or_report, print_vessel_inventory) can be imported by the
services for Tasks 7-9 as well.
"""
import csv
import re

import data_access
import operations
import text_tools


# ---------------------------------------------------------------------------
# Shared prompts and loaders
# ---------------------------------------------------------------------------

def prompt_reference_date():
    """Ask for a YYYY-MM-DD date until valid; repeats only the date prompt."""
    reference_date = None
    while reference_date is None:
        try:
            reference_date = data_access.parse_iso_date(
                input("Reference date (YYYY-MM-DD): ")
            )
        except ValueError:
            print("Error - Date must use YYYY-MM-DD.")
    return reference_date


def prompt_number_in_range(prompt, error_message, low, high):
    """Ask for an integer between low and high (inclusive) until valid."""
    number = None
    while number is None:
        try:
            value = int(input(prompt).strip())
        except ValueError:
            print(error_message)
            continue
        if low <= value <= high:
            number = value
        else:
            print(error_message)
    return number


def load_port_calls_or_report():
    """Return the port call rows, or None after telling the user why not."""
    try:
        return data_access.load_port_calls()
    except FileNotFoundError:
        print("Port call data unavailable: dataset/port_calls.csv not found.")
    except (csv.Error, ValueError) as error:
        print(f"Port call data unavailable: {error}")
    return None


def print_vessel_inventory(vessels, rejected):
    print("Registered HarborFlow vessels:")
    for vessel in vessels:
        print(
            f"- {vessel['name']} | IMO {vessel['imo']} | "
            f"{vessel['capacity_teu']:,} TEU"
        )
    print(f"Skipped vessel files: {len(rejected)}")


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

def service_inspect_manifest():
    """Task 2."""
    vessels, rejected = data_access.load_vessels(data_access.VESSELS_DIR)
    print_vessel_inventory(vessels, rejected)

    vessel = operations.find_vessel_by_name(vessels, input("Vessel name: "))
    if vessel is None:
        print("Vessel not found")
        return
    reference_date = prompt_reference_date()

    port_calls = load_port_calls_or_report()
    if port_calls is None:
        return
    call = operations.select_next_call(port_calls, vessel["vessel_id"], reference_date)
    if call is None:
        print("No upcoming port calls found")
        return

    manifests, _ = data_access.load_manifests(data_access.MANIFESTS_DIR)
    manifest = manifests.get(call["call_id"].casefold())
    if manifest is None:
        print("Manifest unavailable")
        return

    shipments, _ = data_access.load_shipments(data_access.SHIPMENTS_DIR)
    lines = operations.build_manifest_report(
        vessel["name"], call, manifest, operations.index_shipments(shipments)
    )
    for line in lines:
        print(line)


def service_priority_cargo():
    """Task 3."""
    call_id = input("Call ID: ")
    port_calls = load_port_calls_or_report()
    if port_calls is None:
        return
    call = operations.find_call(port_calls, call_id)
    if call is None:
        print("Port call not found")
        return

    manifests, _ = data_access.load_manifests(data_access.MANIFESTS_DIR)
    manifest = manifests.get(call["call_id"].casefold())
    if manifest is None:
        print("Manifest unavailable")
        return

    shipments, _ = data_access.load_shipments(data_access.SHIPMENTS_DIR)
    rows, totals = operations.classify_manifest(
        manifest, operations.index_shipments(shipments)
    )
    for shipment_id, category, reason in rows:
        print(f"{shipment_id} | {category} | {reason}")
    print(operations.format_category_totals(totals))


def service_export_customer_profile():
    """Task 4."""
    customer_name = input("Customer name: ")
    shipments, _ = data_access.load_shipments(data_access.SHIPMENTS_DIR)
    profile = operations.build_customer_profile(customer_name, shipments)
    if profile is None:
        print("Customer not found.")  # the export file is not touched
        return

    export_path = data_access.CUSTOMER_PROFILES_FILE
    try:
        rows = data_access.load_customer_profiles(export_path)
    except (csv.Error, ValueError):
        print(f"Error - {export_path.as_posix()} is unreadable and was not modified.")
        return

    updated_rows = operations.upsert_profile(rows, profile)
    try:
        data_access.save_customer_profiles(updated_rows, export_path)
    except OSError as error:
        print(f"Error - Could not write {export_path.as_posix()}: {error}")
        return
    print(f"Customer profile updated: {export_path.as_posix()}")


def service_calls_by_month():
    """Task 5."""
    month = prompt_number_in_range(
        "Month (1-12): ", "Error - Enter a month from 1 to 12.", 1, 12
    )
    port_calls = load_port_calls_or_report()
    if port_calls is None:
        return
    vessels, _ = data_access.load_vessels(data_access.VESSELS_DIR)
    calls, problems = operations.calls_in_month(port_calls, vessels, month)

    for problem in problems:
        print(problem)
    if not calls:
        print("No port calls found.")
        return
    print(f"Port calls in {operations.MONTH_NAMES[month - 1]}:")
    for arrival, vessel_name, port_code, call_id in calls:
        print(f"- {operations.format_date(arrival)} | {vessel_name} | {port_code} | {call_id}")


def service_sanitize_incident():
    """Task 6."""
    incidents, _ = data_access.load_incidents(data_access.INCIDENTS_DIR)
    if not incidents:
        print("No incident reports found.")
        return
    incidents.sort(key=lambda item: (item["title"].casefold(), item["incident_id"]))
    for number, incident in enumerate(incidents, start=1):
        print(f"{number}. {incident['title']}")

    choice = prompt_number_in_range(
        "Select incident number: ",
        "Error - Select a listed incident.",
        1,
        len(incidents),
    )
    incident = incidents[choice - 1]

    sanitized, substitutions = text_tools.sanitize_text(incident["report"])
    if substitutions == 0:
        print("Incident contains no share-sensitive identifiers.")
        return

    safe_id = re.sub(r"[^\w.-]", "_", incident["incident_id"])
    output_path = data_access.SANITIZED_DIR / f"{safe_id}-sanitized.txt"
    try:
        data_access.save_text_file(output_path, sanitized)
    except OSError as error:
        print(f"Error - Could not write {output_path.as_posix()}: {error}")
        return
    print(f"Sanitized report saved: {output_path.as_posix()}")