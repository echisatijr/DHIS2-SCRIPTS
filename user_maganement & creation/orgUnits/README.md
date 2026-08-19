# CA Pulling

This script fetches all DHIS2 organisation units at catchment-area level and saves them to an Excel file for later use in user creation.

## What it does

The script:

1. asks for the district name
2. converts it to a district-level name such as `Balaka-DHO`
3. finds the matching level 3 organisation unit in DHIS2
4. recursively fetches all child organisation units under that district
5. keeps only level 5 units, which are the catchment areas
6. saves the result as an Excel file in the data folder

## Why this matters

The user creation process needs a list of catchment areas and their IDs so that new users can be assigned to the correct location.

## Expected input

The script expects the district name only, entered manually in the terminal.

Example:

```text
Write your district name: Balaka
```

## Expected output file

The output is saved as:

```text
../data/{district}_CA.xlsx
```

For example:

```text
../data/Balaka_CA.xlsx
```

## Expected output columns

```text
name,id,level,parent_name,parent_id
```

Example:

```text
name,id,level,parent_name,parent_id
Guzani CA (Tongozala Health Centre),tv21Cm2Q9EP,5,Tongozala Health Centre,abcd1234
January CA (Chioshya Health Centre),Qk36Nb1QV64,5,Chioshya Health Centre,efgh5678
```

## Notes

- The script reads data from the DHIS2 organisationUnits API.
- It saves only level 5 org units, which represent catchment areas.
- This file is later used as the CA reference file by the user creation script.
