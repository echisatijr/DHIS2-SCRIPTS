"""
CA Migration Script
Migrates organisation units from a source DHIS2 instance to a destination instance based on UIDs.
Preserves UIDs and metadata to maintain data continuity and relationships.
"""

import requests
import getpass
import os
import pandas as pd
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


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

# Base directory for data files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "data"))


def read_excel_or_delimited(path):
    """Try to read file as CSV or Excel with flexible delimiter detection."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    # If it's a CSV file, try CSV parsing first
    if path.lower().endswith(".csv"):
        delimiters = [",", "\t", ";", "|"]
        for delimiter in delimiters:
            try:
                df = pd.read_csv(path, delimiter=delimiter)
                if len(df.columns) > 1:
                    return df
            except Exception:
                continue
    
    # Try Excel
    try:
        return pd.read_excel(path)
    except Exception:
        pass

    # Try various CSV delimiters as fallback
    delimiters = ["\t", ";", ",", "|"]
    for delimiter in delimiters:
        try:
            df = pd.read_csv(path, delimiter=delimiter)
            if len(df.columns) > 1:
                return df
        except Exception:
            continue

    raise ValueError(f"Could not parse file {path} as Excel or CSV with any delimiter")


def resolve_column_name(df, possible_names):
    """Find a column in DataFrame by trying multiple possible names (case-insensitive, space-insensitive)."""
    normalized_columns = {col.lower().replace(" ", ""): col for col in df.columns}
    for name in possible_names:
        normalized_name = name.lower().replace(" ", "")
        if normalized_name in normalized_columns:
            return normalized_columns[normalized_name]
    return None


def normalize_date(date_value):
    """Convert date to ISO format (YYYY-MM-DD) for DHIS2."""
    if not date_value or pd.isna(date_value) or str(date_value).strip().lower() in ("nan", ""):
        return "1970-01-01"
    
    date_str = str(date_value).strip()
    
    # Try to parse with pandas
    try:
        parsed_date = pd.to_datetime(date_str)
        return parsed_date.strftime("%Y-%m-%d")
    except Exception:
        pass
    
    # Fallback to default
    return "1970-01-01"


def get_org_unit_from_source(session, base_url, uid):
    """Fetch organisation unit details from source instance by UID."""
    url = f"{base_url}/api/organisationUnits/{uid}"
    response = session.get(
        url,
        timeout=30,
    )

    if response.status_code == 200:
        return response.json()
    else:
        return None


def create_org_unit_in_destination(session, base_url, payload):
    """Create org unit in destination DHIS2 and return success status."""
    url = f"{base_url}/api/organisationUnits"
    response = session.post(
        url,
        json=payload,
        timeout=30,
    )

    if response.status_code in (200, 201):
        return True, response.json()
    else:
        try:
            message = response.json()
        except ValueError:
            message = response.text
        return False, message


def create_session_with_retry(username, password):
    """Create a requests session with retry logic."""
    session = requests.Session()
    session.auth = HTTPBasicAuth(username, password)
    session.headers.update({"Content-Type": "application/json"})

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def main():
    # Get source and destination base URLs
    source_base_url = os.getenv("DHIS2_BASE_URL_TEST")
    if not source_base_url:
        source_base_url = input("Enter the source DHIS2 base URL (e.g., https://source.org/dhis): ").strip()

    destination_base_url = os.getenv("DHIS2_BASE_URL_MAIN")
    if not destination_base_url:
        destination_base_url = input("Enter the destination DHIS2 base URL (e.g., https://destination.org/dhis): ").strip()

    # Get destination credentials
    dest_username = os.getenv("DHIS2_USERNAME")
    if not dest_username:
        dest_username = input("Enter destination DHIS2 username: ").strip()

    dest_password = os.getenv("DHIS2_PASSWORD")
    if not dest_password:
        dest_password = getpass.getpass("Enter destination DHIS2 password: ")

    # Get source credentials
    source_username = os.getenv("DHIS2_USERNAME")
    if not source_username:
        source_username = input("Enter source DHIS2 username: ").strip()

    source_password = os.getenv("DHIS2_PASSWORD")
    if not source_password:
        source_password = getpass.getpass("Enter source DHIS2 password: ")

    # Get input file path
    file_path = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "ca_to_migrate_sample.csv"))
    
    if not file_path:
        file_path = input("Enter the CA migration file path (default: ../data/ca_to_migrate.xlsx): ").strip()

    df = read_excel_or_delimited(file_path)

    # Resolve required columns - only UID is required
    uid_col = resolve_column_name(df, ["uid", "id", "orgunit_uid", "ca_uid"])

    # Resolve optional columns
    dest_parent_uid_col = resolve_column_name(df, ["destination_parent_uid", "destination parent uid", "new_parent_uid", "new parent uid", "parent_uid", "parent uid"])

    if uid_col is None:
        raise ValueError(
            f"Missing required UID column in the migration file. "
            f"Expected columns like: uid, id, orgunit_uid, ca_uid. "
            f"Available columns: {list(df.columns)}"
        )

    # Create destination session
    dest_session = create_session_with_retry(dest_username, dest_password)

    # Create source session
    source_session = create_session_with_retry(source_username, source_password)

    migrated = 0
    failed = 0
    migrated_units = []

    for idx, row in df.iterrows():
        uid = str(row.get(uid_col, "")).strip()
        dest_parent_uid = str(row.get(dest_parent_uid_col, "")).strip() if dest_parent_uid_col else ""

        if not uid:
            print(f"Skipping incomplete row {idx + 2}: UID is empty")
            continue

        print(f"\n📦 Migrating org unit: {uid}")

        # Fetch from source
        org_unit = get_org_unit_from_source(source_session, source_base_url, uid)

        if not org_unit:
            failed += 1
            print(f"❌ Failed to fetch from source: {uid}")
            migrated_units.append({
                "Name": "N/A",
                "UID": uid,
                "Status": "❌ Failed",
                "Source Instance": source_base_url,
                "Destination Instance": destination_base_url,
                "Code": "",
                "Parent UID": "",
                "Short name": "",
                "Description": "Failed to fetch from source",
                "Opening date": ""
            })
            continue

        # Prepare payload for destination - fetch all data from source DHIS2
        org_name = org_unit.get("name", "")
        org_code = org_unit.get("code", "")
        org_short_name = org_unit.get("shortName", org_name[:50])
        org_description = org_unit.get("description", "")
        opening_date = org_unit.get("openingDate", "1970-01-01")
        org_level = org_unit.get("level", 5)

        # Determine parent UID - use destination override if provided, otherwise use source parent
        if dest_parent_uid and dest_parent_uid.lower() != "nan":
            parent_uid = dest_parent_uid
        else:
            parent_uid = org_unit.get("parent", {}).get("id", "")

        if not parent_uid:
            failed += 1
            print(f"❌ Failed: No parent UID found for {org_name}")
            migrated_units.append({
                "Name": org_name,
                "UID": uid,
                "Status": "❌ Failed",
                "Source Instance": source_base_url,
                "Destination Instance": destination_base_url,
                "Code": org_code,
                "Parent UID": "",
                "Short name": org_short_name,
                "Description": "No parent UID found",
                "Opening date": opening_date
            })
            continue

        # Build migration payload
        payload = {
            "id": uid,  # Preserve UID
            "name": org_name,
            "shortName": org_short_name,
            "openingDate": normalize_date(opening_date),
            "parent": {"id": parent_uid},
            "level": org_level,
        }

        if org_code and str(org_code).strip():
            payload["code"] = str(org_code).strip()

        if org_description and str(org_description).strip():
            payload["description"] = str(org_description).strip()

        # Create in destination
        success, message = create_org_unit_in_destination(dest_session, destination_base_url, payload)

        if success:
            migrated += 1
            print(f"✅ Successfully migrated: {org_name} (UID: {uid})")
            migrated_units.append({
                "Name": org_name,
                "UID": uid,
                "Status": "✅ Success",
                "Source Instance": source_base_url,
                "Destination Instance": destination_base_url,
                "Code": org_code,
                "Parent UID": parent_uid,
                "Short name": org_short_name,
                "Description": org_description,
                "Opening date": opening_date
            })
        else:
            failed += 1
            error_msg = message.get("message", str(message)) if isinstance(message, dict) else str(message)
            print(f"❌ Failed to migrate: {org_name} | {error_msg}")
            migrated_units.append({
                "Name": org_name,
                "UID": uid,
                "Status": "❌ Failed",
                "Source Instance": source_base_url,
                "Destination Instance": destination_base_url,
                "Code": org_code,
                "Parent UID": parent_uid,
                "Short name": org_short_name,
                "Description": error_msg[:100],
                "Opening date": opening_date
            })

    # Save results
    output_file = os.path.normpath(os.path.join(DATA_DIR, "ca_migrated.xlsx"))
    output_df = pd.DataFrame(migrated_units)
    output_df = output_df[[
        "Name",
        "UID",
        "Status",
        "Source Instance",
        "Destination Instance",
        "Code",
        "Parent UID",
        "Short name",
        "Description",
        "Opening date"
    ]]
    output_df.to_excel(output_file, index=False)
    print(f"\n📂 Migration results saved to {output_file}")

    print(f"\n📊 Summary: migrated={migrated}, failed={failed}")


if __name__ == "__main__":
    main()
