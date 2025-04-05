# ITN Distribution Planning System by Health Facility

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Comprehensive solution for managing mosquito net distribution campaigns across health facilities.

## Features

- **Automated Data Processing**
  - Health facility extraction from organization names
  - Household-level net allocation calculations
  - Data validation and cleaning

- **Detailed Reporting**
  - Facility-specific allocation sheets
  - National summary with totals
  - Bale packaging calculations (50 nets/bale)
  - Excel-safe sheet naming

- **Data Quality**
  - Missing value handling
  - Invalid entry detection
  - Consistency checks

## Input Requirements

### CSV File Format
Must contain these columns:

| Column Name                                    | Description                          |
|------------------------------------------------|--------------------------------------|
| Organisation unit name                         | Health facility parent organization |
| Household System ID                            | Unique household identifier          |
| ITN-HH-Registration - Number of household members | Family size                        |

### Example Input Structure
```csv
Organisation unit name,Household System ID,...
Malaria Zone (Central Hospital),HH_12345,...
Rural District (Clinic A),HH_67890,...