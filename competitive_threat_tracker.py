#!/usr/bin/env python3
"""
Competitive Threat Tracker MVP
Cross-references portfolio holdings against fast-growing private companies,
then uses the Anthropic API to identify genuine competitive threats.
"""

# Import argparse to handle command-line arguments
import argparse

# Import json for reading and writing JSON files
import json

# Import csv for writing the threats output CSV
import csv

# Import os for file and directory path operations
import os

# Import sys for exiting the script on errors
import sys

# Import time for rate limiting between API calls
import time

# Import datetime to generate timestamps for reports
from datetime import datetime

# Import pathlib for cross-platform file path globbing
from pathlib import Path

# Import re for regular expression matching on CSV column names
import re

# Define tickers and patterns that should be excluded from analysis (ETFs, cash, currency, money markets)
EXCLUDED_TICKERS = {"Cash&Other", "JPY", "FGXXX"}
# Define keywords that identify ETFs and index funds by name (case-insensitive matching)
ETF_NAME_KEYWORDS = ["etf", "ishares", "invesco", "advisorshares", "spdr", "vanguard", "index fund"]


# Define a function to check if a holding is an ETF, cash, currency, or other non-operating entity
def is_excluded_holding(ticker, name=""):
    # Check if the ticker is in the explicit exclusion list
    if ticker in EXCLUDED_TICKERS:
        # Return True to exclude this holding
        return True
    # Check if the company name contains ETF-related keywords (case-insensitive)
    name_lower = name.lower()
    # Loop through each ETF keyword to check for a match
    for keyword in ETF_NAME_KEYWORDS:
        # Check if this keyword appears in the name
        if keyword in name_lower:
            # Return True to exclude this ETF
            return True
    # This holding is a real operating company, don't exclude it
    return False

# Try importing openpyxl for reading Excel files
try:
    # Import openpyxl to read .xlsx holdings files
    import openpyxl
# Catch the import error if openpyxl is not installed
except ImportError:
    # Print an error message telling the user how to install the dependency
    print("Error: openpyxl is required. Install with: pip install openpyxl")
    # Exit the script since we can't read Excel without openpyxl
    sys.exit(1)

# Try importing the Anthropic API client library
try:
    # Import the Anthropic class from the anthropic package
    from anthropic import Anthropic
# Catch the import error if anthropic is not installed
except ImportError:
    # Set Anthropic to None so we can check later if it's available
    Anthropic = None


# Define a function to parse and return command-line arguments
def parse_args():
    # Create an argument parser with a description of the script's purpose
    parser = argparse.ArgumentParser(
        description="Competitive Threat Tracker: Identify threats to portfolio holdings from private companies"
    )
    # Add a required argument for the path to the Excel holdings file
    parser.add_argument(
        "--holdings",
        required=True,
        help="Path to Excel file containing portfolio holdings",
    )
    # Add an optional argument for the directory containing private company CSV files
    parser.add_argument(
        "--csv-dir",
        default=None,
        help="Directory containing private company CSV files",
    )
    # Add an optional argument for the path to the competitive profiles JSON file
    parser.add_argument(
        "--profiles",
        default="holdings_competitive_profile.json",
        help="Path to the holdings competitive profile JSON file (default: holdings_competitive_profile.json)",
    )
    # Add an optional argument for the directory where output reports will be saved
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for output files (default: output/)",
    )
    # Add a flag that generates the competitive profile template and exits without analysis
    parser.add_argument(
        "--holdings-only",
        action="store_true",
        help="Only generate the competitive profile template JSON, then exit",
    )
    # Add a flag that shows API prompts without actually calling the API
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be sent to the API without making actual calls",
    )
    # Add an optional argument for the portfolio name used in the report header
    parser.add_argument(
        "--portfolio-name",
        default="Portfolio",
        help="Name of the portfolio for the report header (default: Portfolio)",
    )
    # Add a flag to send the results via email after analysis
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send the results via email after analysis completes",
    )
    # Add a flag for test mode (only emails ardal@militiainv.com)
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: only send email to ardal@militiainv.com",
    )
    # Add an optional argument for the path to the config.yaml file
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )
    # Parse the arguments the user provided on the command line
    args = parser.parse_args()
    # Return the parsed arguments object
    return args


# Define a function to detect the stock exchange market based on ticker suffix
def detect_market(ticker):
    # Strip whitespace from the ticker to avoid matching issues
    ticker = ticker.strip()
    # Check if the ticker ends with "JP" indicating a Japanese listing
    if ticker.endswith(" JP"):
        # Return "Japan" as the market
        return "Japan"
    # Check if the ticker ends with "FP" indicating a French listing
    elif ticker.endswith(" FP"):
        # Return "France" as the market
        return "France"
    # Check if the ticker ends with "MM" indicating a Mexican listing
    elif ticker.endswith(" MM"):
        # Return "Mexico" as the market
        return "Mexico"
    # If no recognized suffix, default to US-listed
    else:
        # Return "US" as the default market
        return "US"


# Define a function to read portfolio holdings from an Excel file
def read_holdings(filepath):
    # Check if the holdings file exists on disk
    if not os.path.exists(filepath):
        # Print an error message with the path that was not found
        print(f"Error: Holdings file not found: {filepath}")
        # Exit the script since we can't proceed without holdings data
        sys.exit(1)
    # Open the Excel workbook in read-only mode with cached data for efficiency
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    # Get the first (active) worksheet from the workbook
    ws = wb.active
    # Read all rows from the worksheet into a list of tuples
    rows = list(ws.iter_rows(values_only=True))
    # Close the workbook to free memory
    wb.close()
    # Check if the workbook had no data at all
    if not rows:
        # Print an error message about the empty file
        print("Error: Holdings file is empty")
        # Exit the script
        sys.exit(1)
    # Extract the header row (first row) and convert each cell to a stripped string
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    # Create a lowercase version of headers for case-insensitive column matching
    headers_lower = [h.lower() for h in headers]
    # Initialize the column index variable for the Ticker column
    ticker_col = None
    # Initialize the column index variable for the Name column
    name_col = None
    # Initialize the column index variable for the Market Value column
    mktval_col = None
    # Loop through each header to identify which column is which
    for i, h in enumerate(headers_lower):
        # Check if this column header matches common ticker column names
        if "ticker" in h or h == "symbol":
            # Store the index of the ticker column
            ticker_col = i
        # Check if this column header matches common name column names
        if "name" in h and "ticker" not in h:
            # Store the index of the name column
            name_col = i
        # Check if this column header matches common market value column names
        if "mkt val" in h or "market val" in h or "mkt_val" in h or "marketval" in h:
            # Store the index of the market value column
            mktval_col = i
    # If we couldn't identify the ticker column, fall back to the first column
    if ticker_col is None:
        # Print a warning that we're using a default column
        print("Warning: Could not identify Ticker column, using first column")
        # Default to column index 0
        ticker_col = 0
    # If we couldn't identify the name column, fall back to the second column
    if name_col is None:
        # Print a warning that we're using a default column
        print("Warning: Could not identify Name column, using second column")
        # Default to column index 1
        name_col = 1
    # Initialize an empty list to store the parsed holding records
    holdings = []
    # Loop through each data row, skipping the header row at index 0
    for row in rows[1:]:
        # Skip rows that are completely empty or too short to have a ticker
        if not row or len(row) <= ticker_col or row[ticker_col] is None:
            # Continue to the next row
            continue
        # Extract the ticker value from this row and convert to string
        ticker = str(row[ticker_col]).strip()
        # Skip rows where the ticker cell was empty
        if not ticker:
            # Continue to the next row
            continue
        # Extract the company name, using empty string if the cell is missing
        name = str(row[name_col]).strip() if len(row) > name_col and row[name_col] else ""
        # Initialize the market value to zero as a default
        mkt_val = 0.0
        # Check if the market value column was identified and this row has data in it
        if mktval_col is not None and len(row) > mktval_col and row[mktval_col] is not None:
            # Try to convert the cell value to a floating point number
            try:
                # Parse the market value as a float for numeric comparison
                mkt_val = float(row[mktval_col])
            # Catch conversion errors if the cell contains non-numeric data
            except (ValueError, TypeError):
                # Keep the default value of 0.0
                mkt_val = 0.0
        # Determine if this is a short position (negative market value means short)
        side = "short" if mkt_val < 0 else "long"
        # Detect which market the ticker trades on from its suffix
        market = detect_market(ticker)
        # Create a dictionary containing all the parsed data for this holding
        holding = {
            "ticker": ticker,
            "name": name,
            "mkt_val": mkt_val,
            "side": side,
            "market": market,
        }
        # Add this holding record to our list
        holdings.append(holding)
    # Print how many holdings were successfully loaded
    print(f"  Loaded {len(holdings)} holdings from {filepath}")
    # Return the complete list of holdings
    return holdings


# Define a function to generate a competitive profile JSON template from holdings
def generate_profile_template(holdings, output_path):
    # Initialize an empty dictionary for the template we'll build
    template = {}
    # Initialize an empty dictionary for any existing profile data to preserve
    existing = {}
    # Check if a profile file already exists at the output path
    if os.path.exists(output_path):
        # Try to load the existing file to preserve user-entered data
        try:
            # Open the existing file for reading
            with open(output_path, "r") as f:
                # Parse the JSON content into a dictionary
                existing = json.load(f)
            # Print a message that we found and loaded existing data
            print(f"  Found existing profile file with {len(existing)} entries")
        # Catch JSON parsing errors or file read errors
        except (json.JSONDecodeError, IOError):
            # Print a warning that the existing file was unreadable
            print(f"  Warning: Could not parse existing profile file, creating fresh template")
    # Loop through each holding to create or preserve its template entry
    for h in holdings:
        # Get the ticker symbol as the dictionary key
        ticker = h["ticker"]
        # Skip ETFs, cash, currency, and money market funds — they don't face competitive threats
        if is_excluded_holding(ticker, h.get("name", "")):
            # Continue to the next holding
            continue
        # Check if this ticker already has a profile in the existing file
        if ticker in existing:
            # Preserve the existing entry without overwriting user-entered data
            template[ticker] = existing[ticker]
        # If the ticker is new, create a blank template entry
        else:
            # Create a skeleton entry with name and side pre-populated
            template[ticker] = {
                "name": h["name"],
                "sector": "",
                "products": "",
                "competitor_keywords": [],
                "side": h["side"],
            }
    # Open the output file for writing the complete template
    with open(output_path, "w") as f:
        # Write the template as pretty-printed JSON with 2-space indentation
        json.dump(template, f, indent=2)
    # Count how many entries are new (no sector filled in yet)
    new_count = sum(1 for t in template.values() if not t.get("sector"))
    # Count how many entries already have user-entered data
    filled_count = len(template) - new_count
    # Print where the template was saved
    print(f"  Profile template written to: {output_path}")
    # Print the count of filled vs new entries
    print(f"  {filled_count} profiles already filled in, {new_count} entries need data")
    # Return the template dictionary
    return template


# Define a function to read filled-in competitive profiles from the JSON file
def read_competitive_profiles(filepath):
    # Check if the profiles file exists on disk
    if not os.path.exists(filepath):
        # Print a message that no profiles file was found
        print(f"  No competitive profile file found at: {filepath}")
        # Return an empty dictionary since there's nothing to load
        return {}
    # Try to open and parse the JSON profiles file
    try:
        # Open the file for reading
        with open(filepath, "r") as f:
            # Parse the JSON content into a dictionary
            profiles = json.load(f)
    # Catch JSON parsing errors or file read errors
    except (json.JSONDecodeError, IOError) as e:
        # Print the error details
        print(f"  Error reading profile file: {e}")
        # Return an empty dictionary
        return {}
    # Filter to only include profiles that have a sector AND are not ETFs/cash/currency
    filled = {k: v for k, v in profiles.items() if v.get("sector") and not is_excluded_holding(k, v.get("name", ""))}
    # Print how many usable profiles were found out of the total
    print(f"  Loaded {len(filled)} filled competitive profiles (out of {len(profiles)} total)")
    # Return only the profiles that have been filled in by the user
    return filled


# Define a function that maps CSV column headers to standardized field names
def detect_csv_columns(headers):
    # Define regex patterns to match for each standard field we want to extract
    patterns = {
        "company_name": [r"company", r"^name$", r"organization", r"startup"],
        "industry": [r"industry", r"sector", r"category", r"vertical", r"segment"],
        "revenue": [r"revenue", r"annual.?revenue", r"arr", r"estimated.?revenue"],
        "employees": [r"employee", r"headcount", r"team.?size", r"staff"],
        "funding": [r"funding", r"total.?raised", r"capital.?raised", r"investment"],
        "growth": [r"growth", r"growth.?rate", r"revenue.?growth", r"yoy"],
        "location": [r"location", r"\bhq\b", r"headquarters", r"city", r"country"],
        "description": [r"description", r"about", r"summary", r"overview", r"business"],
    }
    # Initialize an empty mapping from standard field names to column indices
    column_map = {}
    # Loop through each standard field and its list of matching regex patterns
    for field, field_patterns in patterns.items():
        # Loop through each header in the CSV to check for a match
        for i, header in enumerate(headers):
            # Convert the header to lowercase for case-insensitive comparison
            header_lower = header.lower().strip()
            # Loop through each regex pattern for this field
            for pattern in field_patterns:
                # Check if the pattern matches anywhere in the header text
                if re.search(pattern, header_lower):
                    # Store the column index for this standard field
                    column_map[field] = i
                    # Break out of the pattern loop since we found a match
                    break
            # If we already matched this field, move on to the next field
            if field in column_map:
                # Break out of the header loop
                break
    # Return the mapping of standard field names to their column indices
    return column_map


# Define a function to read all private company CSV files from a directory
def read_private_companies(csv_dir):
    # Check if the CSV directory path is valid and exists
    if not csv_dir or not os.path.exists(csv_dir):
        # Print a message that the directory was not found
        print(f"  No CSV directory found at: {csv_dir}")
        # Return an empty list since there are no companies to load
        return []
    # Find all files ending in .csv in the specified directory
    csv_files = sorted(Path(csv_dir).glob("*.csv"))
    # Check if any CSV files were found
    if not csv_files:
        # Print a message that no CSVs exist in the directory
        print(f"  No CSV files found in: {csv_dir}")
        # Return an empty list
        return []
    # Print how many CSV files were discovered
    print(f"  Found {len(csv_files)} CSV file(s) in {csv_dir}")
    # Initialize an empty list to accumulate all private companies across all files
    all_companies = []
    # Loop through each CSV file to read its contents
    for csv_file in csv_files:
        # Try to read and parse this CSV file
        try:
            # Open the CSV file with UTF-8 encoding, ignoring malformed characters
            with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                # Create a CSV reader that handles quoted fields and commas
                reader = csv.reader(f)
                # Read the first row as the header row
                headers = next(reader, None)
                # Skip this file if it has no header row
                if not headers:
                    # Move on to the next CSV file
                    continue
                # Detect which columns map to our standard field names
                col_map = detect_csv_columns(headers)
                # Check if we found at least the company name column
                if "company_name" not in col_map:
                    # Print a warning that this file lacks a name column
                    print(f"    Warning: No company name column found in {csv_file.name}, skipping")
                    # Skip this file
                    continue
                # Print which standard fields we identified in this file
                print(f"    {csv_file.name}: mapped columns: {list(col_map.keys())}")
                # Initialize a counter for companies loaded from this specific file
                count = 0
                # Loop through each data row in the CSV
                for row in reader:
                    # Skip rows that are too short to have a company name
                    if len(row) <= col_map["company_name"]:
                        # Continue to the next row
                        continue
                    # Extract the company name from the mapped column index
                    company_name = row[col_map["company_name"]].strip()
                    # Skip rows where the company name is empty
                    if not company_name:
                        # Continue to the next row
                        continue
                    # Create a dictionary for this company with its name and source file
                    company = {"company_name": company_name, "source_file": csv_file.name}
                    # Loop through all other mapped fields to extract their values
                    for field, col_idx in col_map.items():
                        # Skip the company_name field since it's already set
                        if field == "company_name":
                            # Continue to the next field
                            continue
                        # Check if this row has data in the column for this field
                        if col_idx < len(row) and row[col_idx].strip():
                            # Store the field value in the company dictionary
                            company[field] = row[col_idx].strip()
                    # Add this company record to the master list
                    all_companies.append(company)
                    # Increment the per-file counter
                    count += 1
                # Print how many companies were loaded from this file
                print(f"    Loaded {count} companies from {csv_file.name}")
        # Catch any errors reading this particular file
        except Exception as e:
            # Print the error with the file name for debugging
            print(f"    Error reading {csv_file.name}: {e}")
    # Print the total number of private companies loaded across all files
    print(f"  Total private companies loaded: {len(all_companies)}")
    # Return the complete list of all private companies
    return all_companies


# Define a function to filter private companies by keyword relevance to a holding
def filter_companies_by_keywords(companies, keywords):
    # If there are no keywords to match against, return nothing
    if not keywords:
        # Return an empty list
        return []
    # Convert all keywords to lowercase for case-insensitive matching
    keywords_lower = [kw.lower() for kw in keywords]
    # Initialize a list to store companies that match at least one keyword
    matches = []
    # Loop through each private company to check for keyword matches
    for company in companies:
        # Build a single searchable text blob from the company's key text fields
        searchable = " ".join([
            company.get("company_name", ""),
            company.get("industry", ""),
            company.get("description", ""),
        ]).lower()
        # Check if any of the keywords appear in the searchable text
        matched = any(kw in searchable for kw in keywords_lower)
        # If the company matched at least one keyword, keep it
        if matched:
            # Add the matching company to our results list
            matches.append(company)
    # Return the filtered list of relevant companies
    return matches


# Define a mapping from granular sector names to broad super-sectors for batching
SECTOR_TO_SUPERSECTOR = {
    # Technology / Semiconductors
    "Semiconductors": "Technology & Semiconductors",
    "Semiconductor Equipment": "Technology & Semiconductors",
    "Semiconductor Materials": "Technology & Semiconductors",
    "Electronic Components": "Technology & Semiconductors",
    "Electronics Distribution": "Technology & Semiconductors",
    "PC / Electronics": "Technology & Semiconductors",
    "Computer Peripherals / Networking": "Technology & Semiconductors",
    "Electronic Test Equipment": "Technology & Semiconductors",
    "Optical Equipment": "Technology & Semiconductors",
    "Functional Films / Materials": "Technology & Semiconductors",
    "Technology / Internet": "Technology & Semiconductors",
    # IT / Software
    "IT Services": "IT Services & Software",
    "IT Services / Parking": "IT Services & Software",
    "IT Services / Software": "IT Services & Software",
    "Internet / Marketplace": "IT Services & Software",
    "HR / Information Services": "IT Services & Software",
    "IT Solutions / Cybersecurity": "IT Services & Software",
    "Streaming / Telecom": "IT Services & Software",
    "Telecom / IT Services": "IT Services & Software",
    "Telecom Equipment / Systems": "IT Services & Software",
    "Video Games": "IT Services & Software",
    # Financial Services
    "Digital Banking": "Financial Services",
    "Community Banking": "Financial Services",
    "Banking": "Financial Services",
    "Investment Banking / Financial Services": "Financial Services",
    "Financial Exchange": "Financial Services",
    "Online Financial Services": "Financial Services",
    "Investment Banking / Securities": "Financial Services",
    "Insurance": "Financial Services",
    "Online Securities": "Financial Services",
    "Insurance / Financial Agency": "Financial Services",
    "Agricultural Finance": "Financial Services",
    "Business Development Company": "Financial Services & BDCs",
    "Venture Lending BDC": "Financial Services & BDCs",
    "Growth Stage BDC": "Financial Services & BDCs",
    "CLO Fund": "Financial Services & BDCs",
    "Alternative Asset Management": "Financial Services & BDCs",
    # Real Estate
    "Real Estate": "Real Estate & Construction",
    "Real Estate / Homebuilding": "Real Estate & Construction",
    "Real Estate / Property Management": "Real Estate & Construction",
    "Real Estate / Condominiums": "Real Estate & Construction",
    "Data Center REIT": "Real Estate & Construction",
    "Homebuilding": "Real Estate & Construction",
    # Construction
    "Construction Engineering": "Real Estate & Construction",
    "Construction": "Real Estate & Construction",
    "Construction / Civil Engineering": "Real Estate & Construction",
    "Forestry / Housing": "Real Estate & Construction",
    # Industrial / Machinery
    "Construction Equipment": "Industrial & Machinery",
    "Outdoor Power Equipment": "Industrial & Machinery",
    "Machine Tools": "Industrial & Machinery",
    "Packaging Machinery": "Industrial & Machinery",
    "Industrial Seals / Fluid Control": "Industrial & Machinery",
    "Building Automation / Control": "Industrial & Machinery",
    "Fire Safety Equipment": "Industrial & Machinery",
    "Commercial Refrigeration": "Industrial & Machinery",
    "Scientific Instruments": "Industrial & Machinery",
    "Electric Equipment / Motors": "Industrial & Machinery",
    "Auto Parts": "Industrial & Machinery",
    "Packaging": "Industrial & Machinery",
    "Wire Products / Industrial": "Industrial & Machinery",
    "Rubber / Polymer Products": "Industrial & Machinery",
    "Healthcare / Industrial Equipment": "Industrial & Machinery",
    # Materials / Chemicals
    "Industrial Materials": "Materials & Chemicals",
    "Specialty Steel": "Materials & Chemicals",
    "Refractories": "Materials & Chemicals",
    "Refractories / Ceramics": "Materials & Chemicals",
    "Specialty Chemicals": "Materials & Chemicals",
    "Specialty Chemicals / Semiconductor": "Materials & Chemicals",
    "Industrial Chemicals / Hygiene": "Materials & Chemicals",
    "Paints / Coatings": "Materials & Chemicals",
    "Metal Products / Exterior Materials": "Materials & Chemicals",
    "Steel Manufacturing": "Materials & Chemicals",
    "Mining / Metals / Machinery": "Materials & Chemicals",
    # Trading / Distribution (sogo shosha + industrial distributors)
    "Trading / Conglomerate": "Trading & Distribution",
    "Steel / Materials Trading": "Trading & Distribution",
    "Trading / Distribution": "Trading & Distribution",
    "Industrial Trading": "Trading & Distribution",
    "Industrial Trading / Distribution": "Trading & Distribution",
    "Industrial Trading / Electronics": "Trading & Distribution",
    "Industrial Distribution": "Trading & Distribution",
    "Electronics Distribution": "Trading & Distribution",
    # Food & Consumer
    "Food Manufacturing": "Food & Consumer",
    "Confectionery / Snacks": "Food & Consumer",
    "Food / Condiments": "Food & Consumer",
    "Confectionery": "Food & Consumer",
    "Flour Milling / Food": "Food & Consumer",
    "Edible Oil / Food": "Food & Consumer",
    "Food Packaging / Distribution": "Food & Consumer",
    "Meat / Food Distribution": "Food & Consumer",
    "Spirits / Beverages": "Food & Consumer",
    "Grocery Retail": "Food & Consumer",
    "Supermarket Retail": "Food & Consumer",
    # Retail / Consumer (non-food)
    "Bicycle Retail": "Retail & Consumer Products",
    "Electronics Retail": "Retail & Consumer Products",
    "Bicycle / Sports Retail": "Retail & Consumer Products",
    "Motorcycle Helmets / Safety": "Retail & Consumer Products",
    "Eyewear": "Retail & Consumer Products",
    "Musical Instruments": "Retail & Consumer Products",
    "Auto Parts Retail": "Retail & Consumer Products",
    "Retail": "Retail & Consumer Products",
    "Restaurants / Retail": "Retail & Consumer Products",
    "Luxury Goods": "Luxury",
    "Luxury Fashion": "Luxury",
    # Coffee / QSR
    "Coffee / Quick Service Restaurant": "Retail & Consumer Products",
    # Used Car
    "Used Car Retail": "Automotive & Used Cars",
    "Online Used Car Sales": "Automotive & Used Cars",
    # Transport / Airports
    "Airport Operations": "Transport & Airports",
    "Railway / Entertainment": "Transport & Airports",
    "Railway": "Transport & Airports",
    "Shipping": "Transport & Airports",
    "Tourism / Transportation": "Transport & Airports",
    "Tourism / Ski Resorts": "Transport & Airports",
    "Logistics IT / Transportation": "Transport & Airports",
    # Energy
    "Midstream Energy": "Energy & Infrastructure",
    # E-commerce / Cloud
    "E-commerce / Cloud Computing": "Technology & Semiconductors",
    # Staffing
    "Education / Staffing": "Staffing & Services",
    "Manufacturing Staffing": "Staffing & Services",
    "Staffing / Outsourcing": "Staffing & Services",
    "Building Maintenance / Services": "Staffing & Services",
    "Building Maintenance / Staffing": "Staffing & Services",
    # Clinical Research
    "Clinical Research / CRO": "Healthcare & Life Sciences",
    # Other
    "Horse Racing / Entertainment": "Other",
    "Engineering Services": "Other",
    "Industrial Materials / Geotextiles": "Other",
    "Technology / Recycling": "Other",
}


# Define a function to map a granular sector to its broad super-sector
def get_supersector(sector):
    # Look up the sector in the mapping, defaulting to "Other" if not found
    return SECTOR_TO_SUPERSECTOR.get(sector, "Other")


# Define a function to group holdings by broad super-sector for efficient API batching
def group_holdings_by_sector(profiles, holdings_lookup):
    # Initialize a dictionary to group holdings by their super-sector
    sector_groups = {}
    # Loop through each ticker and its competitive profile
    for ticker, profile in profiles.items():
        # Get the granular sector for this holding, defaulting to "Other" if empty
        sector = profile.get("sector", "Other").strip() or "Other"
        # Map the granular sector to a broad super-sector for batching
        supersector = get_supersector(sector)
        # Create the super-sector group list if this is the first holding in it
        if supersector not in sector_groups:
            # Initialize an empty list for this super-sector
            sector_groups[supersector] = []
        # Get the base holding data from the holdings lookup, with defaults
        base = holdings_lookup.get(ticker, {
            "ticker": ticker,
            "name": profile.get("name", ""),
            "mkt_val": 0,
            "side": "long",
            "market": "US",
        })
        # Merge profile data into the holding data to create a combined record
        combined = {**base, **profile, "ticker": ticker}
        # Override the side from the profile if it was explicitly set there
        if profile.get("side"):
            # Use the side specified in the profile
            combined["side"] = profile["side"]
        # Add the combined holding record to its super-sector group
        sector_groups[supersector].append(combined)
    # Print how many super-sector batches were created
    print(f"  Grouped holdings into {len(sector_groups)} sector batch(es) for API calls")
    # Return the dictionary mapping super-sectors to lists of holdings
    return sector_groups


# Define a function to format one private company's data as readable text for the prompt
def format_company_for_prompt(company):
    # Start with the company name as the first line
    parts = [f"  - Company: {company['company_name']}"]
    # Add the industry field if available
    if company.get("industry"):
        # Append the industry line
        parts.append(f"    Industry: {company['industry']}")
    # Add the revenue field if available
    if company.get("revenue"):
        # Append the revenue line
        parts.append(f"    Revenue: {company['revenue']}")
    # Add the growth rate field if available
    if company.get("growth"):
        # Append the growth line
        parts.append(f"    Growth: {company['growth']}")
    # Add the employee count field if available
    if company.get("employees"):
        # Append the employees line
        parts.append(f"    Employees: {company['employees']}")
    # Add the funding raised field if available
    if company.get("funding"):
        # Append the funding line
        parts.append(f"    Funding: {company['funding']}")
    # Add the location field if available
    if company.get("location"):
        # Append the location line
        parts.append(f"    Location: {company['location']}")
    # Add the description field if available, truncated to 200 characters
    if company.get("description"):
        # Truncate long descriptions to keep the prompt manageable
        desc = company["description"][:200]
        # Append the truncated description line
        parts.append(f"    Description: {desc}")
    # Join all the parts with newlines and return the formatted string
    return "\n".join(parts)


# Define a function to build the full API prompt for a batch of holdings
def build_api_prompt(holdings_batch, all_companies):
    # Initialize a list to collect each holding's section of the prompt
    holdings_sections = []
    # Initialize a list to collect all keyword-filtered companies (deduplicated)
    all_relevant = []
    # Track company names already added to avoid sending duplicates to the API
    seen_companies = set()
    # Loop through each holding in this sector batch
    for holding in holdings_batch:
        # Get the competitor keywords for this holding
        keywords = holding.get("competitor_keywords", [])
        # Filter private companies by relevance to this holding's keywords
        relevant = filter_companies_by_keywords(all_companies, keywords)
        # Build a note for short positions to include in the prompt
        side_note = ""
        # Check if this is a short position and add a contextual note
        if holding.get("side") == "short":
            # Set the note explaining the short position context
            side_note = " [SHORT POSITION - threats to this company are POSITIVE for the portfolio]"
        # Build the formatted text block describing this holding
        section = f"Holding: {holding.get('name', holding['ticker'])} ({holding['ticker']}){side_note}\n"
        # Add the sector information to the section
        section += f"  Sector: {holding.get('sector', 'N/A')}\n"
        # Add the products/services information to the section
        section += f"  Products/Services: {holding.get('products', 'N/A')}\n"
        # Add the competitor keywords to the section
        section += f"  Competitor Keywords: {', '.join(keywords)}\n"
        # Add the count of candidate companies found for this holding
        section += f"  Candidate companies to evaluate: {len(relevant)}"
        # Add this holding's section to the list
        holdings_sections.append(section)
        # Add the relevant companies to the master list, skipping duplicates
        for company in relevant:
            # Check if this company name has already been added
            if company["company_name"] not in seen_companies:
                # Mark this company as seen
                seen_companies.add(company["company_name"])
                # Add the company to the deduped master list
                all_relevant.append(company)
    # Begin constructing the full prompt with the system instruction
    prompt = """You are an equity research analyst specializing in competitive threat assessment.
Your task is to identify which fast-growing private companies represent genuine competitive threats to public company holdings in a portfolio.

Be selective — only flag companies that are truly competing in the same space, not tangentially related ones.

HOLDINGS TO ANALYZE:

"""
    # Add all the formatted holding sections to the prompt
    prompt += "\n\n".join(holdings_sections)
    # Add the private companies section header
    prompt += "\n\nPRIVATE COMPANIES TO EVALUATE:\n"
    # Check if we have any companies to include
    if all_relevant:
        # Loop through each relevant company and add its formatted data
        for company in all_relevant:
            # Append this company's formatted text block
            prompt += "\n" + format_company_for_prompt(company) + "\n"
    # If no companies matched the keyword filters, say so
    else:
        # Add a note that no candidates were found
        prompt += "\nNo candidate companies matched the keyword filters.\n"
    # Add the detailed instructions for the AI analysis
    prompt += """
INSTRUCTIONS:
For each holding, identify which private companies above are genuine competitive threats.

For each threat, provide:
- holding_ticker: Ticker of the threatened holding
- holding_name: Name of the threatened holding
- holding_side: "long" or "short"
- threat_company: Name of the threatening private company
- threat_score: 1-5 (1=minor, 2=emerging, 3=moderate, 4=significant, 5=severe)
- threat_type: Primary threat vector — "revenue", "margins", or "market_share"
- reasoning: 1-2 sentence explanation of why this is a genuine threat

IMPORTANT: For SHORT positions, threats to the company are POSITIVE for the portfolio.
Still identify them as threats to the company, but note the short context.

Return ONLY a JSON object in this exact format (no markdown fences, no extra text):
{
  "threats": [
    {
      "holding_ticker": "TICKER",
      "holding_name": "Company Name",
      "holding_side": "long",
      "threat_company": "Private Co Name",
      "threat_score": 3,
      "threat_type": "revenue",
      "reasoning": "Explanation here"
    }
  ],
  "holdings_with_no_threats": ["TICKER1", "TICKER2"]
}

If no threats are identified for any holding, return an empty threats array and list all tickers in holdings_with_no_threats."""
    # Return the constructed prompt and the count of relevant companies
    return prompt, len(all_relevant)


# Define a function to call the Anthropic API with rate limiting support
def call_anthropic_api(client, prompt, dry_run=False):
    # If this is a dry run, display the prompt without making an API call
    if dry_run:
        # Print a separator line for readability
        print("\n" + "=" * 80)
        # Print a label indicating this is a dry run
        print("DRY RUN — Prompt that would be sent to the API:")
        # Print another separator
        print("=" * 80)
        # Print the full prompt text that would be sent
        print(prompt)
        # Print a closing separator
        print("=" * 80 + "\n")
        # Return None since no API call was made
        return None
    # Check if the Anthropic client library was successfully imported
    if client is None:
        # Print an error that the API client is not available
        print("  Error: Anthropic API client not available.")
        # Return None
        return None
    # Try to make the actual API call
    try:
        # Send the prompt to Claude Sonnet and wait for a response
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        # Extract the text content from the first content block of the response
        text = response.content[0].text
        # Return the raw response text
        return text
    # Catch any errors from the API call
    except Exception as e:
        # Print the error details
        print(f"  API call failed: {e}")
        # Return None to indicate the call failed
        return None


# Define a function to parse the structured JSON response from the API
def parse_api_response(response_text):
    # If the response is None (dry run or error), return empty results
    if response_text is None:
        # Return empty threats list and empty no-threats list
        return [], []
    # Try to parse the response text as JSON
    try:
        # Strip leading/trailing whitespace from the response
        cleaned = response_text.strip()
        # Check if Claude wrapped the JSON in markdown code fences
        if cleaned.startswith("```"):
            # Find the position of the first newline after the opening fence
            first_newline = cleaned.index("\n")
            # Find the position of the last closing code fence
            last_fence = cleaned.rfind("```")
            # Extract just the JSON content between the fences
            cleaned = cleaned[first_newline + 1 : last_fence].strip()
        # Parse the cleaned string as JSON
        data = json.loads(cleaned)
        # Extract the list of identified threats
        threats = data.get("threats", [])
        # Extract the list of holdings that had no threats
        no_threats = data.get("holdings_with_no_threats", [])
        # Return both lists
        return threats, no_threats
    # Catch JSON parsing errors
    except (json.JSONDecodeError, ValueError) as e:
        # Print a warning about the parse failure
        print(f"  Warning: Could not parse API response as JSON: {e}")
        # Print a preview of the response for debugging purposes
        print(f"  Response preview: {response_text[:500]}")
        # Return empty results
        return [], []


# Define a function to generate the markdown weekly digest report
def generate_markdown_digest(all_threats, holdings, profiles, portfolio_name, output_dir):
    # Get today's date formatted as YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    # Construct the full output file path
    output_path = os.path.join(output_dir, f"threat_digest_{today}.md")
    # Create the output directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)
    # Count the total number of holdings that were scanned (those with profiles)
    total_scanned = len(profiles)
    # Count the total number of threats that were identified
    total_threats = len(all_threats)
    # Group threats by holding ticker for the per-holding report sections
    threats_by_ticker = {}
    # Loop through each threat to organize them by holding
    for threat in all_threats:
        # Get the ticker associated with this threat
        ticker = threat.get("holding_ticker", "UNKNOWN")
        # Create the list for this ticker if it doesn't exist yet
        if ticker not in threats_by_ticker:
            # Initialize an empty list for this ticker's threats
            threats_by_ticker[ticker] = []
        # Add this threat to the appropriate ticker group
        threats_by_ticker[ticker].append(threat)
    # Find the top 5 holdings with the most threats for the summary section
    top_threatened = sorted(
        threats_by_ticker.items(), key=lambda x: len(x[1]), reverse=True
    )[:5]
    # Initialize a list to build the markdown content line by line
    lines = []
    # Add the report title with the portfolio name
    lines.append(f"# Competitive Threat Digest — {portfolio_name}")
    # Add the report date
    lines.append(f"\n**Date:** {today}\n")
    # Add the summary section header
    lines.append("## Summary\n")
    # Add the count of holdings scanned
    lines.append(f"- **Holdings scanned:** {total_scanned}")
    # Add the count of threats identified
    lines.append(f"- **Total threats identified:** {total_threats}")
    # Add the top threatened holdings if there are any
    if top_threatened:
        # Add the sub-header for top threatened holdings
        lines.append("- **Top threatened holdings:**")
        # Loop through the top threatened holdings to list them
        for ticker, ticker_threats in top_threatened:
            # Get the holding name from the first threat record
            name = ticker_threats[0].get("holding_name", ticker)
            # Get the position side from the first threat record
            side = ticker_threats[0].get("holding_side", "long")
            # Add a visual label if this is a short position
            side_label = " *(SHORT)*" if side == "short" else ""
            # Add this holding to the top-threatened list
            lines.append(
                f"  - {name} ({ticker}){side_label}: {len(ticker_threats)} threat(s)"
            )
    # Add a blank line before the detailed findings section
    lines.append("")
    # Add the detailed findings section header
    lines.append("## Detailed Findings\n")
    # Create a lookup dictionary from ticker to holding data
    holdings_lookup = {h["ticker"]: h for h in holdings}
    # Loop through each profiled holding in sorted order to show its threats
    for ticker, profile in sorted(profiles.items()):
        # Get the holding's display name
        name = profile.get("name", ticker)
        # Determine the position side, checking both profile and holdings data
        side = profile.get(
            "side", holdings_lookup.get(ticker, {}).get("side", "long")
        )
        # Add a visual tag for short positions
        side_label = " [SHORT]" if side == "short" else ""
        # Add the holding header as a level-3 heading
        lines.append(f"### {name} ({ticker}){side_label}\n")
        # Check if this holding has any identified threats
        if ticker in threats_by_ticker:
            # Get the list of threats for this holding
            ticker_threats = threats_by_ticker[ticker]
            # Sort threats by score descending so the most severe appear first
            ticker_threats.sort(
                key=lambda x: x.get("threat_score", 0), reverse=True
            )
            # Loop through each threat to add it to the report
            for threat in ticker_threats:
                # Get the numeric threat score
                score = threat.get("threat_score", 0)
                # Map numeric scores to human-readable severity labels
                severity_labels = {
                    1: "Minor",
                    2: "Emerging",
                    3: "Moderate",
                    4: "Significant",
                    5: "Severe",
                }
                # Look up the severity label for this score
                severity = severity_labels.get(score, "Unknown")
                # Get the threat type (revenue, margins, or market_share)
                threat_type = threat.get("threat_type", "N/A")
                # Add the threat company name with its score
                lines.append(
                    f"**{threat.get('threat_company', 'Unknown')}** — Threat Score: {score}/5 ({severity})"
                )
                # Add the type of threat
                lines.append(f"- *Threat to:* {threat_type}")
                # Add the reasoning for why this is a threat
                lines.append(
                    f"- *Why:* {threat.get('reasoning', 'No reasoning provided')}"
                )
                # If this is a short position, add a note about portfolio impact
                if side == "short":
                    # Add the portfolio-positive note
                    lines.append(
                        "- *Portfolio impact:* **POSITIVE** — threat to a short position"
                    )
                # Add a blank line between threats for readability
                lines.append("")
        # If no threats were found for this holding
        else:
            # Add a single line noting no threats
            lines.append("No new threats identified.\n")
    # Add a horizontal rule before the footer
    lines.append("---")
    # Add the generation timestamp footer
    lines.append(f"\n*Generated by Competitive Threat Tracker on {today}*")
    # Join all the lines into a single markdown string
    content = "\n".join(lines)
    # Open the output file for writing
    with open(output_path, "w") as f:
        # Write the complete markdown content to the file
        f.write(content)
    # Print where the digest was saved
    print(f"  Markdown digest written to: {output_path}")
    # Return the output file path
    return output_path


# Define a function to generate the structured threats CSV file
def generate_threats_csv(all_threats, companies_lookup, output_dir):
    # Get today's date formatted as YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    # Construct the full output file path
    output_path = os.path.join(output_dir, f"threats_{today}.csv")
    # Create the output directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)
    # Define the column headers for the CSV file
    fieldnames = [
        "holding_ticker",
        "holding_name",
        "holding_side",
        "threat_company",
        "threat_score",
        "threat_type",
        "reasoning",
        "threat_revenue",
        "threat_growth",
        "threat_funding",
        "data_source",
        "date_identified",
    ]
    # Open the CSV file for writing
    with open(output_path, "w", newline="") as f:
        # Create a DictWriter with the defined column headers
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        # Write the header row to the CSV
        writer.writeheader()
        # Loop through each threat to write one row per threat
        for threat in all_threats:
            # Get the threat company name for looking up additional metrics
            company_name = threat.get("threat_company", "")
            # Look up this company's data from the private companies for enrichment
            company_data = companies_lookup.get(company_name, {})
            # Build the complete row with threat data and enrichment data
            row = {
                "holding_ticker": threat.get("holding_ticker", ""),
                "holding_name": threat.get("holding_name", ""),
                "holding_side": threat.get("holding_side", ""),
                "threat_company": company_name,
                "threat_score": threat.get("threat_score", ""),
                "threat_type": threat.get("threat_type", ""),
                "reasoning": threat.get("reasoning", ""),
                "threat_revenue": company_data.get("revenue", ""),
                "threat_growth": company_data.get("growth", ""),
                "threat_funding": company_data.get("funding", ""),
                "data_source": company_data.get("source_file", ""),
                "date_identified": today,
            }
            # Write this row to the CSV file
            writer.writerow(row)
    # Print where the CSV was saved and how many rows were written
    print(f"  Threats CSV written to: {output_path} ({len(all_threats)} threats)")
    # Return the output file path
    return output_path


# Define the main function that orchestrates the entire workflow
def main():
    # Parse command-line arguments provided by the user
    args = parse_args()
    # Print a startup banner
    print("\n=== Competitive Threat Tracker MVP ===\n")

    # Step 1: Read the portfolio holdings from the Excel file
    print("[1/6] Reading portfolio holdings...")
    # Call the holdings reader with the user-specified file path
    holdings = read_holdings(args.holdings)
    # Create a lookup dictionary from ticker to holding data for quick access
    holdings_lookup = {h["ticker"]: h for h in holdings}

    # Step 2: Generate or update the competitive profile template
    print(f"\n[2/6] Managing competitive profile template...")
    # Generate the template, preserving any existing user-entered data
    generate_profile_template(holdings, args.profiles)
    # Check if the user only wanted to generate the template
    if args.holdings_only:
        # Print a message that we're done and exiting early
        print("\n--holdings-only flag set. Template generated. Exiting.")
        # Return to end the script
        return

    # Step 3: Read the competitive profiles that have been filled in
    print(f"\n[3/6] Reading competitive profiles...")
    # Load only the profiles where the user has entered sector/keyword data
    profiles = read_competitive_profiles(args.profiles)
    # Check if there are any usable profiles
    if not profiles:
        # Print guidance about filling in the profiles
        print("\nNo filled-in competitive profiles found.")
        # Tell the user which file to edit
        print(f"Please fill in sector, products, and competitor_keywords in: {args.profiles}")
        # Suggest using the holdings-only flag first
        print("Tip: Run with --holdings-only first to generate the template.")
        # Exit since there's nothing to analyze
        return

    # Step 4: Read private company data from CSV files
    print(f"\n[4/6] Reading private company data...")
    # Load companies from the CSV directory, or use an empty list if no directory given
    companies = read_private_companies(args.csv_dir) if args.csv_dir else []
    # Build a lookup dictionary from company name to company data for enriching output
    companies_lookup = {c["company_name"]: c for c in companies}
    # Check if we have both profiles and companies to analyze
    if not companies:
        # Print a warning that no private company data is loaded
        print("  Warning: No private company data loaded. API analysis will have no candidates.")
        # Print a hint about providing CSV data
        print("  Provide CSVs via --csv-dir to enable threat matching.")

    # Step 5: Run the API analysis
    print(f"\n[5/6] Running competitive threat analysis...")
    # Initialize the Anthropic API client variable
    client = None
    # Check if this is not a dry run (we need the actual client)
    if not args.dry_run:
        # Check if the anthropic library was imported successfully
        if Anthropic is None:
            # Print an error about the missing library
            print("  Error: anthropic package not installed. Install with: pip install anthropic")
            # Suggest using dry-run mode instead
            print("  Tip: Use --dry-run to preview prompts without the API.")
            # Exit the script
            return
        # Try to create the Anthropic client (reads ANTHROPIC_API_KEY from env)
        try:
            # Initialize the API client
            client = Anthropic()
        # Catch initialization errors (e.g., missing API key)
        except Exception as e:
            # Print the initialization error
            print(f"  Error initializing Anthropic client: {e}")
            # Print a hint about setting the API key
            print("  Make sure ANTHROPIC_API_KEY is set in your environment.")
            # Exit the script
            return
    # Group holdings by sector to minimize the number of API calls
    sector_groups = group_holdings_by_sector(profiles, holdings_lookup)
    # Initialize a master list to collect all identified threats
    all_threats = []
    # Initialize a set to track holdings with no threats
    all_no_threats = set()
    # Track the timestamp of the last API call for rate limiting
    last_api_call = 0.0
    # Initialize a counter for batch progress reporting
    batch_num = 0
    # Get the total number of batches for progress display
    total_batches = len(sector_groups)
    # Loop through each sector group to send batched API calls
    for sector, holdings_batch in sector_groups.items():
        # Increment the batch counter
        batch_num += 1
        # Print progress showing which batch we're on
        print(f"\n  Batch {batch_num}/{total_batches}: {sector} ({len(holdings_batch)} holding(s))")
        # Build the prompt for this batch of holdings
        prompt, relevant_count = build_api_prompt(holdings_batch, companies)
        # Print how many candidate companies passed the keyword filter
        print(f"    {relevant_count} candidate companies after keyword filtering")
        # Apply rate limiting by waiting if less than 2 seconds since last call
        elapsed = time.time() - last_api_call
        # Check if we need to pause to respect the rate limit
        if elapsed < 2.0 and not args.dry_run and last_api_call > 0:
            # Calculate how many seconds we still need to wait
            wait_time = 2.0 - elapsed
            # Print a message about the rate limiting pause
            print(f"    Rate limiting: waiting {wait_time:.1f}s...")
            # Sleep for the remaining time to stay under the rate limit
            time.sleep(wait_time)
        # Record the current time as the timestamp of this API call
        last_api_call = time.time()
        # Make the API call (or display the prompt in dry-run mode)
        response_text = call_anthropic_api(client, prompt, dry_run=args.dry_run)
        # Parse the structured JSON response from the API
        threats, no_threats = parse_api_response(response_text)
        # Print how many threats were found in this batch (skip for dry runs)
        if not args.dry_run:
            # Display the threat count for this batch
            print(f"    Identified {len(threats)} threat(s)")
        # Add this batch's threats to the master list
        all_threats.extend(threats)
        # Add any no-threat tickers to the tracking set
        all_no_threats.update(no_threats)

    # If this was a dry run, show a summary and exit without generating reports
    if args.dry_run:
        # Print a dry run completion message
        print(f"\n=== DRY RUN COMPLETE ===")
        # Show how many API calls would have been made
        print(f"Would have made {total_batches} API call(s)")
        # Tell the user how to run for real
        print("Remove --dry-run to execute the API calls.")
        # Exit
        return

    # Step 6: Generate the output reports
    print(f"\n[6/6] Generating reports...")
    # Generate the markdown weekly digest report
    md_path = generate_markdown_digest(
        all_threats, holdings, profiles, args.portfolio_name, args.output_dir
    )
    # Generate the structured CSV file of all threats
    csv_path = generate_threats_csv(all_threats, companies_lookup, args.output_dir)
    # Print the final summary banner
    print(f"\n=== Analysis Complete ===")
    # Print the count of holdings that were analyzed
    print(f"  Holdings analyzed: {len(profiles)}")
    # Print the total number of threats found
    print(f"  Threats identified: {len(all_threats)}")
    # Print the path to the markdown digest
    print(f"  Digest: {md_path}")
    # Print the path to the threats CSV
    print(f"  Threats CSV: {csv_path}")

    # Check if the user wants to send results via email
    if args.email:
        # Print email step
        print(f"\n[7/7] Sending email...")
        # Import the emailer module
        from emailer import load_config, send_email as send_threat_email
        # Load the email config
        email_config = load_config(args.config)
        # Send the email with the CSV and markdown attachments
        send_threat_email(email_config, csv_path, md_path, test_mode=args.test)


# Run the main function only if this script is executed directly (not imported)
if __name__ == "__main__":
    # Call main to start the program
    main()
