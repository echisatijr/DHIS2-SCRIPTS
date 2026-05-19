# DHIS2 User Creation Script

## Overview
This script automates the bulk creation of users in DHIS2 (District Health Information Software System). It reads user data from Excel files, matches organization units using fuzzy matching, generates secure credentials, and creates users in the DHIS2 system via API calls.

**Note:** This script is actively being developed and optimized. Updates and improvements will be made as we discover optimization opportunities.

## Features
- **Bulk User Creation**: Create multiple users in DHIS2 from Excel data
- **Fuzzy Matching**: Intelligently matches organization units to handle slight variations in naming
- **Secure Password Generation**: Creates unique, secure passwords with format: `FirstLetter` + `LastName` + `@Year` + `RandomDigits`
- **Automatic Username Generation**: Generates unique usernames based on user names, avoiding duplicates
- **Organization Unit Assignment**: Automatically assigns users to matched organization units
- **Role Assignment**: Assigns default user roles (customizable per user)
- **Data Export**: Saves created user credentials to Excel for distribution
- **Error Handling**: Logs errors and skips users that fail creation
- **User Verification**: Checks if usernames already exist before creation

## Prerequisites
### Required Python Packages
```bash
pip install pandas requests fuzzywuzzy python-Levenshtein openpyxl
```

### Required Inputs
1. **DHIS2 Credentials**: Username and password (prompted at runtime)
2. **District Name**: The name of the district (prompted at runtime)
3. **User Data File**: Excel file with user information located at `user_maganement & creation\Creating_User\{district}_users.xlsx`
4. **Organization Unit File**: Excel file with organization units located at `user_maganement & creation\CA_Pulling\{district}_CA.xlsx`

## Input File Format

### User Data File (e.g., `{district}_users.xlsx`)
Required columns:
- `User Full Name`: Full name of the user (e.g., "John Doe Smith")
- `orgUnitName`: Organization unit name (will be matched to actual org units)
- `Email` (optional): User email address
- `Phone Number` (optional): User phone number
- `userRole` (optional): DHIS2 user role ID (uses default if not provided)
- `userGroup` (optional): DHIS2 user group ID

### Organization Unit File (e.g., `{district}_CA.xlsx`)
Required columns:
- `name`: Name of the organization unit
- `id`: DHIS2 organization unit ID
- `parent_name`: Name of the parent organization unit (facility)

## Configuration
### DHIS2 Connection
```python
DHIS2_BASE_URL = "https://ccdev.org/chistest"
```
Update this to your DHIS2 instance URL.

### Default Values
```python
DEFAULT_USER_ROLE = "K7DkWdiGSbA"  # Community Tracker
DEFAULT_USER_GROUP = None  # Set a default group ID if needed
```
Modify these constants if you need different defaults.

## Usage
```bash
python user_creation.py
```

The script will prompt you for:
1. **Username**: DHIS2 system username
2. **Password**: DHIS2 system password
3. **District Name**: Name of the district to process

## Output
### Console Output
- ✅ Success messages for each created user with password
- ❌ Failure messages if user creation fails
- ⚠️ Warnings for organizational units with low matching scores

### Excel File (`created_users.xlsx`)
Contains the following columns for all successfully created users:
- Facility
- Full Name
- Username
- Password
- Assigned Org Unit
- Phone Number
- Email

**Important**: Save this file securely as it contains user passwords.

## How It Works

1. **Load Data**: Reads user and organization unit data from Excel files
2. **Fuzzy Matching**: Matches user-provided org unit names to actual org units (minimum 80% match score)
3. **Generate Credentials**: 
   - Creates unique usernames
   - Generates secure passwords
4. **Assign Organization Units**: Links users to matched org units and retrieves their IDs
5. **Create Users in DHIS2**: Sends user creation requests to DHIS2 API
6. **Export Results**: Saves successful user creations to Excel file

## Function Reference

| Function | Purpose |
|----------|---------|
| `load_data()` | Load user and org unit data from Excel files |
| `username_exists()` | Check if a username already exists in DHIS2 |
| `generate_username()` | Generate a unique username based on full name |
| `generate_password()` | Generate a secure password |
| `find_best_match()` | Find the best matching org unit using fuzzy matching |
| `assign_org_units()` | Assign org units to users and generate credentials |
| `create_user()` | Send user creation request to DHIS2 API |
| `send_users_to_dhis2()` | Process all users and export results to Excel |

## Error Handling
The script logs errors for:
- Failed DHIS2 API requests
- Organization units with no suitable matches (< 80% match score)
- Invalid JSON responses from DHIS2
- Users that fail to create

All errors are logged with timestamps using Python's logging module.

## Notes
- The fuzzy matching score threshold is set to 80%. Adjust in `find_best_match()` if needed
- Username generation supports up to 3 fallback candidates before adding numeric suffixes
- Passwords are randomly generated each time the script runs
- The script skips rows where no organization unit match is found
- Uses DHIS2 API v39+ endpoint format (may require adjustment for older versions)

## Future Optimizations
This script will be continuously updated with:
- Performance improvements
- Enhanced error handling
- Additional validation features
- Support for bulk updates and user deactivation
- Configuration file support (to avoid hardcoding URLs and defaults)
- Batch processing optimizations
- Logging improvements

## Troubleshooting
- **"No suitable match found"**: Org unit name doesn't match closely enough. Verify spelling in input files
- **"Failed to check username existence"**: Check DHIS2 credentials and server connectivity
- **"DHIS2 response is not valid JSON"**: May indicate server error. Check DHIS2 system status
- **Empty output file**: No users were successfully created. Check error logs for details
