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

DHIS2_BASE_URL = os.getenv("DHIS2_BASE_URL_TEST") 
USERNAME = os.getenv("DHIS2_USERNAME")
PASSWORD = os.getenv("DHIS2_PASSWORD")

if not DHIS2_BASE_URL:
    DHIS2_BASE_URL = input("Write the DHIS2 base URL (e.g., https://example.org/dhis): ")
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
DATA_DIR = os.path.normpath(DATA_DIR)


def read_excel_or_delimited(path):
    """Read an Excel file or a text file when the extension is mislabeled."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    lower_path = path.lower()
    try:
        if lower_path.endswith((".xlsx", ".xls")):
            return pd.read_excel(path)
    except Exception:
        pass

    try:
        with open(path, "rb") as file:
            sample = file.read(2048)
        if sample.startswith(b"PK"):
            return pd.read_excel(path)
    except Exception:
        pass

    for sep in ["\t", ";", ",", "|"]:
        try:
            df = pd.read_csv(path, sep=sep)
            if df.shape[1] > 1:
                return df
        except Exception:
            continue

    try:
        return pd.read_excel(path)
    except Exception as exc:
        raise ValueError(f"Unable to read file '{path}'. Please ensure it is a valid Excel or delimited table. {exc}") from exc


# Loading user and organization unit data from Excel files
def load_data(user_file=(os.path.join(DATA_DIR, f"{district}_users.xlsx")), org_unit_file=(os.path.join(DATA_DIR, f"{district}_CA.xlsx"))):
    df_users = read_excel_or_delimited(user_file)
    df_org_units = read_excel_or_delimited(org_unit_file)
    return df_users, df_org_units

# Choose the created users file if present
def find_created_users_file():
    candidates = [os.path.join(DATA_DIR, f"{district}_created_users.xlsx")]
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

    if "CHW Fullname" not in df_created_users.columns:
        print("⚠️ Created users file does not contain a 'CHW Fullname' column. Skipping offline duplicate check.")
        return df_users

    created_full_names = set(df_created_users["CHW Fullname"].astype(str).str.strip())
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
    org_unit_facility_names = df_org_units["parent_name"].tolist()

    # Fast lookup maps
    name_to_id = dict(zip(df_org_units["name"], df_org_units["id"]))
    name_to_parent_id = dict(zip(df_org_units["name"], df_org_units["parent_id"]))
    name_to_parent_name = dict(zip(df_org_units["name"], df_org_units["parent_name"]))

    assigned_ids = []
    assigned_names = []
    parent_ids = []
    parent_names = []

    for _, user in df_users.iterrows():

        assigned_id = None
        assigned_name = None
        parent_id = None
        parent_name = None

        uid = str(user.get("uid", "")).strip()
        ca_name = str(user.get("orgUnitName", "")).strip()
        facility_name = str(user.get("Facility", "")).strip()

        # --------------------------------------------------
        # STEP 1: DIRECT UID (HIGHEST PRIORITY)
        # --------------------------------------------------
        if uid and uid.lower() != "nan":
            assigned_id = uid
            assigned_name = "DIRECT_UID"
            parent_id = None
            parent_name = None

            print(f"✅ Using direct UID for {user['User Full Name']}")

        else:
            # --------------------------------------------------
            # STEP 2: CATCHMENT AREA (FUZZY)
            # --------------------------------------------------
            try:
                if ca_name and ca_name.lower() != "nan":
                    matched_ca = find_best_match(ca_name, org_unit_names)

                    assigned_id = name_to_id.get(matched_ca)
                    assigned_name = matched_ca

                    parent_id = name_to_parent_id.get(matched_ca)
                    parent_name = name_to_parent_name.get(matched_ca)

                    print(f"✅ CA matched: {ca_name} -> {matched_ca}")

            except Exception:
                print(f"⚠️ CA not found: {ca_name}")

            # --------------------------------------------------
            # STEP 3: FACILITY (FUZZY FALLBACK)
            # --------------------------------------------------
            if assigned_id is None:
                try:
                    if facility_name and facility_name.lower() != "nan":
                        matched_facility = find_best_match(facility_name, org_unit_facility_names)

                        assigned_id = name_to_id.get(matched_facility)
                        assigned_name = matched_facility

                        parent_id = name_to_parent_id.get(matched_facility)
                        parent_name = name_to_parent_name.get(matched_facility)

                        print(f"✅ Facility used: {facility_name} -> {matched_facility}")

                except Exception:
                    print(f"⚠️ Facility not found: {facility_name}")

            # --------------------------------------------------
            # STEP 4: UPPER ORG UNIT (FINAL FALLBACK)
            # --------------------------------------------------
            if assigned_id is None:
                try:
                    if facility_name and facility_name.lower() != "nan":
                        matched_facility = find_best_match(facility_name, org_unit_names)

                        assigned_id = name_to_parent_id.get(matched_facility)
                        assigned_name = name_to_parent_name.get(matched_facility)

                        parent_id = None
                        parent_name = None

                        print(f"⚠️ Using upper org unit for {user['User Full Name']}")

                except Exception:
                    print(f"❌ Could not resolve org unit for {user['User Full Name']}")
                    continue

        assigned_ids.append(assigned_id)
        assigned_names.append(assigned_name)
        parent_ids.append(parent_id)
        parent_names.append(parent_name)

    # --------------------------------------------------
    # APPLY RESULTS BACK TO DATAFRAME
    # --------------------------------------------------
    df_users = df_users.iloc[:len(assigned_ids)].copy()

    df_users["assigned_orgUnit"] = assigned_ids
    df_users["assigned_orgUnitName"] = assigned_names

    df_users["parent_orgunit_id"] = parent_ids
    df_users["parent_orgunit_name"] = parent_names

    # Username + password generation
    df_users["username"] = df_users["User Full Name"].apply(generate_username)
    df_users["password"] = df_users["User Full Name"].apply(generate_password)

    return df_users

def sanitize_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    if isinstance(value, float):
        if pd.isna(value):
            return None
        return value
    if isinstance(value, list):
        cleaned = []
        for item in value:
            sanitized = sanitize_value(item)
            if sanitized is not None:
                cleaned.append(sanitized)
        return cleaned if cleaned else None
    if isinstance(value, dict):
        cleaned_dict = {}
        for key, val in value.items():
            sanitized = sanitize_value(val)
            if sanitized is not None:
                cleaned_dict[key] = sanitized
        return cleaned_dict if cleaned_dict else None
    return value


# Creating a user in DHIS2
def create_user(user):
    url = f"{DHIS2_BASE_URL}/api/users"

    role_id = sanitize_value(user.get("userRole")) or DEFAULT_USER_ROLE
    group_id = sanitize_value(user.get("userGroup"))

    user_payload = {
        # Must have parameters
        "firstName": user["User Full Name"].split()[0],
        "surname": user["User Full Name"].split()[-1],
        "username": sanitize_value(user["username"]),
        "password": sanitize_value(user["password"]),
        "organisationUnits": [{"id": sanitize_value(user["assigned_orgUnit"])}],
        "dataViewOrganisationUnits": [{"id": sanitize_value(user["assigned_orgUnit"])}],
        "userRoles": [{"id": role_id}],
    }

    if group_id:
        user_payload["userGroups"] = [{"id": group_id}]

    email = sanitize_value(user.get("Email"))
    phone_number = sanitize_value(user.get("Phone Number"))

    if email:
        user_payload["email"] = email
    if phone_number:
        user_payload["phoneNumber"] = phone_number

    try:
        response = session.post(
            url,
            json=sanitize_value(user_payload),
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            timeout=20
        )
        return response
    except requests.exceptions.RequestException as exc:
        print(f"❌ Network error while creating user '{user['User Full Name']}' ({user['username']}): {exc}")
        return None

# Sending users to DHIS2 and saving to an Excel_file
def send_users_to_dhis2(df_users, district_name, output_file=os.path.join(DATA_DIR, f"{district}_created_users.xlsx")):
    created_users = []
    expected_columns = [
        "Catchment Area",
        "CA UID",
        "CHW Fullname",
        "Phone Number",
        "Facility Name",
        "Username",
        "Password",
    ]

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
                "Catchment Area": user["assigned_orgUnitName"],
                "CA UID": user.get("assigned_orgUnit", ""),
                "CHW Fullname": user["User Full Name"],
                "Phone Number": user.get("Phone Number", ""),
                "Facility Name": user.get("parent_orgunit_name", ""),
                "Username": user["username"],
                "Password": user["password"],
                "_created_uid": created_uid,
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
        df_created_users = df_created_users[[col for col in expected_columns if col in df_created_users.columns]]

        if not df_created_users.columns.equals(pd.Index(expected_columns[:len(df_created_users.columns)])):
            df_created_users = df_created_users.reindex(columns=expected_columns)

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