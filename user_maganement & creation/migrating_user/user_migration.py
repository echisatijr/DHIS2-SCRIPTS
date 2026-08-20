import pandas as pd
import requests, os, getpass
from requests.auth import HTTPBasicAuth
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CONFIGURATION
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

SOURCE_BASE_URL = os.getenv("DHIS2_BASE_URL_TEST")
TARGET_BASE_URL = os.getenv("DHIS2_BASE_URL_MAIN")

SOURCE_USERNAME = os.getenv("DHIS2_USERNAME")
SOURCE_PASSWORD = os.getenv("DHIS2_PASSWORD")

TARGET_USERNAME = os.getenv("DHIS2_USERNAME")
TARGET_PASSWORD = os.getenv("DHIS2_PASSWORD")


if not SOURCE_BASE_URL:
    SOURCE_BASE_URL = input("Write the source DHIS2 base URL (e.g., https://example.org/dhis): ")
if not SOURCE_USERNAME:
    SOURCE_USERNAME = input("Write your username: ")
if not SOURCE_PASSWORD:
    SOURCE_PASSWORD = getpass.getpass("Write your password: ")

if not TARGET_BASE_URL:
    TARGET_BASE_URL = input("Write the target DHIS2 base URL (e.g., https://example.org/dhis): ")
if not TARGET_USERNAME:
    TARGET_USERNAME = input("Write your username: ")
if not SOURCE_PASSWORD:
    TARGET_PASSWORD = getpass.getpass("Write your password: ")

#EXCEL_FILE = (f"../user_data/usernames.xlsx")


EXCEL_FILE = "../data/usernamess.xlsx"

DEFAULT_USER_GROUPS = [
    #"OPJ9nY0fsmX",   # Tasking group /main
    #"RHVLhmG812z",   # mchinji HSA /main
    "CaO6Svyo4KX" # Balaka HSA/ main
]

# SESSION
session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
})

# PASSWORD GENERATOR
def generate_password(full_name):
    parts = full_name.split()
    first_letter = parts[0][0].upper()
    last_name = parts[-1].lower()
    current_year = datetime.now().year
    return f"{first_letter}{last_name}@{current_year}"

# LOAD USERNAMES FROM THE SPECIFIED FILE
def load_usernames(file_path):
    try:
        df = pd.read_excel(file_path)

        if "username" not in df.columns:
            raise Exception("Missing 'username' column")

        usernames = df["username"].dropna().astype(str).str.strip().tolist()

        print(f"📥 Loaded {len(usernames)} usernames from Excel")

        return usernames

    except Exception as e:
        print(f"❌ ERROR loading Excel file: {e}")
        return []
    
# GET USER FROM SOURCE INSTANCE
def get_user_from_source(username):
    try:
        print(f"🔎 Fetching user from SOURCE: {username}")

        fields = (
            "id,firstName,surname,email,phoneNumber,"
            "userCredentials[username,userRoles[id,name]],"
            "organisationUnits[id,name],"
            "dataViewOrganisationUnits[id,name],"
            "userGroups[id,name]"
        )

        url = (
            f"{SOURCE_BASE_URL}/api/users"
            f"?filter=username:eq:{username}"
            f"&fields={fields}"
        )

        response = session.get(
            url,
            auth=HTTPBasicAuth(SOURCE_USERNAME, SOURCE_PASSWORD),
            timeout=30,
            verify=False
        )

        if response.status_code != 200:
            print(f"❌ SOURCE ERROR {username}: {response.status_code}")
            print(response.text)
            return None

        users = response.json().get("users", [])

        if not users:
            print(f"⚠️ User not found in SOURCE: {username}")
            return None

        print(f"✅ Found user in SOURCE: {username}")
        return users[0]

    except Exception as e:
        print(f"❌ Exception fetching SOURCE user {username}: {e}")
        return None

# CHECKING EXITANCE OF A USER IN TARGET
def user_exists_in_target(username):
    try:
        url = (
            f"{TARGET_BASE_URL}/api/users"
            f"?filter=username:eq:{username}&fields=id"
        )

        response = session.get(
            url,
            auth=HTTPBasicAuth(TARGET_USERNAME, TARGET_PASSWORD),
            timeout=30,
            verify=False
        )

        if response.status_code != 200:
            print(f"⚠️ TARGET CHECK FAILED: {username}")
            return False

        users = response.json().get("users", [])
        return len(users) > 0

    except Exception as e:
        print(f"❌ TARGET CHECK ERROR {username}: {e}")
        return False

# CREATE USER IN TARGET
def create_user_in_target(user_data):
    try:
        credentials = user_data.get("userCredentials", {})
        username = credentials.get("username")

        full_name = f"{user_data.get('firstName','')} {user_data.get('surname','')}"
        password = generate_password(full_name)

        print(f"🔐 Creating user: {username}")
        print(f"🔑 Generated password: {password}")

        payload = {
            "firstName": user_data.get("firstName", ""),
            "surname": user_data.get("surname", ""),
            "email": user_data.get("email", ""),
            "phoneNumber": user_data.get("phoneNumber", ""),
            "userCredentials": {
                "username": username,
                "password": password,
                "userRoles": [
                    {"id": r["id"]} for r in credentials.get("userRoles", [])
                ]
            },
            "organisationUnits": [
                {"id": o["id"]} for o in user_data.get("organisationUnits", [])
            ],
            "dataViewOrganisationUnits": [
                {"id": o["id"]} for o in user_data.get("dataViewOrganisationUnits", [])
            ],
            "userGroups": [
                {"id": gid}
                for gid in DEFAULT_USER_GROUPS
            ]
        }

        response = session.post(
            f"{TARGET_BASE_URL}/api/users",
            json=payload,
            auth=HTTPBasicAuth(TARGET_USERNAME, TARGET_PASSWORD),
            timeout=30,
            verify=False
        )

        if response.status_code == 201:
            print(f"✅ SUCCESS: {username} created")
            return True
        else:
            print(f"❌ FAILED: {username}")
            print(f"Status: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"❌ EXCEPTION creating user: {e}")
        return False

# MAIN MIGRATION
def migrate_users():
    usernames = ["mchinthowa"]  # load_usernames(EXCEL_FILE)

    if not usernames:
        print("⚠️ No users to process")
        return

    print("\n🚀 STARTING MIGRATION PROCESS")
    print("=" * 50)

    migrated = 0
    skipped = 0
    failed = 0

    for username in usernames:

        print("\n--------------------------------------------------")
        print(f"👤 Processing: {username}")
        print("--------------------------------------------------")

        if user_exists_in_target(username):
            print(f"⚠️ Already exists: {username}")
            skipped += 1
            continue

        user_data = get_user_from_source(username)

        if not user_data:
            failed += 1
            continue

        success = create_user_in_target(user_data)

        if success:
            migrated += 1
        else:
            failed += 1

    print("\n========================================")
    print("🎯 MIGRATION COMPLETED")
    print("========================================")
    print(f"✅ Migrated: {migrated}")
    print(f"⚠️ Skipped: {skipped}")
    print(f"❌ Failed: {failed}")
    print("========================================")

# RUN SCRIPT
if __name__ == "__main__":
    migrate_users()