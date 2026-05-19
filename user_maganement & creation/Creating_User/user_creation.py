# Importing requred python models
import os, getpass, logging, requests
import pandas as pd
from datetime import datetime
from fuzzywuzzy import fuzz, process
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

# Optional speed optimization for fuzzy matching:
# pip install python-Levenshtein

# Load environment variables from a .env file if present
def load_env_file(path=f"../../.env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            if not line.strip() or line.strip().startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.strip().split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_env_file()

DHIS2_BASE_URL = os.getenv("DHIS2_BASE_URL", "https://ccdev.org/chistest")
USERNAME = os.getenv("DHIS2_USERNAME")
PASSWORD = os.getenv("DHIS2_PASSWORD")

if not USERNAME:
    USERNAME = input("Write your username: ")
if not PASSWORD:
    PASSWORD = getpass.getpass("Write your password: ")

# Getting District.
district = input("Write the district name: ")
# First letter to be capital and the rest to be small letter.
district_name = f"{district}-DHO"

# Default user role id and group id
DEFAULT_USER_ROLE = "K7DkWdiGSbA" # Community Tracker

# Configure a shared requests session with retry support
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
    raise_on_status=False
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

# Loading user and organization unit data from Excel files
def load_data(user_file=(f"data/{district}_users.xlsx"), org_unit_file = (f"data/{district}_CA.xlsx")):
    df_users = pd.read_excel(user_file)
    df_org_units = pd.read_excel(org_unit_file)
    return df_users, df_org_units

# Choose the created users file if present
def find_created_users_file():
    candidates = [f"data/{district_name}_created_users.xlsx"]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

# Load previously created users from Excel for offline duplicate checking
def load_created_users():
    created_users_file = find_created_users_file()
    if not created_users_file:
        logging.info("No created users file found. Skipping offline duplicate check.")
        return pd.DataFrame()
    try:
        df_created = pd.read_excel(created_users_file)
        logging.info(f"Loaded created users from {created_users_file}")
        return df_created
    except Exception as exc:
        logging.warning(f"Unable to load created users file '{created_users_file}': {exc}")
        return pd.DataFrame()

# Filter out users whose full name already exists in the created users list
def filter_already_created_users(df_users, df_created_users):
    print("\n🔎 Checking for already created users by full name...")
    if df_created_users.empty:
        print("✅ No created users file available, processing all users.")
        return df_users

    if "Full Name" not in df_created_users.columns:
        print("⚠️ Created users file does not contain a 'Full Name' column. Skipping offline duplicate check.")
        return df_users

    created_full_names = set(df_created_users["Full Name"].astype(str).str.strip())
    df_users["User Full Name"] = df_users["User Full Name"].astype(str).str.strip()

    duplicate_mask = df_users["User Full Name"].isin(created_full_names)
    skipped_users = df_users.loc[duplicate_mask, "User Full Name"].tolist()
    if skipped_users:
        print(f"⏭️ Skipping {len(skipped_users)} already created user(s):")
        for full_name in skipped_users:
            print(f"   - {full_name}")
    else:
        print("✅ No matching created users found. Continuing.")

    df_users_filtered = df_users.loc[~duplicate_mask].copy()
    if df_users_filtered.empty:
        print("✅ All users in the input list have already been created.")
    return df_users_filtered

# Checking if a username already exists in DHIS2
def username_exists(username):
    try:
        response = session.get(
            f"{DHIS2_BASE_URL}/api/users?filter=username:eq:{username}&fields=id",
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            timeout=15
        )
        if response.status_code == 200:
            try:
                return len(response.json().get("users", [])) > 0
            except requests.exceptions.JSONDecodeError:
                print("❌ Error: DHIS2 response is not valid JSON.")
        else:
            print(f"❌ Error: Failed to check username existence. Status code: {response.status_code}")
    except requests.exceptions.RequestException as exc:
        print(f"❌ Network error while checking username '{username}': {exc}")
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
    df_users["parent"] = df_org_units["parent_name"]
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
    try:
        response = session.post(
            url,
            json=user_payload,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            timeout=20
        )
        return response
    except requests.exceptions.RequestException as exc:
        print(f"❌ Network error while creating user '{user['User Full Name']}' ({user['username']}): {exc}")
        return None

# Sending users to DHIS2 and saving to an Excel_file
def send_users_to_dhis2(df_users, district_name, output_file=f"data/{district_name}_created_users.xlsx"):
    created_users = []
    for _, user in df_users.iterrows():
        response = create_user(user)
        if response is None:
            continue
        if response.status_code == 201:
            try:
                response_body = response.json()
            except ValueError:
                response_body = {}

            created_uid = response_body.get("uid") or response_body.get("response", {}).get("uid")

            created_users.append({
                #"District Name": district_name,
                "Facility": user["parent"],
                "Full Name": user["User Full Name"],
                "Username": user["username"],
                "Password": user["password"],
                "UID": created_uid,
                "Assigned Org Unit": user["assigned_orgUnitName"],
                "Phone Number": user.get("Phone Number", ""),
                "Email": user.get("Email"),
            })
            print(f"✅ User {user['username']} created successfully!, password is {user['password']} UID: {created_uid}")

        else:
            try:
                error_message = response.json().get("message", "Unknown error")
            except Exception:
                error_message = response.text if response is not None else "No response"
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

    df_created_users = load_created_users()
    df_users = filter_already_created_users(df_users, df_created_users)

    if df_users.empty:
        logging.info("No users left to process after offline duplicate filtering.")
        exit()

    df_users = assign_org_units(df_users, df_org_units)
    send_users_to_dhis2(df_users, district_name)