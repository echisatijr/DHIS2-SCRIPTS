import requests
import json
import time

# DHIS2 settings
dhis2_url = "https://ccdev.org/chistest/api/organisationUnits.json?paging=false&fields=id,name,parent[id]"
dhis2_username = "achisati"
dhis2_password = "Achisati@2023"

# OpenMRS settings
openmrs_url = "http://localhost/openmrs/ws/rest/v1/location"
openmrs_username = "admin"
openmrs_password = "Admin123"

# Cache to track created locations
created_locations = {}

# Helper Functions
def get_dhis2_orgunits():
    response = requests.get(dhis2_url, auth=(dhis2_username, dhis2_password))
    response.raise_for_status()
    return response.json().get("organisationUnits", [])

def find_openmrs_location_by_name(name):
    response = requests.get(
        f"{openmrs_url}?q={name}",
        auth=(openmrs_username, openmrs_password)
    )
    results = response.json().get("results", [])
    for loc in results:
        if loc["name"] == name:
            return loc["uuid"]
    return None

def create_openmrs_location(name, description, parent_uuid=None):
    if name in created_locations:
        return created_locations[name]

    payload = {
        "name": name,
        "description": description,
    }
    if parent_uuid:
        payload["parentLocation"] = parent_uuid

    response = requests.post(
        openmrs_url,
        auth=(openmrs_username, openmrs_password),
        headers={"Content-Type": "application/json"},
        json=payload
    )

    if response.status_code in (200, 201):
        uuid = response.json()["uuid"]
        created_locations[name] = uuid
        print(f"Created location: {name}")
        return uuid
    else:
        print(f"Failed to create {name}: {response.text}")
        return None

def ensure_location(unit, all_units_map):
    name = unit["name"]
    dhis_id = unit["id"]

    # Skip if already created
    if name in created_locations:
        return created_locations[name]

    parent_uuid = None
    parent = unit.get("parent")
    if parent:
        parent_unit = all_units_map.get(parent["id"])
        if parent_unit:
            parent_uuid = ensure_location(parent_unit, all_units_map)

    return create_openmrs_location(name, f"DHIS2 ID: {dhis_id}", parent_uuid)

# Main Execution

org_units = get_dhis2_orgunits()
units_by_id = {unit["id"]: unit for unit in org_units}

for unit in org_units:
    ensure_location(unit, units_by_id)
    time.sleep(0.2)  # small delay to avoid rate limiting
