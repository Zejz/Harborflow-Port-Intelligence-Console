import csv

import data_access
import operations
import tasks_2_6

#---------------------------------------------------------------------------
# Analyze the longest stable event sequence
#---------------------------------------------------------------------------
def service_longest_stable_sequence():
    """Task 7."""
    manifests, _ = data_access.load_manifests(data_access.MANIFESTS_DIR)
    if not manifests:
        print("Manifest unavailable")
        return

    call_id = input("Call ID: ").strip().casefold()
    manifest = manifests.get(call_id)
    if manifest is None:
        print("Manifest unavailable")
        return

    event_codes = manifest["event_codes"]
    longest_sequence = operations.find_longest_stable_sequence(event_codes)
    print(f"Event codes: {','.join(event_codes)}")
    print(f"Longest stable sequence length: {len(longest_sequence)}")
    print(f"Sequence: {' -> '.join(longest_sequence)}")


#---------------------------------------------------------------------------
# Assess weather risk for upcoming calls
#---------------------------------------------------------------------------
def service_weather_risk():
    """Task 8."""
    vessels, rejected = data_access.load_vessels(data_access.VESSELS_DIR)
    tasks_2_6.print_vessel_inventory(vessels, rejected)
    vessel = operations.find_vessel_by_name(vessels, input("Vessel name: "))
    if vessel is None:
        print("Vessel not found")
        return

    reference_date = tasks_2_6.prompt_reference_date()
    port_calls = tasks_2_6.load_port_calls_or_report()
    if port_calls is None:
        return
    try:
        forecasts, rejected = data_access.load_weather(data_access.WEATHER_FILE)
    except FileNotFoundError:
        print("Weather data unavailable: dataset/weather.csv not found.")
        return
    except (csv.Error, ValueError) as error:
        print(f"Weather data unavailable: {error}")
        return

    for line_number, reason in rejected:
        print(f"Skipped malformed forecast row {line_number}: {reason}")

    calls, problems = operations.weather_risk_for_calls(
        port_calls, vessel["vessel_id"], reference_date, forecasts
    )
    for problem in problems:
        print(problem)
    if not calls:
        print("No upcoming port calls found.")
        return

    for arrival, port_code, _call_id, forecast, recommendations in calls:
        print(f"{vessel['name']} | {port_code} | {operations.format_date(arrival)}")
        if forecast is None:
            print("Forecast unavailable")
            continue
        print(
            f"Wind: {forecast['wind_kmh']:.1f} km/h | "
            f"Rain: {forecast['precipitation_mm']:.1f} mm | "
            f"Waves: {forecast['wave_height_m']:.1f} m"
        )
        print(f"Recommendation: {' '.join(recommendations)}")


#---------------------------------------------------------------------------
# Search incident reports
#---------------------------------------------------------------------------
def service_search_incidents():
    """Task 9."""
    try:
        cached_index = data_access.load_incident_index(
            data_access.INCIDENT_INDEX_FILE, data_access.INCIDENTS_DIR
        )
    except (OSError, ValueError) as error:
        print(f"Incident index unavailable: {error}. Rebuilding.")
        cached_index = None

    if cached_index is None:
        incidents, rejected = data_access.load_incidents(data_access.INCIDENTS_DIR)
        for filename, reason in rejected:
            print(f"Skipped incident file {filename}: {reason}")
        index, titles = operations.build_incident_index(incidents)
        try:
            data_access.save_incident_index(
                index, titles, data_access.INCIDENT_INDEX_FILE
            )
        except OSError as error:
            print(f"Error - Could not save incident index: {error}")
    else:
        index, titles = cached_index

    query = input("Search incident reports: ")
    matches = operations.search_incident_index(index, query)
    if not matches:
        print("No matching incidents found.")
        return

    print(f"Matches for '{query.strip()}':")
    for incident_id, score in matches:
        print(f"- {incident_id} | score {score} | {titles[incident_id]}")
