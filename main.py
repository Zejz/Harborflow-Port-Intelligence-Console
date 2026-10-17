"""HarborFlow Assignment 2 starter entry point."""
import json
import csv
import os

def main():
    """Run the HarborFlow Port Intelligence Console."""
    # TODO: implement the persistent menu and orchestrate the services.
Running = 1
while Running:
    Choice = input("""HARBORFLOW PORT INTELLIGENCE
    1. List registered vessels
    2. Inspect a vessel manifest
    3. Identify priority cargo
    4. Export a customer operations profile
    5. Find port calls by month
    6. Sanitize an incident report
    7. Analyze the longest stable event sequence
    8. Assess weather risk for upcoming calls
    9. Search incident reports
    10. Close console
    Select service:""")


    """Choice 1"""


    if Choice == "1":


        REQUIRED_FIELDS = {"vessel_id", "name", "imo", "capacity_teu"}


        def load_json(path): 
            with open(path, 'r') as f:
                return json.load(f)


        def load_vessels(directory):
            vessels = []
            rejected = []
            for filename in os.listdir(directory):
                try:
                    vessel = load_json(os.path.join(directory, filename))

                    if not isinstance(vessel, dict):
                        raise ValueError("Expected a JSON object")

                    missing = REQUIRED_FIELDS - vessel.keys()
                    if missing:
                        raise ValueError(
                        f"Missing required fields: {', '.join(sorted(missing))}"
                        )

                    if not isinstance(vessel["name"], str):
                        raise ValueError("name must be a string")

                    vessels.append(vessel)

                except (OSError, ValueError) as error:
                    rejected.append((filename, str(error)))

            vessels.sort(key=lambda vessel: vessel["name"].casefold())
            return vessels, rejected


        vessels, rejected = load_vessels('dataset/vessels')
        
        print("Registered HarborFlow vessels:")
        for vessel in vessels:
            print(
            f"- {vessel['name']} | IMO {vessel['imo']} | "
            f"{vessel['capacity_teu']:,} TEU"
            )
        print(f"Skipped vessel files: {len(rejected)}")

        for filename, reason in rejected:
            print(f"Skipped {filename}: {reason}")




pass

if __name__ == "__main__":
    main()

