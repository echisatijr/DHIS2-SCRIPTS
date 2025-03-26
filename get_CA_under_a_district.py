import requests
import pandas as pd

# DHIS2 Credentials
DHIS2_BASE_URL = "https://ccdev.org/chistest"
USERNAME = "achisati"
PASSWORD = "Achisati@2023"

# Set up a session for authentication
session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.headers.update({"Content-Type": "application/json"})

# Step 1: Get Level 3 Org Unit ID by Name
def get_level_3_org_unit_id_by_name(level_3_name):
    url = f"{DHIS2_BASE_URL}/api/organisationUnits.json"
    params = {
        "filter": f"name:eq:{level_3_name}",  # Filter for org unit name
        "fields": "id,name",                  # Get only the id and name
        "paging": "false"
    }
    
    response = requests.get(url, auth=(USERNAME, PASSWORD), params=params)

    if response.status_code == 200:
        data = response.json()
        if data["organisationUnits"]:
            return data["organisationUnits"][0]["id"]  # Return the ID of the first matching level 3 org unit
        else:
            print(f"No level 3 org unit found with the name '{level_3_name}'.")
            return None
    else:
        print(f"Error: Failed to fetch level 3 org unit with status code {response.status_code}")
        return None

# Step 2: Fetch all child org units under a parent (Level 4, Level 5, etc.)
def get_all_child_org_units(parent_id):
    url = f"{DHIS2_BASE_URL}/api/organisationUnits.json"
    params = {
        "filter": f"parent.id:eq:{parent_id}",  # Fetch all child org units under the parent ID
        "fields": "id,name,level,parent[id,name]",
        "paging": "false"
    }

    response = requests.get(url, auth=(USERNAME, PASSWORD), params=params)

    if response.status_code == 200:
        data = response.json()
        if data.get("organisationUnits"):
            return data["organisationUnits"]
        else:
            return []
    else:
        print(f"Error: Failed to fetch org units for parent ID {parent_id}")
        return []

# Step 3: Recursively fetch all level 5 org units under a given parent
def get_level_5_org_units(parent_id):
    level_5_org_units = []
    
    # Get all children under the parent
    child_org_units = get_all_child_org_units(parent_id)
    
    for unit in child_org_units:
        if unit["level"] == 5:
            # If it's a level 5 org unit, add it to the list
            level_5_org_units.append(unit)
        else:
            # If it's not level 5, recursively fetch its children
            level_5_org_units.extend(get_level_5_org_units(unit["id"]))
    
    return level_5_org_units

# Step 4: Fetch all level 5 org units under a level 3 org unit by name
def fetch_level_5_org_units_by_level_3_name(level_3_name):
    # Step 1: Get the ID of the level 3 org unit by its name
    print(f"Fetching level 3 org unit ID for {level_3_name}...")
    level_3_id = get_level_3_org_unit_id_by_name(level_3_name)
    
    if not level_3_id:
        return []  # If the level 3 org unit was not found, return an empty list
    
    # Step 2: Recursively get all level 5 org units under the level 3 org unit
    level_5_org_units = get_level_5_org_units(level_3_id)
    
    return level_5_org_units

# Step 5: Save the org units to an Excel file
def save_org_units_to_excel(org_units, filename="org_units_Chitipa.xlsx"):
    # Convert the list of org units to a DataFrame
    df = pd.DataFrame(org_units)

    # Save the DataFrame to an Excel file
    df.to_excel(filename, index=False)
    print(f"Org units saved to {filename}")

# Example Usage:
level_3_name = "Chitipa-DHO"  # Replace with the name of the level 3 org unit
level_5_org_units = fetch_level_5_org_units_by_level_3_name(level_3_name)

if level_5_org_units:
    print(f"\nLevel 5 org units under {level_3_name}:")
    for unit in level_5_org_units:
        print(f"ID: {unit['id']}, Name: {unit['name']}, Level: {unit['level']}")
    
    # Save the org units to an Excel file
    save_org_units_to_excel(level_5_org_units)
else:
    print(f"No level 5 org units found under {level_3_name}.")
