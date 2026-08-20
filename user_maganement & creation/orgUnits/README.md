# Organisation Unit Management (OrgUnits)

This folder contains scripts for managing DHIS2 organisation units at catchment-area level: pulling, creating, and migrating across instances.

---

## 1. CA Pulling (`ca_pulling.py`)

Fetches all DHIS2 organisation units at catchment-area level and saves them to an Excel file for later use in user creation.

### What it does

1. asks for the district name
2. converts it to a district-level name such as `Balaka-DHO`
3. finds the matching level 3 organisation unit in DHIS2
4. recursively fetches all child organisation units under that district
5. keeps only level 5 units, which are the catchment areas
6. saves the result as an Excel file in the data folder

### Why this matters

The user creation process needs a list of catchment areas and their IDs so that new users can be assigned to the correct location.

### Expected input

The script expects the district name only, entered manually in the terminal.

```text
Write your district name: Balaka
```

### Expected output file

```text
../data/{district}_CA.xlsx
```

Example: `../data/Balaka_CA.xlsx`

### Expected output columns

```text
name,id,level,parent_name,parent_id
```

Example:

```text
name,id,level,parent_name,parent_id
Guzani CA (Tongozala Health Centre),tv21Cm2Q9EP,5,Tongozala Health Centre,abcd1234
January CA (Chioshya Health Centre),Qk36Nb1QV64,5,Chioshya Health Centre,efgh5678
```

### Notes

- The script reads data from the DHIS2 organisationUnits API
- It saves only level 5 org units, which represent catchment areas
- This file is later used as the CA reference file by the user creation script

---

## 2. CA Creation (`ca_creation.py`)

Bulk creates DHIS2 catchment-area organisation units from an Excel or CSV input file with flexible parent and metadata options.

### What it does

1. reads an input file (Excel or CSV) with catchment-area details
2. for each row, creates an organisation unit in DHIS2 with:
   - custom UID (if provided) or DHIS2 auto-generated UID
   - metadata: code, short name, description, opening date
3. exports created units to an Excel file with all details

### Why this matters

Batch creation of catchment areas is faster and more reliable than manual entry, especially when migrating data between instances or setting up new districts.

### Expected input file

**Location**: `../data/ca_to_create.xlsx` (or any CSV/Excel file)

**Required columns**:
- `Name` - The name of the catchment area
- `Parent UID` - The UID of the parent organisation unit (facility/health center)

**Optional columns**:
- `UID` - Custom UID (if empty, DHIS2 will auto-generate)
- `Code` - Organisation unit code
- `Short name` - Short name (defaults to Name if empty)
- `Description` - Description
- `Opening date` - Opening date (defaults to "1970-01-01" if empty)

### Expected input format

```text
Name,Parent UID,UID,Code,Short name,Description,Opening date
Adamu CA,R96XZz9y9Ji,CDqeCZzOjec,,Adamu CA,,1970-01-01
Isa CA,R96XZz9y9Ji,ouIKbti9czO,,Isa CA,,1970-01-01
New CA,R96XZz9y9Ji,,NEW123,New CA,New catchment area,2025-01-01
```

**Note**: The organization level is automatically derived from the parent org unit level (parent level + 1).

### How to run

```bash
./myvenv/bin/python orgUnits/ca_creation.py
```

Then enter the file path when prompted (default: `../data/ca_to_create.xlsx`)

### Expected output file

```text
../data/ca_created.xlsx
```

### Expected output columns

```text
Name,UID,Code,Parent UID,Short name,Description,Opening date
```

Example:

```text
Name,UID,Code,Parent UID,Short name,Description,Opening date
Adamu CA,CDqeCZzOjec,,R96XZz9y9Ji,Adamu CA,,1970-01-01
Isa CA,ouIKbti9czO,,R96XZz9y9Ji,Isa CA,,1970-01-01
New CA,AbCdEfG1234,NEW123,R96XZz9y9Ji,New CA,New catchment area,2025-01-01
```

### Notes

- The script automatically detects Excel (.xlsx) and CSV files
- If a UID is provided, it will be used; otherwise DHIS2 generates one automatically
- All optional fields have sensible defaults
- The output file includes the actual UIDs assigned by DHIS2

---

## 3. CA Migration (`ca_migration.py`)

Migrates organisation units from a source DHIS2 instance to a destination instance based on UIDs, preserving all metadata.

### What it does

1. reads UIDs from an input file
2. fetches organisation unit details from source DHIS2 instance (by UID)
3. creates the same organisation units in destination DHIS2 instance with:
   - preserved UIDs (so references remain valid)
   - all original metadata (code, short name, description, opening date)
4. exports created units to an Excel file with migration status

### Why this matters

Migrating organisation units between instances (e.g., test to production) is complex because:
- UIDs must be preserved for data continuity
- Metadata must match exactly
- Parent org units must exist in destination
- The migration must be traceable and reversible

### Expected input file

**Location**: `../data/ca_to_migrate.xlsx` (or any CSV/Excel file)

**Required columns**:
- `UID` (or `id`, `orgunit_uid`, `ca_uid`) - The UID of the organisation unit to migrate from source instance

**Optional columns**:
- `Destination Parent UID` (or `parent_uid`, etc.) - Override the parent org unit in destination (if empty, uses source parent)
- All other columns are ignored

### Expected input format

```text
UID
CDqeCZzOjec
ouIKbti9czO
AbCdEfG1234
```

Or with optional parent override:

```text
UID,Destination Parent UID
CDqeCZzOjec,
ouIKbti9czO,R96XZz9y9Ji
AbCdEfG1234,
```

**Note**: All metadata (name, code, short name, description, opening date) is fetched from the source DHIS2 instance and preserved in the destination.

### How to run

```bash
./myvenv/bin/python orgUnits/ca_migration.py
```

Then enter:
1. The source DHIS2 base URL (e.g., `https://source.org/dhis`)
2. The destination DHIS2 base URL (e.g., `https://destination.org/dhis`)
3. Source DHIS2 credentials (username/password)
4. Destination DHIS2 credentials (username/password)
5. The input file path (default: `../data/ca_to_migrate.xlsx`)

### Expected output file

```text
../data/ca_migrated.xlsx
```

### Expected output columns

```text
Name,UID,Status,Source Instance,Destination Instance,Code,Parent UID,Short name,Description,Opening date
```

Example:

```text
Name,UID,Status,Source Instance,Destination Instance,Code,Parent UID,Short name,Description,Opening date
Adamu CA,CDqeCZzOjec,✅ Success,https://source.org/dhis,https://dest.org/dhis,,R96XZz9y9Ji,Adamu CA,,1970-01-01
Isa CA,ouIKbti9czO,❌ Failed,https://source.org/dhis,https://dest.org/dhis,,R96XZz9y9Ji,Isa CA,Parent not found,1970-01-01
```

### Notes

- The script requires valid credentials for both source and destination instances (from .env or interactive input)
- Migration is logged so you can track which org units succeeded/failed
- UIDs are preserved to maintain data relationships
- If a destination parent UID is not provided, the source parent UID is used
- Failed migrations show the error reason so you can debug and retry

---

## 4. CA Update (`ca_update.py`)

Updates existing DHIS2 catchment-area organisation unit details based on UIDs. Only provided fields are updated; others are preserved.

### What it does

1. reads an input file (Excel or CSV) with UID and optional fields to update
2. for each row with a UID, fetches the org unit from DHIS2
3. updates only the fields that are provided (non-empty)
4. preserves all other fields unchanged
5. exports update results to an Excel file with status and what was updated

### Why this matters

Batch updating org unit details (fixing names, codes, descriptions, dates) is much faster than manual entry, and you only need to specify fields that changed.

### Expected input file

**Location**: `../data/ca_to_update.xlsx` (or any CSV/Excel file)

**Required columns**:
- `UID` (or `id`, `orgunit_uid`, `ca_uid`) - The UID of the organisation unit to update

**Optional columns**:
- `Name` - New name (if empty, not updated)
- `Code` - New code (if empty, not updated)
- `Parent UID` - New parent org unit (if empty, not updated)
- `Short name` - New short name (if empty, not updated)
- `Description` - New description (if empty, not updated)
- `Opening date` - New opening date (if empty, not updated)

### Expected input format

```text
Name,UID,Code,Parent UID,Short name,Description,Opening date
Lingwang'wa 2 CA,kkx7J2I37vq,,,,Updated catchment area,1970-01-01
Updated CA,ouIKbti9czO,NEW123,,,New description,
Another CA,AbCdEfG1234,,R96XZz9y9Ji,Another CA Updated,,
```

**Note**: Only non-empty cells will be updated. Empty cells are ignored and existing values are preserved.

### How to run

```bash
./myvenv/bin/python orgUnits/ca_update.py
```

Then enter:
1. The input file path (default: `../data/ca_to_update.xlsx`)
2. DHIS2 credentials (username/password if not in .env)

### Expected output file

```text
../data/ca_updated.xlsx
```

### Expected output columns

```text
Name,UID,Status,Code,Parent UID,Short name,Description,Opening date,Updates Applied
```

Example:

```text
Name,UID,Status,Code,Parent UID,Short name,Description,Opening date,Updates Applied
Lingwang'wa 2 CA,kkx7J2I37vq,✅ Success,,,,,1970-01-01,Description
Updated CA,ouIKbti9czO,✅ Success,NEW123,,,,, Code, Description
Another CA Updated,AbCdEfG1234,✅ Success,,R96XZz9y9Ji,Another CA Updated,,, Parent UID, Short name
```

### Notes

- Only fields with values in the input file are updated
- All other fields are preserved unchanged
- Date formats are automatically normalized to ISO format (YYYY-MM-DD)
- Empty cells are skipped, so you can update just the fields you need
- Failed updates show the error reason for debugging
- The "Updates Applied" column shows which fields were actually changed

