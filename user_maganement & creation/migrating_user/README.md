# Migrating User

This script copies users from one DHIS2 instance to another.

## What it does

The script:

1. reads usernames from an Excel file
2. checks whether each username already exists in the target DHIS2 instance
3. fetches the user record from the source DHIS2 instance
4. creates a new user in the target instance
5. assigns the same roles, organisation units, and default user groups
6. generates a new password automatically for the target instance
7. prints a final migration summary

## Why this matters

This is useful when a user list must be moved from a source DHIS2 environment to a target environment, such as from staging to production or from one server to another.

## Expected input file

The script expects an Excel file located at:

```text
../user_data/usernames.xlsx
```

## Expected input column

```text
username
```

Example:

```text
username
agathazidana
achidya
```

## Expected output

The script does not create a separate Excel report. It prints progress and a final summary in the terminal.

Example:

```text
✅ SUCCESS: agathazidana created
⚠️ Already exists: achidya
========================================
🎯 MIGRATION COMPLETED
========================================
✅ Migrated: 12
⚠️ Skipped: 3
❌ Failed: 1
```

## Notes

- The script uses a source base URL and a target base URL.
- Default user groups are assigned during migration.
- A password is generated automatically for each migrated user.
- The migration uses the source user’s roles and organisation-unit assignments as a template.
