# DHIS2 Bulk User Creation Script

This script automates the process of creating user accounts on a DHIS2 instance by reading user details from an Excel spreadsheet. It ensures that usernames are unique, assigns appropriate roles and organizational units, and reports the result of each account creation attempt.

## 📋 Features

- Generates unique usernames.
- Generates secure passwords based on the current year.
- Retrieves organization unit IDs at level 5.
- Retrieves user group IDs.
- Creates users via the DHIS2 API.
- Supports email, phone number, user roles, and user groups.
- Reads user details from an Excel spreadsheet.

## 🔧 Prerequisites

- Python 3.x
- DHIS2 credentials with user management permissions
- Required Python modules:
  - `requests`
  - `getpass`
  - `pandas`
  - `openpyxl` (for reading `.xlsx` files)
- Internet access to reach your DHIS2 server

Install dependencies using pip:

```bash
pip install requests pandas openpyxl
