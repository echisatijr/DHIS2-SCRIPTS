#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ITN Distribution Planning Tool

This module processes household data to generate a logistics plan for Insecticide-Treated Nets (ITN) distribution.
It calculates required nets per household, summarizes needs per health catchment area, and produces allocation reports.

Key Features:
- Processes recent CSV data file automatically
- Calculates nets required based on household size
- Generates per-catchment area allocation sheets
- Summarizes total needs including bale calculations

Output:
- Timestamped Excel file with:
  - Summary sheet with aggregated statistics
  - Detailed allocation per Health Surveillance Assistant (HSA)
"""

from pathlib import Path
import re
from datetime import datetime
import typing
import pandas as pd
import pydash as py_
import math

def process_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and processes raw household data for ITN allocation calculations.

    Args:
        data: Raw input DataFrame containing household registration data

    Returns:
        Processed DataFrame with cleaned data and calculated LLIN requirements

    Processing Steps:
        1. Column selection and validation
        2. Missing data handling
        3. LLIN requirement calculation based on household size
    """
    # Define essential columns with fallback for missing data
    relevant_columns = [
        'Organisation unit name', 'Created by', 'Household head name',
        'Household head identifier', 'Household System ID', 'Village Name',
        'ITN-HH-Registration - Number of household members',
        'LLIN-HR - Total Number of LLINs allocated or required (both households and schools)',
        'ITN-HH-Registration - Registration type'
    ]

    # Filter to available columns
    existing_columns = [col for col in relevant_columns if col in data.columns]
    data = data[existing_columns]

    # Handle missing values with type-appropriate defaults
    fill_values = {
        'Household System ID': "",
        'ITN-HH-Registration - Registration type': "",
        'Household head name': "",
        'Household head identifier': "",
        'Village Name': "",
        'ITN-HH-Registration - Number of household members': 0,
        'LLIN-HR - Total Number of LLINs allocated or required (both households and schools)': 0
    }
    data.fillna(fill_values, inplace=True)

    def calculate_llins_required(num_members: int) -> int:
        """
        Determines ITN allocation based on WHO recommendations for household size.
        
        Allocation Logic:
        - 1 net for 1-2 people
        - 2 nets for 3-4 people
        - 3 nets for 5-6 people
        - 4 nets for 7+ people
        """
        if num_members <= 0:
            return 0
        elif num_members <= 2:
            return 1
        elif num_members <= 4:
            return 2
        elif num_members <= 6:
            return 3
        else:  # 7+ members
            return 4

    # Apply allocation calculation
    data['LLIN-HR - Total Number of LLINs allocated or required (both households and schools)'] = \
        data['ITN-HH-Registration - Number of household members'].apply(calculate_llins_required)

    return data

if __name__ == "__main__":
    # Configure file paths
    script_dir = Path(__file__).parent
    input_file = py_.max_by(collection=script_dir.glob("*.csv"), 
                           iteratee=lambda x: x.stat().st_mtime_ns)

    if not input_file:
        raise FileNotFoundError("No CSV files found in the script directory.")

    # Load and process data
    raw_data = pd.read_csv(input_file)
    processed_data = process_data(raw_data)

    # Group data by HSA (using 'Created by' field)
    hsa_groups = processed_data.groupby('Created by')
    report_time = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = script_dir / f'{input_file.stem}_processed_{report_time}.xlsx'

    # Prepare reporting structures
    summary_reports = []
    detailed_reports = []

    with pd.ExcelWriter(output_path) as excel_writer:
        # Process each HSA group
        for hsa_group in hsa_groups.groups:
            group_data = hsa_groups.get_group(hsa_group)
            
            # Clean and format group data
            group_clean = (
                group_data.rename(columns={"Organisation unit name": "Catchment Area"})
                .drop(columns=['Village Name', 'Created by'])
                .sort_values('Household System ID')
                .drop_duplicates('Household System ID', keep='last')
            )

            # Extract HSA details
            hsa_name = " ".join(
                reversed(re.sub(r"\(\w+\)", "", hsa_group).strip().split(", "))
            ).strip()
            catchment_area = ",".join(group_clean['Catchment Area'].unique())

            # Calculate statistics
            stats = {
                'households_total': group_clean['Household System ID'].nunique(),
                'population_total': group_clean['ITN-HH-Registration - Number of household members'].sum(),
                'unallocated_households': group_clean['ITN-HH-Registration - Number of household members']
                    .value_counts().get(0, 0),
                'nets_required': group_clean['LLIN-HR - Total Number of LLINs allocated or required (both households and schools)'].sum()
            }

            # Calculate bale requirements (50 nets/bale)
            nets_per_bale = 50
            bales = stats['nets_required'] // nets_per_bale
            loose_nets = stats['nets_required'] % nets_per_bale

            # Compile summary
            summary = pd.DataFrame([{
                'Catchment Area': catchment_area,
                'Assigned HSA': hsa_name,
                'Number of households': stats['households_total'],
                'Total household members': stats['population_total'],
                'Unallocated households': stats['unallocated_households'],
                'Total ITNs required': stats['nets_required'],
                'Total ITNs allocated': stats['nets_required'],  # Required = Allocated
                'Number of bales': bales,
                'Loose nets': loose_nets
            }])
            summary_reports.append(summary)

            # Store detailed report
            sheet_name = re.sub(r"[\[\]:*?/\]]", "", f"{hsa_name} - {catchment_area}")[:31]
            detailed_reports.append({
                'sheet_name': sheet_name,
                'data': group_clean
            })

        # Write all reports to Excel
        pd.concat(summary_reports).sort_values('Assigned HSA').to_excel(
            excel_writer, sheet_name="Summary", index=False)
        
        for report in detailed_reports:
            report['data'].to_excel(
                excel_writer, sheet_name=report['sheet_name'], index=False)

    print(f"Report generation complete: {output_path}")