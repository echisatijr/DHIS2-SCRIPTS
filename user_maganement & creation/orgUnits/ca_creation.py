import os
import getpass
import requests
import pandas as pd
from requests.auth import HTTPBasicAuth


def load_env_file(path="../../.env"):
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

BASE_URL = os.getenv("DHIS2_BASE_URL_TEST") or os.getenv("DHIS2_BASE_URL")
USERNAME = os.getenv("DHIS2_USERNAME")
PASSWORD = os.getenv("DHIS2_PASSWORD")

if not BASE_URL:
    BASE_URL = input("Write the DHIS2 base URL (e.g., https://example.org/dhis): ").strip()
if not USERNAME:
    USERNAME = input("Write your username: ").strip()
if not PASSWORD:
    PASSWORD = getpass.getpass("Write your password: ")


def read_excel_or_delimited(path):
    """Read Excel or a delimited text file when the extension is mislabeled."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    try:
        if path.lower().endswith((".xlsx", ".xls")):
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

    return pd.read_excel(path)


def load_ca_creation_file():
    default_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "ca_to_create.xlsx"))
    print(f"Looking for CA creation file: {default_path}")

    if os.path.exists(default_path):
        return read_excel_or_delimited(default_path)

    custom_path = input("Enter the CA creation Excel/CSV file path or press Enter to use the default file: ").strip()
    if not custom_path:
        raise FileNotFoundError("No CA creation file found. Please provide a file with Parent Name, Parent UID, OrgUnit Name, and Level columns.")
    return read_excel_or_delimited(custom_path)


def resolve_column_name(df, possible_names):
    normalized_map = {str(col).strip().lower().replace(" ", "_"): col for col in df.columns}
    for name in possible_names:
        key = str(name).strip().lower().replace(" ", "_")
        if key in normalized_map:
            return normalized_map[key]
    return None


def build_payload(ca_name, parent_id, org_level, ca_code=None):
    payload = {
        "name": str(ca_name).strip(),
        "shortName": str(ca_name).strip()[:50],
        "openingDate": "2024-01-01",
        "parent": {"id": parent_id},
        "level": int(org_level),
    }

    if ca_code:
        payload["code"] = str(ca_code).strip()

    return payload


def create_org_unit(session, payload):
    url = f"{BASE_URL}/api/organisationUnits"
    response = session.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=30,
    )

    if response.status_code in (200, 201):
        body = response.json()
        created_id = body.get("uid") or body.get("response", {}).get("uid") or body.get("id")
        return True, created_id, response.text

    try:
        message = response.json()
    except ValueError:
        message = response.text

    return False, None, message


def main():
    file_path = input("Enter the CA creation file path (default: ../data/ca_to_create.xlsx): ").strip()
    if not file_path:
        file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "ca_to_create.xlsx"))

    df = read_excel_or_delimited(file_path)

    parent_name_col = resolve_column_name(df, ["parent_name", "parent name", "parent", "parentname"])
    parent_uid_col = resolve_column_name(df, ["parent_uid", "parent uid", "parent_id", "parent id", "uid_parent"])
    orgunit_name_col = resolve_column_name(df, ["orgunit_name", "org_unit_name", "orgunit to create", "org unit to create", "ca_name", "catchment_area", "name", "ca"])
    level_col = resolve_column_name(df, ["level", "org_level", "organisation_level", "orgunit_level"])

    missing = []
    for col_name, label in [(parent_name_col, "Parent Name"), (parent_uid_col, "Parent UID"), (orgunit_name_col, "OrgUnit Name"), (level_col, "Level")]:
        if col_name is None:
            missing.append(label)

    if missing:
        raise ValueError(
            "Missing required columns in the CA creation file. "
            "Expected columns include: Parent Name, Parent UID, OrgUnit Name, Level. "
            f"Detected missing: {missing}"
        )

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    created = 0
    failed = 0

    for _, row in df.iterrows():
        parent_name = str(row.get(parent_name_col, "")).strip()
        parent_uid = str(row.get(parent_uid_col, "")).strip()
        org_name = str(row.get(orgunit_name_col, "")).strip()
        level_value = row.get(level_col)

        if not parent_name or not parent_uid or not org_name or pd.isna(level_value):
            print(f"Skipping incomplete row: parent_name={parent_name!r}, parent_uid={parent_uid!r}, org_name={org_name!r}, level={level_value!r}")
            continue

        try:
            org_level = int(level_value)
        except (TypeError, ValueError):
            print(f"Skipping invalid level row: parent={parent_name}, org={org_name}, level={level_value!r}")
            continue

        payload = build_payload(org_name, parent_uid, org_level)

        print(f"Creating CA: {org_name} under parent '{parent_name}' ({parent_uid}) at level {org_level}")
        success, created_id, message = create_org_unit(session, payload)

        if success:
            created += 1
            print(f"✅ Created: {org_name} | ID: {created_id}")
        else:
            failed += 1
            print(f"❌ Failed: {org_name} | {message}")

    print(f"\nSummary: created={created}, failed={failed}")


if __name__ == "__main__":
    main()
