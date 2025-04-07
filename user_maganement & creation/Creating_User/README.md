# DHIS2 Bulk User Creation Script

This Python script streamlines the process of bulk user creation in a DHIS2 instance using input data from Excel files. It performs fuzzy matching for organization unit names, generates unique usernames and secure passwords, and assigns default roles and groups.

---

## Features

- Reads user and organization unit data from Excel files
- Uses fuzzy matching to map user entries to organization units
- Automatically generates unique usernames
- Generates passwords in the format: `FirstInitialLastName@Year`
- Assigns user roles and groups
- Interacts with the DHIS2 API to create users
- Saves created users and their credentials to a new Excel file

---

## Requirements

- Python 3.x
- Required Python modules:
  - `pandas`
  - `requests`
  - `openpyxl`
  - `fuzzywuzzy`

Install dependencies using pip:

```bash
pip install pandas requests openpyxl fuzzywuzzy
