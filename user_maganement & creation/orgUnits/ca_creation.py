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

BASE_URL = os.getenv("DHIS2_BASE_URL_MAIN") #or os.getenv("DHIS2_BASE_URL")
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
        if path.lower().endswith((".xlsx", ".xls", ".csv")):
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


def resolve_column_name(df, possible_names):
    """Resolve column names flexibly, case-insensitive and space-insensitive."""
    normalized_map = {str(col).strip().lower().replace(" ", "_"): col for col in df.columns}
    for name in possible_names:
        key = str(name).strip().lower().replace(" ", "_")
        if key in normalized_map:
            return normalized_map[key]
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


def get_parent_org_unit(session, parent_uid):
    """Fetch parent org unit details to determine child level."""
    url = f"{BASE_URL}/api/organisationUnits/{parent_uid}"
    response = session.get(
        url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=30,
    )
    if response.status_code == 200:
        return response.json()
    return None


def build_payload(ca_name, parent_id, ca_uid=None, ca_code=None, short_name=None, description=None, opening_date=None, parent_level=None):
    """Build DHIS2 org unit payload with optional UID and auto-derived level."""
    # Level is parent's level + 1
    org_level = int(parent_level) + 1 if parent_level else 5
    
    payload = {
        "name": str(ca_name).strip(),
        "shortName": (str(short_name).strip() if short_name and str(short_name).strip() else str(ca_name).strip()[:50]),
        "openingDate": normalize_date(opening_date),
        "parent": {"id": parent_id},
        "level": int(org_level),
    }

    # Include UID if provided and not empty
    if ca_uid and str(ca_uid).strip() and str(ca_uid).strip().lower() != "nan":
        payload["id"] = str(ca_uid).strip()

    # Include code if provided
    if ca_code and str(ca_code).strip() and str(ca_code).strip().lower() != "nan":
        payload["code"] = str(ca_code).strip()

    # Include description if provided
    if description and str(description).strip() and str(description).strip().lower() != "nan":
        payload["description"] = str(description).strip()

    return payload


def create_org_unit(session, payload):
    """Create org unit in DHIS2 and return success status and created UID."""
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


def save_created_units(created_units, output_path):
    """Save created org units to an Excel file in the specified format."""
    if not created_units:
        return

    output_df = pd.DataFrame(created_units)
    output_df = output_df[[
        "Name",
        "UID",
        "Code",
        "Parent UID",
        "Short name",
        "Description",
        "Opening date"
    ]]
    output_df.to_excel(output_path, index=False)
    print(f"📂 Created units saved to {output_path}")


def main():
    file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "ca_to_create_sample.csv"))
    
    if not file_path:
        file_path = input("Enter the CA creation file path (default: ../data/ca_to_create.xlsx): ").strip()

    df = read_excel_or_delimited(file_path)

    # Resolve required columns (only Parent UID and Name)
    parent_uid_col = resolve_column_name(df, ["parent_uid", "parent uid", "parent_id", "parent id"])
    orgunit_name_col = resolve_column_name(df, ["name", "orgunit_name", "org_unit_name", "ca_name", "ca"])

    # Resolve optional columns
    uid_col = resolve_column_name(df, ["uid", "id", "orgunit_uid", "ca_uid"])
    code_col = resolve_column_name(df, ["code", "org_code", "ca_code"])
    short_name_col = resolve_column_name(df, ["short_name", "shortname", "short name"])
    description_col = resolve_column_name(df, ["description", "desc"])
    opening_date_col = resolve_column_name(df, ["opening_date", "openingdate", "opening date"])

    missing = []
    for col_name, label in [(parent_uid_col, "Parent UID"), (orgunit_name_col, "Name")]:
        if col_name is None:
            missing.append(label)

    if missing:
        raise ValueError(
            "Missing required columns. Expected: Parent UID, Name. "
            f"Detected missing: {missing}"
        )

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    created = 0
    failed = 0
    created_units = []

    for _, row in df.iterrows():
        parent_uid = str(row.get(parent_uid_col, "")).strip()
        org_name = str(row.get(orgunit_name_col, "")).strip()
        ca_uid = str(row.get(uid_col, "")).strip() if uid_col else ""
        ca_code = str(row.get(code_col, "")).strip() if code_col else ""
        short_name = str(row.get(short_name_col, "")).strip() if short_name_col else ""
        description = str(row.get(description_col, "")).strip() if description_col else ""
        opening_date = str(row.get(opening_date_col, "")).strip() if opening_date_col else ""

        if not parent_uid or not org_name:
            print(f"Skipping incomplete row: parent_uid={parent_uid!r}, org_name={org_name!r}")
            continue

        # Fetch parent org unit to determine level
        parent_org_unit = get_parent_org_unit(session, parent_uid)
        if not parent_org_unit:
            print(f"❌ Failed to fetch parent org unit {parent_uid} for {org_name}")
            failed += 1
            continue

        parent_level = parent_org_unit.get("level")
        uid_info = f" with UID {ca_uid}" if ca_uid else " (DHIS2 will generate UID)"
        print(f"Creating CA: {org_name} under parent ({parent_uid}) at level {int(parent_level) + 1}{uid_info}")
        
        payload = build_payload(org_name, parent_uid, ca_uid=ca_uid, ca_code=ca_code, short_name=short_name, description=description, opening_date=opening_date, parent_level=parent_level)
        success, created_id, message = create_org_unit(session, payload)

        if success:
            created += 1
            print(f"✅ Created: {org_name} | UID: {created_id}")
            created_units.append({
                "Name": org_name,
                "UID": created_id,
                "Code": ca_code if ca_code else "",
                "Parent UID": parent_uid,
                "Short name": short_name if short_name else org_name[:50],
                "Description": description if description else "",
                "Opening date": opening_date if opening_date else "1970-01-01"
            })
        else:
            failed += 1
            print(f"❌ Failed: {org_name} | {message}")

    output_file = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "ca_created.xlsx"))
    save_created_units(created_units, output_file)

    print(f"\nSummary: created={created}, failed={failed}")


if __name__ == "__main__":
    main()
