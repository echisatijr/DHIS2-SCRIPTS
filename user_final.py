## importing required modules
import requests
import json
import pandas as pd
from datetime import datetime

## User credentials for DHIS2 server 
DHIS2_URL = "https://ccdev.org/chistest"
USERNAME = "achisati"
PASSWORD = "Achisati@2023"

## Setting up an authentication session
session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.headers.update({"Content-Type": "application/json"})

## Function to check if a username exists in DHIS2
def username_exists(username):
    response = session.get(f"{DHIS2_URL}/api/users?filter=username:eq:{username}&fields=id")
    if response.status_code == 200:
        data = response.json()
        return len(data["users"]) > 0  ## Returns True if username already exists
    return False

## Function to generate a unique username
"""
def generate_username(first_name, last_name):
    base_username = f"{first_name[0].lower()}{last_name.lower()}"  # First letter + last name
    if username_exists(base_username):
        return f"{first_name.lower()}{last_name.lower()}"  # Full first name + last name
    return base_username
"""
def generate_username(first_name, last_name):
    base_username = f"{first_name[0].lower()}{last_name.lower()}"  ## First letter + last name
    if username_exists(base_username):
        alternative_username = f"{first_name.lower()}{last_name.lower()}"  ## Full first + last name
        if username_exists(alternative_username):
            return f"{alternative_username}1"  ## Append "1" if full name format exists
        return alternative_username
    return base_username

## Generating password
## format: First letter of first name + last name + @ + year
def generate_password(first_name, last_name):
    year = datetime.now().year
    password = f"{first_name[0].upper()}{last_name.lower()}@{year}"
    return password

## getting organization unit ID by name and fetch only Level 5 (catchment area)
def get_org_unit_level_5(levels):
    response = session.get(f"{DHIS2_URL}/api/organisationUnits?filter=name:eq:{levels[-1]}&fields=id,name,parent")
    if response.status_code == 200:
        data = response.json()
        if data['organisationUnits']:
            return [{"id": data['organisationUnits'][0]['id']}]
        else:
            print(f"❌ Organization unit '{levels[-1]}' not found!")
            return None
    else:
        print(f"❌ Failed to fetch organization units. Status code: {response.status_code}")
        return None

## Getting the user group ID by name
def get_user_group_id(group_name):
    response = session.get(f"{DHIS2_URL}/api/userGroups?filter=name:eq:{group_name}&fields=id,name")
    if response.status_code == 200:
        data = response.json()
        if data['userGroups']:
            return data['userGroups'][0]['id']
        else:
            print(f"❌ User group '{group_name}' not found!")
            return None
    else:
        print(f"❌ Failed to fetch user group. Status code: {response.status_code}")
        return None

## Reading from the Excel file
excel_file = r"C:\Users\ALNAFE ENOCK CHISATI\Documents\LETS CODE!\DHIS2-SCRIPTS\final_users.xlsx"

df = pd.read_excel(excel_file)

## Iterate over each row in the Excel file
for index, row in df.iterrows():
    first_name = row["firstName"].strip()
    last_name = row["surname"].strip()
    username = generate_username(first_name, last_name)  ## Generating unique username
    password = generate_password(first_name, last_name)  ## Generating password in the desired format

    new_user = {
        "firstName": first_name,
        "surname": last_name,
        "username": username,
        "password": password,
    }

    if pd.notna(row.get("email")):
        new_user["email"] = row["email"]
    
    if pd.notna(row.get("phoneNumber")):
        new_user["phoneNumber"] = row["phoneNumber"]
    
    if pd.notna(row.get("userRoleID")):
        new_user["userRoles"] = [{"id": row["userRoleID"]}]
    
    org_unit_hierarchy = get_org_unit_level_5([row["Level 1"], row["Level 2"], row["Level 3"], row["Level 4"], row["Level 5"]])
    
    if org_unit_hierarchy:
        new_user["organisationUnits"] = org_unit_hierarchy
        new_user["dataViewOrganisationUnits"] = org_unit_hierarchy
        new_user["teiSearchOrganisationUnits"] = org_unit_hierarchy
    
    if pd.notna(row.get("userGroupID")):
        user_group_id = get_user_group_id(row["userGroupID"])
        if user_group_id:
            new_user["userGroups"] = [{"id": user_group_id}]
    
    response = session.post(f"{DHIS2_URL}/api/users", data=json.dumps(new_user))

    if response.status_code == 201:
        print(f"✅ User {username} created successfully!, password is {password}")
    else:
        error_message = response.json().get("response", {}).get("errorReports", [{}])[0].get("message", "Unknown error")
        print(f"[+] {error_message} password is {password}")
