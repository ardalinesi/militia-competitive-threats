#!/usr/bin/env python3
"""
Disruption Monitor — Startup Intelligence Classifier
Loads a startup universe, classifies each startup on key dimensions
(strategy, product, TAM, geography, industry, subsector, AI dependency,
competitive advantage), and outputs a structured intelligence report.
"""

# Import argparse to handle command-line arguments
import argparse

# Import json for reading and writing JSON data
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

# Define an explicit whitelist of Growjo Industry values that qualify as software/tech
SOFTWARE_INDUSTRY_WHITELIST = {
    "ai", "saas", "tech services", "fintech", "it security", "digital health",
    "internet", "analytics", "devops", "hr", "marketing", "martech", "adtech",
    "salestech", "edtech", "legaltech", "iot", "networking", "event tech",
    "content", "e-learning providers", "foodtech",
}


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

# Try importing the OpenAI API client library
try:
    # Import the OpenAI class from the openai package
    from openai import OpenAI
# Catch the import error if openai is not installed
except ImportError:
    # Set OpenAI to None so we can check later if it's available
    OpenAI = None


# Define a function to parse and return command-line arguments
def parse_args():
    # Create an argument parser with a description of the script's purpose
    parser = argparse.ArgumentParser(
        description="Disruption Monitor: Classify fast-growing startups by strategy, product, TAM, industry, and competitive advantage"
    )
    # Add an optional argument for the path to the Excel holdings file (no longer required)
    parser.add_argument(
        "--holdings",
        default=None,
        help="Path to Excel file containing portfolio holdings (optional, for future cross-referencing)",
    )
    # Add an optional argument for the directory containing private company CSV files
    parser.add_argument(
        "--csv-dir",
        default=None,
        help="Directory containing private company CSV files",
    )
    # Add an optional argument for the directory where output reports will be saved
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for output files (default: output/)",
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
    # Add the scope flag to filter startups by type (software-only vs all)
    parser.add_argument(
        "--scope",
        default="software",
        choices=["software", "all"],
        help="Filter startups to software/SaaS/tech only (default) or include all industries",
    )
    # Add the startups-per-batch flag to control how many startups are sent per API call
    parser.add_argument(
        "--startups-per-batch",
        type=int,
        default=25,
        help="Number of startups to send per API call (default: 25)",
    )
    # Add a minimum employee count filter to proxy for ARR floor
    parser.add_argument(
        "--min-employees",
        type=int,
        default=None,
        help="Minimum employee count filter (proxy for ARR floor, e.g. 250 ≈ $50M ARR)",
    )
    # Add a maximum employee count filter to proxy for ARR ceiling
    parser.add_argument(
        "--max-employees",
        type=int,
        default=None,
        help="Maximum employee count filter (proxy for ARR ceiling, e.g. 10000 ≈ $2B ARR)",
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


# Define a function to filter startups to software/SaaS/tech companies based on the scope setting
def filter_startups_by_scope(companies, scope):
    # If scope is "all", return all companies without filtering
    if scope == "all":
        # Print a message that no scope filter is applied
        print(f"  Scope: all — keeping all {len(companies)} startups")
        # Return the unfiltered list
        return companies
    # Initialize a list to store companies that match the software scope
    filtered = []
    # Track which industries were rejected for the log
    rejected_industries = {}
    # Loop through each company to check if its Industry field is in the whitelist
    for company in companies:
        # Get the industry field and normalize to lowercase for matching
        industry = company.get("industry", "").strip().lower()
        # Check if this industry is in the explicit whitelist
        if industry in SOFTWARE_INDUSTRY_WHITELIST:
            # Add the matching company to our filtered list
            filtered.append(company)
        else:
            # Track rejected industries for debugging
            rejected_industries[industry] = rejected_industries.get(industry, 0) + 1
    # Print how many companies passed the scope filter
    print(f"  Scope: software — filtered {len(companies)} startups down to {len(filtered)} software/SaaS/tech companies")
    # Print the top rejected industries for transparency
    if rejected_industries:
        # Sort by count descending and show top 5
        top_rejected = sorted(rejected_industries.items(), key=lambda x: -x[1])[:5]
        # Format the rejected list
        rejected_str = ", ".join(f"{ind} ({cnt})" for ind, cnt in top_rejected)
        # Print which industries were excluded
        print(f"    Top excluded industries: {rejected_str}")
    # Return the filtered list of software-relevant startups
    return filtered


# Define a function to parse an employee count string into an integer (handles "1,418", "1418", "1.4K", etc.)
def parse_employee_count(raw):
    # If the value is empty or None, return None
    if not raw:
        return None
    # Remove commas and whitespace from the string
    cleaned = str(raw).strip().replace(",", "")
    # Try to parse as a plain integer first
    try:
        return int(cleaned)
    except ValueError:
        pass
    # Handle "K" suffix (e.g., "1.4K" = 1400)
    if cleaned.upper().endswith("K"):
        try:
            return int(float(cleaned[:-1]) * 1000)
        except ValueError:
            pass
    # Could not parse, return None
    return None


# Define a function to estimate ARR from employee count using $175K ARR-per-employee heuristic
def estimate_arr_from_employees(employee_count):
    # If we don't have an employee count, return None
    if employee_count is None:
        return None
    # Multiply employee count by $175K (midpoint of $150-200K SaaS rule of thumb)
    return employee_count * 175000


# Define a function to format an ARR estimate as a readable string (e.g., "$87.5M")
def format_arr_estimate(arr):
    # If the ARR is None, return empty string
    if arr is None:
        return ""
    # If the ARR is $1B or more, format in billions
    if arr >= 1_000_000_000:
        return f"${arr / 1_000_000_000:.1f}B"
    # If the ARR is $1M or more, format in millions
    if arr >= 1_000_000:
        return f"${arr / 1_000_000:.0f}M"
    # Otherwise format in thousands
    return f"${arr / 1000:.0f}K"


# Define a function to filter startups by employee count range (proxy for ARR band)
def filter_startups_by_employees(companies, min_employees, max_employees):
    # If neither filter is set, return all companies unchanged
    if min_employees is None and max_employees is None:
        return companies
    # Initialize a list for companies that pass the filter
    filtered = []
    # Count how many companies we skip because they have no employee data
    skipped_no_data = 0
    # Loop through each company to check its employee count
    for company in companies:
        # Parse the employee count from the raw CSV value
        emp_count = parse_employee_count(company.get("employees", ""))
        # If we can't parse the employee count, skip this company
        if emp_count is None:
            skipped_no_data += 1
            continue
        # Check the minimum employee threshold
        if min_employees is not None and emp_count < min_employees:
            continue
        # Check the maximum employee threshold
        if max_employees is not None and emp_count > max_employees:
            continue
        # This company passes the employee filter, keep it
        filtered.append(company)
    # Build a filter description string for the log message
    filter_desc = ""
    if min_employees is not None and max_employees is not None:
        filter_desc = f"{min_employees}-{max_employees} employees"
    elif min_employees is not None:
        filter_desc = f">= {min_employees} employees"
    else:
        filter_desc = f"<= {max_employees} employees"
    # Print how many companies passed the employee filter
    print(f"  Employee filter ({filter_desc}): {len(companies)} → {len(filtered)} startups ({skipped_no_data} skipped, no employee data)")
    # Return the filtered list
    return filtered


# Define a function to format one startup's data as readable text for the API prompt
def format_startup_for_prompt(company):
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


# Define a function to build the Stage 2 startup classification prompt for a batch of startups
def build_classification_prompt(startups_batch):
    # Start the prompt with the system instruction for the AI
    prompt = """You are an equity research analyst specializing in private market intelligence. For each startup below, classify it on the following dimensions:

1. **strategy**: The startup's strategic approach. One of: "disruptor" (directly attacking incumbents), "niche_specialist" (serving an underserved segment), "platform_play" (building an ecosystem/marketplace), "vertical_saas" (industry-specific software), "horizontal_tool" (cross-industry tool/infrastructure), "deep_tech" (R&D-heavy, novel technology), "marketplace" (connecting buyers and sellers), "other"
2. **product_service**: A 1-2 sentence description of their core product or service offering
3. **tam_estimate**: Estimated total addressable market size. One of: "micro" (<$1B), "small" ($1-10B), "medium" ($10-50B), "large" ($50-200B), "massive" (>$200B)
4. **geographic_focus**: Primary geographic markets. One of: "us_only", "north_america", "europe", "asia", "global", "emerging_markets", "other"
5. **industry**: The broad industry. Examples: "financial_services", "healthcare", "enterprise_software", "cybersecurity", "e_commerce", "logistics", "education", "energy", "media_entertainment", "real_estate", "agriculture", etc.
6. **subsector**: A more specific subsector within the industry. Be precise — e.g., "accounts_payable_automation" not just "fintech", or "endpoint_detection_response" not just "cybersecurity"
7. **ai_dependency**: How central is AI/ML to the company's competitive advantage? One of: "core" (AI is the product), "significant" (AI provides major differentiation), "moderate" (AI enhances but isn't central), "minimal" (little to no AI), "unknown"
8. **competitive_advantage**: A 1-2 sentence description of their primary moat or competitive edge (e.g., proprietary data, network effects, switching costs, regulatory advantage, technical IP, brand, cost structure)

Be specific and precise. Use only the information provided — do not hallucinate details. If you cannot determine a field from the data given, use "unknown".

STARTUPS:
"""
    # Loop through each startup in this batch to add its formatted data
    for startup in startups_batch:
        # Append this startup's formatted text block
        prompt += "\n" + format_startup_for_prompt(startup) + "\n"
    # Add the response format instructions
    prompt += """
Return ONLY a JSON array (no markdown fences, no extra text):
[
  {
    "startup_name": "Startup Name",
    "strategy": "disruptor",
    "product_service": "Description of what they do",
    "tam_estimate": "medium",
    "geographic_focus": "us_only",
    "industry": "enterprise_software",
    "subsector": "developer_tools",
    "ai_dependency": "core",
    "competitive_advantage": "Description of their moat"
  }
]"""
    # Return the constructed prompt
    return prompt


# Define a function to call the OpenAI API with rate limiting support
def call_openai_api(client, prompt, dry_run=False):
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
    # Check if the OpenAI client library was successfully imported
    if client is None:
        # Print an error that the API client is not available
        print("  Error: OpenAI API client not available.")
        # Return None
        return None
    # Try to make the actual API call
    try:
        # Send the prompt to GPT-4.1-mini with high token limit to avoid JSON truncation
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=16384,
            messages=[{"role": "user", "content": prompt}],
        )
        # Extract the text content from the first choice in the response
        text = response.choices[0].message.content
        # Return the raw response text
        return text
    # Catch any errors from the API call
    except Exception as e:
        # Print the error details
        print(f"  API call failed: {e}")
        # Return None to indicate the call failed
        return None


# Define a function to parse the startup classification JSON response from Stage 2
def parse_classification_response(response_text):
    # If the response is None (dry run or error), return empty results
    if response_text is None:
        # Return an empty list of classifications
        return []
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
        # Parse the cleaned string as a JSON array
        data = json.loads(cleaned)
        # Verify the parsed data is a list
        if not isinstance(data, list):
            # If it's a dict with a key containing the array, try to extract it
            if isinstance(data, dict):
                # Check common wrapper keys that Claude might use
                for key in ["results", "startups", "data", "classifications"]:
                    # Check if this key contains a list
                    if key in data and isinstance(data[key], list):
                        # Use that list as the data
                        data = data[key]
                        # Break since we found it
                        break
        # Return the parsed list of classifications
        return data if isinstance(data, list) else []
    # Catch JSON parsing errors
    except (json.JSONDecodeError, ValueError) as e:
        # Print a warning about the parse failure
        print(f"  Warning: Could not parse classification response as JSON: {e}")
        # Print a preview of the response for debugging purposes
        print(f"  Response preview: {response_text[:500]}")
        # Return empty results
        return []


# Define a function to generate a markdown startup classification digest
def generate_classification_digest(classifications, portfolio_name, output_dir):
    # Get today's date formatted as YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    # Construct the output file name
    filename = f"startup_intelligence_{today}.md"
    # Build the full output file path
    output_path = os.path.join(output_dir, filename)
    # Create the output directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)
    # Count totals for the summary section
    total = len(classifications)
    # Count startups by strategy type
    strategy_counts = {}
    # Count startups by industry
    industry_counts = {}
    # Count startups where AI is core
    ai_core_count = 0
    # Loop through all classifications to compute summary stats
    for c in classifications:
        # Get the strategy value
        strat = c.get("strategy", "unknown")
        # Increment the strategy counter
        strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
        # Get the industry value
        ind = c.get("industry", "unknown")
        # Increment the industry counter
        industry_counts[ind] = industry_counts.get(ind, 0) + 1
        # Check if AI is core to this startup
        if c.get("ai_dependency") == "core":
            # Increment the AI core counter
            ai_core_count += 1
    # Initialize a list to build the markdown content line by line
    lines = []
    # Add the report title
    lines.append(f"# Startup Intelligence Report — {portfolio_name}")
    # Add the report date
    lines.append(f"\n**Date:** {today}\n")
    # Add the summary section
    lines.append("## Summary\n")
    # Add the total startup count
    lines.append(f"- **Startups classified:** {total}")
    # Add the AI-core count
    lines.append(f"- **AI-core startups:** {ai_core_count}")
    # Add the industry breakdown
    lines.append(f"- **Industries covered:** {len(industry_counts)}")
    # Add blank line
    lines.append("")
    # Add strategy breakdown
    lines.append("### Strategy Breakdown\n")
    # Sort strategies by count descending
    for strat, count in sorted(strategy_counts.items(), key=lambda x: -x[1]):
        # Add each strategy and its count
        lines.append(f"- **{strat}:** {count}")
    # Add blank line
    lines.append("")
    # Add industry breakdown
    lines.append("### Industry Breakdown\n")
    # Sort industries by count descending
    for ind, count in sorted(industry_counts.items(), key=lambda x: -x[1]):
        # Add each industry and its count
        lines.append(f"- **{ind}:** {count}")
    # Add blank line
    lines.append("")
    # Add the detailed classifications section
    lines.append("## Startup Profiles\n")
    # Sort by industry then startup name for organized reading
    sorted_classifications = sorted(classifications, key=lambda x: (x.get("industry", ""), x.get("startup_name", "")))
    # Track current industry for section grouping
    current_industry = None
    # Loop through each classified startup
    for c in sorted_classifications:
        # Get the industry for this startup
        industry = c.get("industry", "unknown")
        # Check if we're starting a new industry group
        if industry != current_industry:
            # Update the current industry tracker
            current_industry = industry
            # Add an industry subheading
            lines.append(f"### {industry.replace('_', ' ').title()}\n")
        # Get the startup name
        name = c.get("startup_name", "Unknown")
        # Add the startup name as a bold entry
        lines.append(f"**{name}**")
        # Add the product/service description
        lines.append(f"- **Product/Service:** {c.get('product_service', 'Unknown')}")
        # Add the strategy
        lines.append(f"- **Strategy:** {c.get('strategy', 'Unknown')}")
        # Add the subsector
        lines.append(f"- **Subsector:** {c.get('subsector', 'Unknown')}")
        # Add the TAM estimate
        lines.append(f"- **TAM:** {c.get('tam_estimate', 'Unknown')}")
        # Add the geographic focus
        lines.append(f"- **Geographic Focus:** {c.get('geographic_focus', 'Unknown')}")
        # Add the AI dependency level
        lines.append(f"- **AI Dependency:** {c.get('ai_dependency', 'Unknown')}")
        # Add the competitive advantage
        lines.append(f"- **Competitive Advantage:** {c.get('competitive_advantage', 'Unknown')}")
        # Add enrichment data if available from the source CSV
        if c.get("funding"):
            # Add funding info
            lines.append(f"- **Funding:** {c['funding']}")
        # Check for growth data
        if c.get("growth"):
            # Add growth info
            lines.append(f"- **Growth:** {c['growth']}")
        # Check for employee data
        if c.get("employees"):
            # Add employee count
            lines.append(f"- **Employees:** {c['employees']}")
        # Add a blank line between entries
        lines.append("")
    # Add a horizontal rule before the footer
    lines.append("---")
    # Add the generation timestamp footer
    lines.append(f"\n*Generated by Disruption Monitor on {today}*")
    # Join all the lines into a single markdown string
    content = "\n".join(lines)
    # Open the output file for writing
    with open(output_path, "w") as f:
        # Write the complete markdown content to the file
        f.write(content)
    # Print where the digest was saved
    print(f"  Intelligence digest written to: {output_path}")
    # Return the output file path
    return output_path


# Define a function to generate the startup classification CSV
def generate_classification_csv(classifications, output_dir):
    # Get today's date formatted as YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    # Construct the full output file path
    output_path = os.path.join(output_dir, f"startup_classifications_{today}.csv")
    # Create the output directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)
    # Define the column headers for the CSV file (includes estimated_arr)
    fieldnames = [
        "startup_name",
        "strategy",
        "product_service",
        "tam_estimate",
        "geographic_focus",
        "industry",
        "subsector",
        "ai_dependency",
        "competitive_advantage",
        "estimated_arr",
        "funding",
        "growth",
        "employees",
        "location",
        "source_file",
        "date_classified",
    ]
    # Open the CSV file for writing
    with open(output_path, "w", newline="") as f:
        # Create a DictWriter with the defined column headers
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        # Write the header row to the CSV
        writer.writeheader()
        # Loop through each classification to write one row per startup
        for c in classifications:
            # Parse the employee count to compute the ARR estimate
            emp_count = parse_employee_count(c.get("employees", ""))
            # Compute the estimated ARR from the employee count
            arr_raw = estimate_arr_from_employees(emp_count)
            # Format the ARR as a human-readable string
            arr_str = format_arr_estimate(arr_raw)
            # Build the row from classification data
            row = {
                "startup_name": c.get("startup_name", ""),
                "strategy": c.get("strategy", ""),
                "product_service": c.get("product_service", ""),
                "tam_estimate": c.get("tam_estimate", ""),
                "geographic_focus": c.get("geographic_focus", ""),
                "industry": c.get("industry", ""),
                "subsector": c.get("subsector", ""),
                "ai_dependency": c.get("ai_dependency", ""),
                "competitive_advantage": c.get("competitive_advantage", ""),
                "estimated_arr": arr_str,
                "funding": c.get("funding", ""),
                "growth": c.get("growth", ""),
                "employees": c.get("employees", ""),
                "location": c.get("location", ""),
                "source_file": c.get("source_file", ""),
                "date_classified": today,
            }
            # Write this row to the CSV file
            writer.writerow(row)
    # Print where the CSV was saved and how many rows were written
    print(f"  Classifications CSV written to: {output_path} ({len(classifications)} startups)")
    # Return the output file path
    return output_path


# Define the main function that orchestrates the entire pipeline
def main():
    # Parse command-line arguments provided by the user
    args = parse_args()
    # Print a startup banner
    print("\n=== Disruption Monitor — Startup Intelligence ===\n")

    # ─── Stage 1: Load Startup Universe ───
    # Print the stage header
    print("[Stage 1] Loading startup universe...")
    # Read private companies from CSV files, or use empty list if no directory given
    companies = read_private_companies(args.csv_dir) if args.csv_dir else []
    # Check if we have any companies to analyze
    if not companies:
        # Print an error about missing startup data
        print("  Error: No startup data loaded. Provide CSVs via --csv-dir.")
        # Exit the script
        return
    # Filter startups by scope (software-only vs all)
    companies = filter_startups_by_scope(companies, args.scope)
    # Check if any companies passed the scope filter
    if not companies:
        # Print an error about no companies matching the scope
        print("  Error: No startups match the selected scope filter.")
        # Exit the script
        return
    # Apply employee count filter if --min-employees or --max-employees was provided
    companies = filter_startups_by_employees(companies, args.min_employees, args.max_employees)
    # Check if any companies passed the employee filter
    if not companies:
        # Print an error about no companies matching the employee range
        print("  Error: No startups match the employee count filter.")
        # Exit the script
        return
    # Build a lookup dictionary from company name to company data for enriching output
    companies_lookup = {c["company_name"]: c for c in companies}

    # ─── Stage 2: Startup Classification via Claude API ───
    # Print the stage header
    print(f"\n[Stage 2] Classifying startups (strategy, product, TAM, geo, industry, subsector, AI, moat)...")
    # Initialize the Anthropic API client variable
    client = None
    # Check if this is not a dry run (we need the actual client)
    if not args.dry_run:
        # Check if the openai library was imported successfully
        if OpenAI is None:
            # Print an error about the missing library
            print("  Error: openai package not installed. Install with: pip install openai")
            # Suggest using dry-run mode instead
            print("  Tip: Use --dry-run to preview prompts without the API.")
            # Exit the script
            return
        # Try to create the OpenAI client (reads OPENAI_API_KEY from env)
        try:
            # Initialize the API client
            client = OpenAI()
        # Catch initialization errors (e.g., missing API key)
        except Exception as e:
            # Print the initialization error
            print(f"  Error initializing OpenAI client: {e}")
            # Print a hint about setting the API key
            print("  Make sure OPENAI_API_KEY is set in your environment.")
            # Exit the script
            return
    # Calculate how many batches we need based on the startups-per-batch setting
    batch_size = args.startups_per_batch
    # Calculate the total number of batches using ceiling division
    total_batches = (len(companies) + batch_size - 1) // batch_size
    # Print the batch plan
    print(f"  Batching {len(companies)} startups into {total_batches} batch(es) of up to {batch_size}")
    # Initialize a master list to collect all classifications from all batches
    all_classifications = []
    # Track the timestamp of the last API call for rate limiting
    last_api_call = 0.0
    # Loop through each batch of startups
    for batch_idx in range(total_batches):
        # Calculate the start index for this batch
        start = batch_idx * batch_size
        # Calculate the end index for this batch
        end = min(start + batch_size, len(companies))
        # Extract this batch of startups from the full list
        batch = companies[start:end]
        # Print progress showing which batch we're on
        print(f"\n  Batch {batch_idx + 1}/{total_batches}: startups {start + 1}-{end}")
        # Build the classification prompt for this batch
        prompt = build_classification_prompt(batch)
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
        response_text = call_openai_api(client, prompt, dry_run=args.dry_run)
        # Parse the structured JSON response from the API
        batch_classifications = parse_classification_response(response_text)
        # Print how many startups were successfully classified in this batch
        if not args.dry_run:
            # Display the classification count
            print(f"    {len(batch_classifications)} startup(s) classified")
        # Add this batch's classifications to the master list
        all_classifications.extend(batch_classifications)

    # If this was a dry run, show a summary and exit without generating reports
    if args.dry_run:
        # Print a dry run completion message
        print(f"\n=== DRY RUN COMPLETE ===")
        # Show how many API calls would have been made
        print(f"Would have made {total_batches} classification API call(s)")
        # Tell the user how to run for real
        print("Remove --dry-run to execute the API calls.")
        # Exit
        return

    # Enrich classifications with source CSV data (funding, growth, employees, location)
    enriched = []
    # Track which startups were classified by name for deduplication
    seen_names = set()
    # Loop through each classification to enrich it
    for c in all_classifications:
        # Get the startup name from the classification
        name = c.get("startup_name", "")
        # Skip duplicates (same startup classified in overlapping batches)
        if name.lower() in seen_names:
            # Continue to the next classification
            continue
        # Add this name to the seen set
        seen_names.add(name.lower())
        # Look up the original CSV data for this startup
        source_data = companies_lookup.get(name, {})
        # Merge the source CSV fields into the classification
        c["funding"] = source_data.get("funding", "")
        # Add growth data from the source
        c["growth"] = source_data.get("growth", "")
        # Add employee data from the source
        c["employees"] = source_data.get("employees", "")
        # Add location data from the source
        c["location"] = source_data.get("location", "")
        # Add the source file name
        c["source_file"] = source_data.get("source_file", "")
        # Add the enriched classification to the list
        enriched.append(c)
    # Print the classification results
    print(f"\n  Total startups classified: {len(enriched)}")

    # ─── Stage 3: Output Reports ───
    # Print the stage header
    print(f"\n[Stage 3] Generating output reports...")
    # Generate the classification CSV
    csv_path = generate_classification_csv(enriched, args.output_dir)
    # Generate the markdown intelligence digest
    md_path = generate_classification_digest(enriched, args.portfolio_name, args.output_dir)

    # Print the final summary banner
    print(f"\n=== Classification Complete ===")
    # Print the total number of startups classified
    print(f"  Startups classified: {len(enriched)}")
    # Print the path to the intelligence digest
    print(f"  Intelligence digest: {md_path}")
    # Print the path to the classifications CSV
    print(f"  Classifications CSV: {csv_path}")

    # Check if the user wants to send results via email
    if args.email:
        # Print the email step
        print(f"\n[Email] Sending intelligence email...")
        # Import the emailer module
        from emailer import load_config, send_email as send_intelligence_email
        # Load the email config
        email_config = load_config(args.config)
        # Send the email with the CSV and markdown attachments
        send_intelligence_email(email_config, csv_path, md_path, test_mode=args.test)


# Run the main function only if this script is executed directly (not imported)
if __name__ == "__main__":
    # Call main to start the program
    main()
