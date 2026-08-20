"""
CA Update Script
Updates organisation unit details in DHIS2 based on UIDs.
Allows partial updates - only provided fields are updated, others are preserved.
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

BASE_URL = os.getenv("DHIS2_BASE_URL_MAIN") #or os.getenv("DHIS2_BASE_URL")
USERNAME = os.getenv("DHIS2_USERNAME")
PASSWORD = os.getenv("DHIS2_PASSWORD")

if not BASE_URL:
    BASE_URL = input("Write the DHIS2 base URL (e.g., https://example.org/dhis): ").strip()
if not USERNAME:
    USERNAME = input("Write your username: ").strip()
if not PASSWORD:
    PASSWORD = getpass.getpass("Write your password: ")

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
        return None
    
    date_str = str(date_value).strip()
    
    # Try to parse with pandas
    try:
        parsed_date = pd.to_datetime(date_str)
        return parsed_date.strftime("%Y-%m-%d")
    except Exception:
        pass
    
    # Fallback
    return None


def get_org_unit(session, uid):
    """Fetch organisation unit details from DHIS2 by UID."""
    url = f"{BASE_URL}/api/organisationUnits/{uid}"
    response = session.get(
        url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=30,
    )

    if response.status_code == 200:
        return response.json()
    else:
        return None


def update_org_unit(session, uid, payload):
    """Update org unit in DHIS2 and return success status."""
    url = f"{BASE_URL}/api/organisationUnits/{uid}"
    response = session.put(
        url,
        json=payload,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=30,
    )

    if response.status_code in (200, 204):
        return True, response.text
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


def save_updated_units(updated_units, output_path):
    """Save updated org units to an Excel file."""
    if not updated_units:
        return

    output_df = pd.DataFrame(updated_units)
    output_df = output_df[[
        "Name",
        "UID",
        "Status",
        "Code",
        "Parent UID",
        "Short name",
        "Description",
        "Opening date",
        "Updates Applied"
    ]]
    output_df.to_excel(output_path, index=False)
    print(f"📂 Updated units saved to {output_path}")


def main():
    file_path = input("Enter the CA update file path (default: ../data/ca_to_update_sample.csv): ").strip()
    if not file_path:
        file_path = os.path.normpath(os.path.join(BASE_DIR, "..", "data", "ca_to_update_sample.csv"))

    df = read_excel_or_delimited(file_path)

    # Resolve required column
    uid_col = resolve_column_name(df, ["uid", "id", "orgunit_uid", "ca_uid"])

    # Resolve optional columns
    name_col = resolve_column_name(df, ["name", "orgunit_name", "ca_name"])
    code_col = resolve_column_name(df, ["code", "org_code", "ca_code"])
    parent_uid_col = resolve_column_name(df, ["parent_uid", "parent uid", "parent_id"])
    short_name_col = resolve_column_name(df, ["short_name", "shortname", "short name"])
    description_col = resolve_column_name(df, ["description", "desc"])
    opening_date_col = resolve_column_name(df, ["opening_date", "openingdate", "opening date"])

    if uid_col is None:
        raise ValueError(
            f"Missing required UID column in the update file. "
            f"Expected columns like: uid, id, orgunit_uid, ca_uid. "
            f"Available columns: {list(df.columns)}"
        )

    session = create_session_with_retry(USERNAME, PASSWORD)

    updated = 0
    failed = 0
    updated_units = []

    for idx, row in df.iterrows():
        uid = str(row.get(uid_col, "")).strip()

        if not uid or str(uid).lower() == "nan":
            print(f"Skipping incomplete row {idx + 2}: UID is empty")
            continue

        print(f"\n📝 Updating org unit: {uid}")

        # Fetch existing org unit
        org_unit = get_org_unit(session, uid)
        if not org_unit:
            failed += 1
            print(f"❌ Failed: Could not fetch org unit {uid}")
            updated_units.append({
                "Name": "N/A",
                "UID": uid,
                "Status": "❌ Failed",
                "Code": "",
                "Parent UID": "",
                "Short name": "",
                "Description": "Could not fetch org unit",
                "Opening date": "",
                "Updates Applied": "N/A"
            })
            continue

        # Build update payload with only provided fields
        payload = {}
        updates_applied = []

        # Name
        if name_col and pd.notna(row.get(name_col)):
            name_val = str(row.get(name_col, "")).strip()
            if name_val and str(name_val).lower() != "nan":
                payload["name"] = name_val
                updates_applied.append("Name")

        # Code
        if code_col and pd.notna(row.get(code_col)):
            code_val = str(row.get(code_col, "")).strip()
            if code_val and str(code_val).lower() != "nan":
                payload["code"] = code_val
                updates_applied.append("Code")

        # Parent UID
        if parent_uid_col and pd.notna(row.get(parent_uid_col)):
            parent_uid_val = str(row.get(parent_uid_col, "")).strip()
            if parent_uid_val and str(parent_uid_val).lower() != "nan":
                payload["parent"] = {"id": parent_uid_val}
                updates_applied.append("Parent UID")

        # Short name
        if short_name_col and pd.notna(row.get(short_name_col)):
            short_name_val = str(row.get(short_name_col, "")).strip()
            if short_name_val and str(short_name_val).lower() != "nan":
                payload["shortName"] = short_name_val
                updates_applied.append("Short name")

        # Description
        if description_col and pd.notna(row.get(description_col)):
            desc_val = str(row.get(description_col, "")).strip()
            if desc_val and str(desc_val).lower() != "nan":
                payload["description"] = desc_val
                updates_applied.append("Description")

        # Opening date
        if opening_date_col and pd.notna(row.get(opening_date_col)):
            normalized_date = normalize_date(row.get(opening_date_col))
            if normalized_date:
                payload["openingDate"] = normalized_date
                updates_applied.append("Opening date")

        # If no updates provided, skip
        if not payload:
            print(f"⏭️ Skipped: No updates provided for {uid}")
            continue

        # Perform update
        print(f"Updating: {', '.join(updates_applied)}")
        success, message = update_org_unit(session, uid, payload)

        if success:
            updated += 1
            print(f"✅ Updated: {org_unit.get('name')} | UID: {uid}")
            updated_units.append({
                "Name": org_unit.get("name", ""),
                "UID": uid,
                "Status": "✅ Success",
                "Code": payload.get("code", org_unit.get("code", "")),
                "Parent UID": payload.get("parent", {}).get("id", org_unit.get("parent", {}).get("id", "")),
                "Short name": payload.get("shortName", org_unit.get("shortName", "")),
                "Description": payload.get("description", org_unit.get("description", "")),
                "Opening date": payload.get("openingDate", org_unit.get("openingDate", "")),
                "Updates Applied": ", ".join(updates_applied)
            })
        else:
            failed += 1
            error_msg = message.get("message", str(message)) if isinstance(message, dict) else str(message)
            print(f"❌ Failed: {org_unit.get('name')} | {error_msg}")
            updated_units.append({
                "Name": org_unit.get("name", ""),
                "UID": uid,
                "Status": "❌ Failed",
                "Code": org_unit.get("code", ""),
                "Parent UID": org_unit.get("parent", {}).get("id", ""),
                "Short name": org_unit.get("shortName", ""),
                "Description": error_msg[:100],
                "Opening date": org_unit.get("openingDate", ""),
                "Updates Applied": "N/A"
            })

    # Save results
    output_file = os.path.normpath(os.path.join(DATA_DIR, "ca_updated.xlsx"))
    save_updated_units(updated_units, output_file)

    print(f"\n📊 Summary: updated={updated}, failed={failed}")


if __name__ == "__main__":
    main()
