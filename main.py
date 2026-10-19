"""HarborFlow Assignment 2 entry point: menu and orchestration only.

File access lives in data_access.py, business rules in operations.py,
regex/text logic in text_tools.py and the Task 2-6 services in tasks_2_6.py.
"""
import data_access
from tasks_2_6 import (
    print_vessel_inventory,
    service_calls_by_month,
    service_export_customer_profile,
    service_inspect_manifest,
    service_priority_cargo,
    service_sanitize_incident,
)

MENU = """HARBORFLOW PORT INTELLIGENCE
1. List registered vessels
2. Inspect a vessel manifest
3. Identify priority cargo
4. Export a customer operations profile
5. Find port calls by month
6. Sanitize an incident report
7. Analyze the longest stable event sequence
8. Assess weather risk for upcoming calls
9. Search incident reports
10. Close console"""


def service_list_vessels():
    """Task 1."""
    vessels, rejected = data_access.load_vessels(data_access.VESSELS_DIR)
    print_vessel_inventory(vessels, rejected)


# Services 7-9 are not implemented yet, so they are not listed here.
SERVICES = {
    1: service_list_vessels,
    2: service_inspect_manifest,
    3: service_priority_cargo,
    4: service_export_customer_profile,
    5: service_calls_by_month,
    6: service_sanitize_incident,
}


def main():
    """Run the HarborFlow Port Intelligence Console."""
    running = True
    while running:
        print(MENU)
        try:
            choice = int(input("Select service: ").strip())
        except ValueError:
            print("Error - Select a service from 1 to 10.")
            continue

        if choice == 10:
            print("Console closed. HarborFlow operational data remains safe.")
            running = False
        elif choice in SERVICES:
            SERVICES[choice]()
        elif not 1 <= choice <= 10:
            print("Error - Select a service from 1 to 10.")


if __name__ == "__main__":
    main()

