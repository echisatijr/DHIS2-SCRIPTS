# DHIS2 User Management Scripts

This folder contains the scripts used to manage DHIS2 users and organisation units in a district workflow.

## Overview

The workflow is split into these main tasks:

- CA Pulling: fetches all catchment-area level 5 organisation units from DHIS2 and saves them to an Excel file.
- Creating User: reads district user data, matches it to CA/facility units, creates DHIS2 users, and exports the created-user report.
- Deleting User: deletes a fixed list of DHIS2 user IDs.
- Migrating User: copies users from a source DHIS2 instance to a target DHIS2 instance using a list of usernames.

## Folder structure

- ca_pulling/
  - Downloads catchment areas from DHIS2.
- creating_user/
  - Creates new DHIS2 users from a district file.
- deleting_user/
  - Removes selected user IDs from DHIS2.
- migrating_user/
  - Copies users from one DHIS2 instance to another.
- data/
  - Stores input and output Excel files for district work.

## Common requirements

Before running any script, make sure you have:

- a valid DHIS2 server URL
- valid DHIS2 credentials
- a .env file in the parent folder containing values such as:

```env
DHIS2_BASE_URL_TEST=https://your-server/dhis
DHIS2_BASE_URL_MAIN=https://target-server/dhis
DHIS2_USERNAME=your_username
DHIS2_PASSWORD=your_password
```

- Python dependencies installed in the virtual environment, including:
  - pandas
  - requests
  - fuzzywuzzy
  - openpyxl

## Typical data flow

1. Pull CA data from DHIS2 for a district.
2. Prepare the user input Excel file for that district.
3. Run the user creation script.
4. Review the created_users output file.
5. Use migration or deletion scripts only when needed.

## Common input/output conventions

The scripts use district-based Excel files stored in the data folder. Typical naming:

- Balaka_users.xlsx
- Balaka_CA.xlsx
- Balaka_created_users.xlsx

This helps keep each district’s user creation records separate.

---

## Scripts summary

### ca_pulling
Purpose: Fetch all level 5 catchment areas under the district.

Expected input:

```text
District name is entered manually in the terminal.
```

Expected output columns:

```text
name,id,level,parent_name,parent_id
```

### creating_user
Purpose: Create DHIS2 users for a district and save a final created-user report.

Expected input columns:

```text
User Full Name,orgUnitName,Facility,Phone Number,Email,userRole,userGroup
```

Expected output columns:

```text
Catchment Area,CA UID,CHW Fullname,Phone Number,Facility Name,Username,Password
```

### deleting_user
Purpose: Delete a fixed list of user IDs from DHIS2.

Expected input:

```text
A Python list of DHIS2 user IDs inside the script.
```

Expected output:

```text
Console result: Deleted / Failed
```

### migrating_user
Purpose: Copy selected users from a source DHIS2 instance to a target DHIS2 instance.

Expected input column:

```text
username
```

Expected output:

```text
Console summary: Migrated, Skipped, Failed
```

---

## Notes

- Some scripts prompt for the district name interactively.
- Some scripts depend on names matching DHIS2 data exactly.
- The user creation script uses fuzzy matching for CA and facility names, so minor naming differences can still be resolved.
- Always confirm the district file names before running a script.
