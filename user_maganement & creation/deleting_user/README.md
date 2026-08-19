# Deleting User

This script deletes a fixed list of DHIS2 users by UID.

## What it does

The script:

1. reads a list of user IDs defined inside the script
2. sends a DELETE request to the DHIS2 users API for each UID
3. prints whether each deletion was successful or failed

## Expected input

This script does not read a file. It uses a Python list of user IDs directly inside the script.

Example:

```python
uids = [
    "OlMAXtz2XuW",
    "XU8LpU0sQbM",
    "xs5dghN3UsY"
]
```

## Expected output

The output is written to the console.

Example:

```text
✅ Deleted: OlMAXtz2XuW
❌ Failed: XU8LpU0sQbM | 404 | ...
```

## Purpose

Use this script when you need to remove specific users from DHIS2 in bulk, especially when they are no longer active or need to be cleaned from a test or staging environment.

## Notes

- This is not a data-driven script.
- The IDs to delete are manually written in the script.
- Use it carefully because deletion is permanent.
