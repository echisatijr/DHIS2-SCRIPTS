# DHIS2 Level 5 Org Units Fetcher

This Python script connects to a DHIS2 instance and retrieves all **Level 5 Organisation Units** (typically **Catchment Areas**) under a specified **Level 3 Organisation Unit** (usually a **District**). The results are saved in an Excel file.

## Features

- Authenticates to DHIS2 using your credentials.
- Locates a Level 3 org unit (e.g., `DistrictName-DHO`) by name.
- Recursively retrieves all Level 5 org units under the selected district.
- Outputs the results to an Excel file using `pandas`.

## Requirements

- Python 3.x
- Required Python packages:
  - `requests`
  - `pandas`
  - `openpyxl`

Install dependencies using:

```bash
pip install requests pandas openpyxl
