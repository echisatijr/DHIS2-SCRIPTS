# Importing requred python models
import os, getpass, logging, requests
import pandas as pd
from datetime import datetime
from fuzzywuzzy import fuzz, process
from requests.auth import HTTPBasicAuth

# DHIS2 Credentials
DHIS2_BASE_URL = "https://ccdev.org/chistest"
USERNAME = input("Write your username: ")
PASSWORD = getpass.getpass("Write your password: ")

# Getting District.
district = input("Write the district name: ")
district_name = f"{district}-DHO"

# Default user role id and group id
DEFAULT_USER_ROLE = "K7DkWdiGSbA" # Community Tracker

# Loading user and organization unit data from Excel files
def load_data(user_file=(f"{district}_users.xlsx"), org_unit_file = (f"{district}_CA.xlsx")):
    df_users = pd.read_excel(user_file)
    df_org_units = pd.read_excel(org_unit_file)
    return df_users, df_org_units

# Checking if a username already exists in DHIS2
def username_exists(username):
    response = requests.get(
        f"{DHIS2_BASE_URL}/api/users?filter=username:eq:{username}&fields=id",
        auth=HTTPBasicAuth(USERNAME, PASSWORD)
    )
    if response.status_code == 200:
        try:
            return len(response.json().get("users", [])) > 0
        except requests.exceptions.JSONDecodeError:
            print("❌ Error: DHIS2 response is not valid JSON.")
    else:
        print(f"❌ Error: Failed to check username existence. Status code: {response.status_code}")
    return False

# Generating a unique username
def generate_username(full_name):
    name_parts = full_name.split() #Splitting the Full name
    if len(name_parts) == 3:
        base_username = f"{name_parts[0][0].lower()}{name_parts[2].lower()}"
        if username_exists(base_username):
            base_username = f"{name_parts[0][0].lower()}{name_parts[1][0].lower()}{name_parts[2].lower()}"
        if username_exists(base_username):
            base_username = f"{name_parts[0].lower()}{name_parts[1].lower()}{name_parts[2].lower()}"
        if username_exists(base_username):
            count = 1
            new_username = f"{base_username}{count}"
            while username_exists(new_username):
                count += 1
                new_username = f"{base_username}{count}"
            return new_username
    else:
        base_username = f"{name_parts[0][0].lower()}{name_parts[-1].lower()}"

    if username_exists(base_username):
        base_username = f"{name_parts[0].lower()}{name_parts[-1].lower()}"
        if username_exists(base_username):
            count = 1
            new_username = f"{base_username}{count}"
            while username_exists(new_username):
                count += 1
                new_username = f"{base_username}{count}"
            return new_username
    return base_username

# Generating a password
def generate_password(full_name):
    parts = full_name.split()
    first_letter = parts[0][0].upper()
    last_name = parts[-1].lower()
    current_year = datetime.now().year
    return f"{first_letter}{last_name}@{current_year}"

# Findinng the best matching organization unit using fuzzy matching
# Partial_ration, check substrings.
def find_best_match(org_unit_name, org_units):
    best_match, score = process.extractOne(org_unit_name, org_units, scorer=fuzz.partial_ratio)
    if score < 80:
        raise logging.error(f"No suitable match found for '{org_unit_name}'. Best match: '{best_match}' with score {score}")
    return best_match

# Assigning organization units and generate usernames and passwords
def assign_org_units(df_users, df_org_units):
    org_unit_names = df_org_units["name"].tolist()
    df_users["assigned_orgUnitName"] = df_users["orgUnitName"].apply(lambda x: find_best_match(x, org_unit_names))
    df_users = df_users.merge(df_org_units[["name", "id"]], left_on="assigned_orgUnitName", right_on="name", how="left")
    df_users.rename(columns={"id": "assigned_orgUnit"}, inplace=True)
    df_users.drop(columns=["name"], inplace=True)
    df_users.dropna(subset=["assigned_orgUnit"], inplace=True)
    df_users["username"] = df_users["User Full Name"].apply(generate_username)
    df_users["password"] = df_users["User Full Name"].apply(generate_password)
    return df_users

# Creating a user in DHIS2
def create_user(user):
    url = f"{DHIS2_BASE_URL}/api/users"
    user_payload = {
        # Must have parameters
        "firstName": user["User Full Name"].split()[0],
        "surname": user["User Full Name"].split()[-1],
        "username": user["username"],
        "password": user["password"],
        "organisationUnits": [{"id": user["assigned_orgUnit"]}],
        "dataViewOrganisationUnits" : [{"id": user["assigned_orgUnit"]}],
        "userRoles": [{"id": user.get("userRole")}],
        "userGroups": [{"id": user.get("userGroup")}]
    }
    # Optional parameters
    if pd.notna(user.get("Email")):
        user_payload["email"] = user["Email"]
    if pd.notna(user.get("Phone Number")):
        user_payload["phoneNumber"] = user["Phone Number"]
    response = requests.post(url, json=user_payload, auth=HTTPBasicAuth(USERNAME, PASSWORD))
    return response

# Sending users to DHIS2 and saving to an Excel_file
def send_users_to_dhis2(df_users, district_name, output_file="created_users.xlsx"):
    created_users = []
    for _, user in df_users.iterrows():
        response = create_user(user)
        if response.status_code == 201:
            created_users.append({
                "District Name": district_name,
                "Full Name": user["User Full Name"],
                "Username": user["username"],
                "Password": user["password"],
                "Assigned Org Unit": user["assigned_orgUnitName"],
                "Phone Number": user.get("Phone Number", ""),
                "Email": user.get("Email"),
            })
            print(f"✅ User {user['username']} created successfully!, password is {user['password']}")

        else:
            error_message = response.json().get("message", "Unknown error")
            print(f"❌ Failed to create user {user['username']}: {error_message}")

# Saving to Excel file.
    if created_users:
        df_created_users = pd.DataFrame(created_users)
        if os.path.exists(output_file):
            with pd.ExcelWriter(output_file, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
                df_created_users.to_excel(writer, index=False, header=False, startrow=writer.sheets['Sheet1'].max_row)
        else:
            df_created_users.to_excel(output_file, index=False)
        print(f"📂 Created users saved to {output_file}")

# Main Methord (Execution Poin)
if __name__ == "__main__":
    df_users, df_org_units = load_data()
    df_users = assign_org_units(df_users, df_org_units)
    send_users_to_dhis2(df_users, district_name)