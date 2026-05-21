import requests, os, getpass
from requests.auth import HTTPBasicAuth

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

BASE_URL = os.getenv("DHIS2_BASE_URL") 
USERNAME = os.getenv("DHIS2_USERNAME")
PASSWORD = os.getenv("DHIS2_PASSWORD")

if not BASE_URL:
    BASE_URL = input("Write the DHIS2 base URL (e.g., https://example.org/dhis): ")
if not USERNAME:
    USERNAME = input("Write your username: ")
if not PASSWORD:
    PASSWORD = getpass.getpass("Write your password: ")

#user ids to be deleted
uids = [
    "OlMAXtz2XuW",
    "XU8LpU0sQbM",
    "xs5dghN3UsY",
    "ccyA6RKuuji",
    "iIU5sdAZBt6",
    "mLiaFXJapP7",
    "k5NZqm53FqT",

    "BmEWTtjfsLB",
    "SDEgmSMmEBQ",
    "PLOkTmL0jp4",
    "il1Q7fRQdpu",
    "XbjhU5qRfnp",
    "aRfN38vsSPZ",
    "CF14VGPeZeY"
]

def delete_user(uid):
    url = f"{BASE_URL}/api/29/users/{uid}"

    response = requests.delete(
        url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=20
    )

    if response.status_code == 200:
        print(f"✅ Deleted: {uid}")
    else:
        print(f"❌ Failed: {uid} | {response.status_code} | {response.text}")

for uid in uids:
    delete_user(uid)