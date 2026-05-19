import requests, getpass
import pandas as pd

# DHIS2 User Credentials
DHIS2_BASE_URL = "https://ccdev.org/chistest"
USERNAME = input("Write your username: ")
PASSWORD = getpass.getpass("Write your password: ")

# Setting up a session for authentication
session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.headers.update({"Content-Type": "application/json"}) 

# First letter to be capital and the rest to be small letter.
district_name = input("Write your district name: ")

# Geting Level 3 Org (District) Unit ID by Name
def get_level_3_org_unit_id_by_name(level_3_name):
    url = f"{DHIS2_BASE_URL}/api/organisationUnits.json"
    params = {
        "filter": f"name:eq:{level_3_name}",  # Filter for org unit name
        "fields": "id,name",                  # Get only the id and name
        "paging": "false"
    }
    
    message = requests.get(url, auth=(USERNAME, PASSWORD), params=params)

    if message.status_code == 200:
        data = message.json()
        if data["organisationUnits"]:
            return data["organisationUnits"][0]["id"]  # Return the ID of the first matching level 3 org unit
        else:
            print(f"No level 3 org unit found with the name '{level_3_name}'.")
            return None
    else:
        print(f"Error: Failed to fetch level 3 org unit with status code {message.status_code}")
        return None

# Fetching all child org units under a parent (Healthy Facilities) (Level 4)
def get_all_child_org_units(parent_id):
    url = f"{DHIS2_BASE_URL}/api/organisationUnits.json"
    params = {
        "filter": f"parent.id:eq:{parent_id}",  # Fetch all child org units under the parent ID
        "fields": "id,name,level,parent[id,name]",
        "paging": "false"
    }

    message = requests.get(url, auth=(USERNAME, PASSWORD), params=params)

    if message.status_code == 200:
        data = message.json()
        if data.get("organisationUnits"):
            return data["organisationUnits"]
        else:
            return []
    else:
        print(f"Error: Failed to fetch org units for parent ID {parent_id}")
        return []

# Recursively fetching all level 5 org units (Catcment Area) under a given parent
def get_level_5_org_units(parent_id):
    level_5_org_units = []
    
    # Get all children under the parent
    child_org_units = get_all_child_org_units(parent_id)
    
    for unit in child_org_units:
        if unit["level"] == 5:
            # If it's a level 5 org unit, add it to the lis
            unit_parent = unit.pop('parent')
            parent_name, parent_id = unit_parent['name'], unit_parent['id']
            new_unit = {**unit, "parent_name" : parent_name, "parent_id" : parent_id}
            level_5_org_units.append(new_unit)
        else:
            # If it's not level 5, recursively fetch its children
            level_5_org_units.extend(get_level_5_org_units(unit["id"]))
    
    return level_5_org_units

# Fetching all level 5 org units under a level 3 org unit by name
def fetch_level_5_org_units_by_level_3_name(level_3_name):
    # Step Get the ID of the level 3 org unit by its name
    print(f"System is Fetching Level 5 org unit ID for {level_3_name} \nPlease Wait...")
    level_3_id = get_level_3_org_unit_id_by_name(level_3_name)
    
    if not level_3_id:
        return []  # If the level 3 org unit was not found, return an empty list
    
    # Recursively get all level 5 org units under the level 3 org unit
    level_5_org_units = get_level_5_org_units(level_3_id)
    
    return level_5_org_units

# Save the org units to an Excel file
def save_org_units_to_excel(org_units, filename= f"{district_name}_CA.xlsx"):
    # Convert the list of org units to a DataFrame
    df = pd.DataFrame(org_units)

    # Save the DataFrame to an Excel file
    df.to_excel(filename, index=False)
    print(f"Org units saved to {filename}")

level_3_name = f"{district_name}-DHO"  # Give the name of the level 3 org unit (District)
level_5_org_units = fetch_level_5_org_units_by_level_3_name(level_3_name)

if level_5_org_units:
    print(f"\nLevel 5 org units under {level_3_name}:")
    for unit in level_5_org_units:
        print(f"ID: {unit['id']}, Name: {unit['name']}, Level: {unit['level']}")
    
    # Saving the org units to an Excel file
    save_org_units_to_excel(level_5_org_units)
else:
    print(f"No level 5 org units found under {level_3_name}.")