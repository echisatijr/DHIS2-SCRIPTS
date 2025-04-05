#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ITN Distribution Planner by Health Facility

This script processes household data to generate a distribution plan for Insecticide-Treated Nets (ITNs),
prioritizing health facility-level organization. It features automated data cleaning, requirement calculations,
and Excel report generation with summary-first presentation.

Key Features:
- Health facility extraction from organizational names
- WHO-compliant net allocation calculations
- Multi-sheet Excel output with summary first
- Automated file handling with timestamping
"""

import re
from pathlib import Path
from datetime import datetime
import pandas as pd
import pydash as py_

# Constants
NETS_PER_BALE = 50
SUMMARY_SHEET_NAME = "00_Summary"  # Ensures first position via naming
REQUIRED_COLUMNS = [
    'Organisation unit name', 
    'Household System ID',
    'ITN-HH-Registration - Number of household members'
]

def process_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize raw household data
    
    Args:
        raw_df: Input DataFrame from CSV file
        
    Returns:
        Processed DataFrame with calculated fields and cleaned values
    
    Processing Steps:
        1. Column validation and selection
        2. Health facility extraction
        3. Missing value handling
        4. Net requirement calculations
    """
    # Validate required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in raw_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

    # Extract health facility from organizational name
    raw_df['Health Facility'] = (
        raw_df['Organisation unit name']
        .str.extract(r'\((.*?)\)', expand=False)
        .fillna("Unspecified Facility")
        .str.strip()
    )

    # Standardize missing values
    processed_df = raw_df.fillna({
        'Household System ID': 'MISSING_ID',
        'ITN-HH-Registration - Number of household members': 0,
        'Village Name': 'Unspecified'
    }).copy()

    # Calculate net requirements using WHO standards
    def calculate_nets(household_size: int) -> int:
        """Determine ITN allocation based on household size brackets"""
        if household_size <= 0: return 0
        if household_size <= 2: return 1
        if household_size <= 4: return 2
        if household_size <= 6: return 3
        return 4  # 7+ members

    processed_df['Calculated ITNs'] = (
        processed_df['ITN-HH-Registration - Number of household members']
        .apply(calculate_nets))
    
    return processed_df

def generate_report(processed_df: pd.DataFrame, output_path: Path) -> None:
    """
    Generate structured Excel report with summary-first organization
    
    Args:
        processed_df: Cleaned DataFrame from process_data
        output_path: Destination path for Excel report
    """
    # Prepare data containers
    summaries = []
    facility_details = []

    # Process each health facility
    for facility_name, facility_data in processed_df.groupby('Health Facility'):
        # Clean sheet name for Excel compatibility
        sheet_name = re.sub(r"[\[\]\\/*?]", "_", facility_name)[:30].strip()
        
        # Calculate facility statistics
        stats = {
            'households': facility_data['Household System ID'].nunique(),
            'population': facility_data['ITN-HH-Registration - Number of household members'].sum(),
            'unallocated': (facility_data['ITN-HH-Registration - Number of household members'] <= 0).sum(),
            'nets_required': facility_data['Calculated ITNs'].sum()
        }
        
        # Calculate bale packaging
        bales, loose_nets = divmod(stats['nets_required'], NETS_PER_BALE)
        
        # Store summary data
        summaries.append({
            'Health Facility': facility_name,
            'Households': stats['households'],
            'Total Population': stats['population'],
            'Unallocated Households': stats['unallocated'],
            'Total ITNs Required': stats['nets_required'],
            'Bales Required': bales,
            'Loose Nets': loose_nets
        })
        
        # Store detailed data for facility sheet
        facility_details.append({
            'sheet_name': sheet_name,
            'data': facility_data.drop(columns=['Health Facility'])
        })

    # Create summary dataframe with totals
    summary_df = pd.DataFrame(summaries)
    totals_row = pd.DataFrame([{
        'Health Facility': 'NATIONAL TOTAL',
        'Households': summary_df['Households'].sum(),
        'Total Population': summary_df['Total Population'].sum(),
        'Unallocated Households': summary_df['Unallocated Households'].sum(),
        'Total ITNs Required': summary_df['Total ITNs Required'].sum(),
        'Bales Required': summary_df['Total ITNs Required'].sum() // NETS_PER_BALE,
        'Loose Nets': summary_df['Total ITNs Required'].sum() % NETS_PER_BALE
    }])
    full_summary = pd.concat([summary_df, totals_row], ignore_index=True)

    # Write to Excel with summary first
    with pd.ExcelWriter(output_path) as writer:
        # Write summary sheet (first position)
        full_summary.sort_values('Health Facility').to_excel(
            writer, 
            sheet_name=SUMMARY_SHEET_NAME, 
            index=False
        )
        
        # Write facility-specific sheets
        for detail in sorted(facility_details, key=lambda x: x['sheet_name']):
            detail['data'].to_excel(
                writer,
                sheet_name=detail['sheet_name'],
                index=False
            )

if __name__ == "__main__":
    # Configure file paths
    script_dir = Path(__file__).parent
    try:
        # Find most recent CSV
        input_file = py_.max_by(
            script_dir.glob("*.csv"),
            lambda f: f.stat().st_mtime
        )
        if not input_file:
            raise FileNotFoundError("No CSV files found in directory")
        
        # Generate output filename
        output_file = script_dir / f"ITN_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        # Execute processing pipeline
        raw_data = pd.read_csv(input_file)
        cleaned_data = process_data(raw_data)
        generate_report(cleaned_data, output_file)
        
        print(f"Successfully generated report: {output_file}")
    
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        exit(1)
