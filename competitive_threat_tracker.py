#!/usr/bin/env python3
"""
Disruption Monitor — Competitive Threat Tracker
Starts from a startup universe, maps each startup to the public companies
it threatens, gathers financial evidence, then optionally filters to
portfolio holdings.
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

# Define keywords used to identify software/SaaS/tech companies for the --scope software filter
SOFTWARE_SCOPE_KEYWORDS = [
    "software", "saas", "cloud", "platform", "app", "digital", "tech",
    "ai", "artificial intelligence", "machine learning", "data", "analytics",
    "automation", "cybersecurity", "cyber", "devops", "api", "fintech",
    "edtech", "healthtech", "martech", "adtech", "regtech", "insurtech",
    "blockchain", "crypto", "iot", "internet of things", "robotics",
    "computer", "computing", "web", "mobile", "streaming", "e-commerce",
    "ecommerce", "payment", "neobank", "digital bank",
]


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

# Try importing yfinance for financial data lookups
try:
    # Import yfinance to pull earnings, revenue, analyst recommendations, and price data
    import yfinance as yf
# Catch the import error if yfinance is not installed
except ImportError:
    # Set yf to None so we can check later if it's available
    yf = None


# Define a function to parse and return command-line arguments
def parse_args():
    # Create an argument parser with a description of the script's purpose
    parser = argparse.ArgumentParser(
        description="Disruption Monitor: Identify threats to public companies from fast-growing startups"
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
    # Add a flag to skip the financial evidence stage entirely for faster testing
    parser.add_argument(
        "--skip-evidence",
        action="store_true",
        help="Skip Stage 3 (financial evidence) entirely for faster testing",
    )
    # Add a flag to enable the optional Claude + web search qualitative overlay
    parser.add_argument(
        "--qualitative",
        action="store_true",
        help="Enable Stage 3b: Claude + web search qualitative overlay on top of yfinance data",
    )
    # Add a flag to skip the holdings filter and only produce the broad market report
    parser.add_argument(
        "--broad-only",
        action="store_true",
        help="Skip the holdings filter and only produce the broad market report",
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
    # Loop through each company to check if it's in the software/tech space
    for company in companies:
        # Build a searchable text blob from the company's industry and description fields
        searchable = " ".join([
            company.get("industry", ""),
            company.get("description", ""),
            company.get("company_name", ""),
        ]).lower()
        # Check if any software/tech keyword appears in the searchable text
        matched = any(kw in searchable for kw in SOFTWARE_SCOPE_KEYWORDS)
        # If the company matches at least one keyword, keep it
        if matched:
            # Add the matching company to our filtered list
            filtered.append(company)
    # Print how many companies passed the scope filter
    print(f"  Scope: software — filtered {len(companies)} startups down to {len(filtered)} software/SaaS/tech companies")
    # Return the filtered list of software-relevant startups
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


# Define a function to build the Stage 2 threat mapping prompt for a batch of startups
def build_threat_mapping_prompt(startups_batch):
    # Start the prompt with the system instruction for the AI
    prompt = """You are an equity research analyst. For each startup below, identify:
1. What product/service/market it is targeting
2. Which specific publicly traded companies (by ticker and name) are most exposed to disruption from this startup
3. How the startup threatens them (revenue displacement, margin compression, market share loss)

Be specific — only list public companies where there is a clear, direct competitive overlap. Do not list tangentially related companies.

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
    "startup_description": "What they do",
    "target_market": "The specific market/product category they compete in",
    "threatened_companies": [
      {
        "ticker": "TICK",
        "company_name": "Public Co Name",
        "threat_type": "revenue | margins | market_share",
        "threat_score": 1,
        "reasoning": "1-2 sentence explanation"
      }
    ]
  }
]

If a startup does not clearly threaten any public company, include it with an empty threatened_companies array."""
    # Return the constructed prompt
    return prompt


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
        # Send the prompt to Claude Sonnet with high token limit to avoid JSON truncation
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
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


# Define a function to call the Anthropic API with web search tool enabled for qualitative research
def call_anthropic_api_with_search(client, prompt):
    # Check if the Anthropic client library was successfully imported
    if client is None:
        # Print an error that the API client is not available
        print("  Error: Anthropic API client not available.")
        # Return None
        return None
    # Try to make the API call with web search tool
    try:
        # Send the prompt to Claude Sonnet with web search enabled and high token limit
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16384,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        # Initialize an empty list to collect text responses from content blocks
        text_parts = []
        # Loop through each content block in the response
        for block in response.content:
            # Check if this block is a text block (not a tool use block)
            if hasattr(block, "text"):
                # Add the text to our collection
                text_parts.append(block.text)
        # Join all text parts into a single string
        text = "\n".join(text_parts)
        # Return the combined response text
        return text
    # Catch any errors from the API call
    except Exception as e:
        # Print the error details
        print(f"  API call with web search failed: {e}")
        # Return None to indicate the call failed
        return None


# Define a function to parse the threat mapping JSON response from Stage 2
def parse_threat_mapping_response(response_text):
    # If the response is None (dry run or error), return empty results
    if response_text is None:
        # Return an empty list of threat mappings
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
                for key in ["results", "startups", "data", "threats"]:
                    # Check if this key contains a list
                    if key in data and isinstance(data[key], list):
                        # Use that list as the data
                        data = data[key]
                        # Break since we found it
                        break
        # Return the parsed list of threat mappings
        return data if isinstance(data, list) else []
    # Catch JSON parsing errors
    except (json.JSONDecodeError, ValueError) as e:
        # Print a warning about the parse failure
        print(f"  Warning: Could not parse threat mapping response as JSON: {e}")
        # Print a preview of the response for debugging purposes
        print(f"  Response preview: {response_text[:500]}")
        # Return empty results
        return []


# Define a function to convert a Bloomberg-style ticker to a yfinance-compatible ticker
def map_ticker_to_yfinance(ticker):
    # Strip whitespace from the ticker
    ticker = ticker.strip()
    # Check if the ticker has a Japanese suffix and convert to Tokyo Stock Exchange format
    if ticker.endswith(" JP"):
        # Strip the " JP" suffix and append ".T" for Yahoo Finance's Tokyo exchange code
        return ticker[:-3].strip() + ".T"
    # Check if the ticker has a French suffix and convert to Paris exchange format
    elif ticker.endswith(" FP"):
        # Strip the " FP" suffix and append ".PA" for Yahoo Finance's Paris exchange code
        return ticker[:-3].strip() + ".PA"
    # Check if the ticker has a Mexican suffix and convert to Mexico exchange format
    elif ticker.endswith(" MM"):
        # Strip the " MM" suffix and append ".MX" for Yahoo Finance's Mexico exchange code
        return ticker[:-3].strip() + ".MX"
    # If no recognized suffix, return the ticker as-is (assumed US-listed)
    return ticker


# Define a function to strip market suffixes from a ticker for matching purposes
def strip_ticker_suffix(ticker):
    # Strip whitespace from the ticker
    ticker = ticker.strip()
    # Define the list of known Bloomberg market suffixes
    suffixes = [" JP", " FP", " MM", " LN", " GR", " AU", " HK", " SP", " IT", " SM"]
    # Loop through each suffix to check for a match
    for suffix in suffixes:
        # Check if the ticker ends with this suffix
        if ticker.endswith(suffix):
            # Return the ticker without the suffix
            return ticker[:-len(suffix)].strip()
    # No suffix found, return the ticker as-is
    return ticker


# Define a function to fetch financial evidence from yfinance for a single ticker (Stage 3a)
def fetch_yfinance_evidence(ticker_raw):
    # Convert the raw ticker to a yfinance-compatible format
    yf_ticker = map_ticker_to_yfinance(ticker_raw)
    # Initialize the evidence dictionary with default values
    evidence = {
        "ticker": ticker_raw,
        "yf_ticker": yf_ticker,
        "earnings_misses_last_4q": 0,
        "revenue_trend": "unknown",
        "revenue_qoq_changes": [],
        "analyst_consensus": "unknown",
        "recent_downgrades": 0,
        "price_return_3m": None,
        "price_return_6m": None,
        "evidence_strength": 0,
        "evidence_summary": "No financial data available",
    }
    # Check if yfinance is installed
    if yf is None:
        # Print a warning that yfinance is not available
        print(f"    Warning: yfinance not installed, skipping evidence for {ticker_raw}")
        # Return the default evidence dictionary
        return evidence
    # Try to fetch data from yfinance, wrapping everything in a try/except
    try:
        # Create a yfinance Ticker object for this stock
        ticker_obj = yf.Ticker(yf_ticker)

        # --- Earnings history: check for EPS misses ---
        # Try to access earnings history data
        try:
            # Get the earnings history DataFrame (actual vs estimate EPS)
            earnings_hist = ticker_obj.earnings_history
            # Check if we got valid earnings data back
            if earnings_hist is not None and not earnings_hist.empty:
                # Take the last 4 quarters of earnings data
                recent = earnings_hist.tail(4)
                # Initialize a counter for earnings misses
                misses = 0
                # Loop through each row to check for misses
                for _, row in recent.iterrows():
                    # Try to extract actual and estimate EPS values
                    try:
                        # Get the actual EPS value from this row
                        actual = row.get("epsActual", row.get("Reported EPS", None))
                        # Get the estimated EPS value from this row
                        estimate = row.get("epsEstimate", row.get("EPS Estimate", None))
                        # Check if both values exist and actual is below estimate
                        if actual is not None and estimate is not None and float(actual) < float(estimate):
                            # Increment the miss counter
                            misses += 1
                    # Catch any conversion or access errors
                    except (ValueError, TypeError):
                        # Skip this row if we can't parse the values
                        pass
                # Store the number of earnings misses
                evidence["earnings_misses_last_4q"] = misses
        # Catch any errors accessing earnings history
        except Exception:
            # Leave the default value of 0 misses
            pass

        # --- Revenue trend: quarterly financials ---
        # Try to access quarterly financial statements
        try:
            # Get the quarterly income statement data
            q_financials = ticker_obj.quarterly_financials
            # Check if we got valid financial data back
            if q_financials is not None and not q_financials.empty:
                # Look for a revenue row (could be labeled differently)
                revenue_row = None
                # Check common labels for the revenue line item
                for label in ["Total Revenue", "Revenue", "Operating Revenue"]:
                    # Check if this label exists in the financial data index
                    if label in q_financials.index:
                        # Use this row as the revenue data
                        revenue_row = q_financials.loc[label]
                        # Break since we found a match
                        break
                # Check if we found a revenue row with data
                if revenue_row is not None and len(revenue_row) >= 2:
                    # Sort by column date to ensure chronological order (oldest first)
                    revenue_sorted = revenue_row.sort_index()
                    # Take the last 4 quarters (or fewer if not enough data)
                    recent_rev = revenue_sorted.tail(4)
                    # Get the revenue values as a list
                    rev_values = recent_rev.values.tolist()
                    # Calculate quarter-over-quarter percentage changes
                    qoq_changes = []
                    # Loop through pairs of consecutive quarters to compute changes
                    for i in range(1, len(rev_values)):
                        # Check that the previous quarter's revenue is valid and non-zero
                        if rev_values[i - 1] is not None and rev_values[i - 1] != 0 and rev_values[i] is not None:
                            # Calculate the QoQ percentage change
                            change = (rev_values[i] - rev_values[i - 1]) / abs(rev_values[i - 1])
                            # Add this change to our list
                            qoq_changes.append(round(change, 4))
                    # Store the QoQ changes
                    evidence["revenue_qoq_changes"] = qoq_changes
                    # Determine the overall revenue trend from the changes
                    if qoq_changes:
                        # Count how many quarters had negative revenue growth
                        declining_quarters = sum(1 for c in qoq_changes if c < 0)
                        # If more than half the quarters declined, label as declining
                        if declining_quarters > len(qoq_changes) / 2:
                            # Set the trend to declining
                            evidence["revenue_trend"] = "declining"
                        # If more than half grew, label as growing
                        elif declining_quarters < len(qoq_changes) / 2:
                            # Set the trend to growing
                            evidence["revenue_trend"] = "growing"
                        # If exactly split, label as stable
                        else:
                            # Set the trend to stable
                            evidence["revenue_trend"] = "stable"
        # Catch any errors accessing quarterly financials
        except Exception:
            # Leave the default value
            pass

        # --- Analyst recommendations ---
        # Try to access analyst recommendation data
        try:
            # Get the recommendations DataFrame
            recs = ticker_obj.recommendations
            # Check if we got valid recommendations data
            if recs is not None and not recs.empty:
                # Initialize a counter for recent downgrades
                downgrade_count = 0
                # Initialize the consensus variable
                consensus = "unknown"
                # Try to use recommendations_summary for consensus
                try:
                    # Get the recommendations summary
                    rec_summary = ticker_obj.recommendations_summary
                    # Check if summary data exists
                    if rec_summary is not None and not rec_summary.empty:
                        # Get the most recent period's data (first row)
                        latest = rec_summary.iloc[0]
                        # Count buy-side recommendations
                        buy_count = int(latest.get("strongBuy", 0)) + int(latest.get("buy", 0))
                        # Count hold recommendations
                        hold_count = int(latest.get("hold", 0))
                        # Count sell-side recommendations
                        sell_count = int(latest.get("sell", 0)) + int(latest.get("strongSell", 0))
                        # Determine consensus based on which category has the most
                        if sell_count > buy_count and sell_count > hold_count:
                            # Set consensus to sell
                            consensus = "sell"
                        # Check if buy recommendations dominate
                        elif buy_count > sell_count and buy_count > hold_count:
                            # Set consensus to buy
                            consensus = "buy"
                        # Otherwise default to hold
                        else:
                            # Set consensus to hold
                            consensus = "hold"
                # Catch errors accessing recommendations summary
                except Exception:
                    # Leave consensus as unknown
                    pass
                # Store the analyst consensus
                evidence["analyst_consensus"] = consensus
                # Try to count downgrades from the full recommendations history
                try:
                    # Check for common downgrade column patterns
                    if "To Grade" in recs.columns and "Action" in recs.columns:
                        # Loop through recommendation rows to count downgrades
                        for _, row in recs.iterrows():
                            # Check if this recommendation was a downgrade
                            action = str(row.get("Action", "")).lower()
                            # If the action contains "down", count it as a downgrade
                            if "down" in action:
                                # Increment the downgrade counter
                                downgrade_count += 1
                # Catch errors counting downgrades
                except Exception:
                    # Leave default value
                    pass
                # Store the downgrade count
                evidence["recent_downgrades"] = downgrade_count
        # Catch any errors accessing recommendations
        except Exception:
            # Leave default values
            pass

        # --- Price performance ---
        # Try to fetch 6-month price history
        try:
            # Get 6 months of daily closing prices
            hist = ticker_obj.history(period="6mo")
            # Check if we got valid price history
            if hist is not None and not hist.empty and len(hist) > 1:
                # Get the most recent closing price
                latest_price = hist["Close"].iloc[-1]
                # Get the closing price from 6 months ago (first data point)
                price_6m_ago = hist["Close"].iloc[0]
                # Calculate 6-month return
                if price_6m_ago > 0:
                    # Compute the percentage return over 6 months
                    evidence["price_return_6m"] = round((latest_price - price_6m_ago) / price_6m_ago, 4)
                # Calculate 3-month return (approximately 63 trading days)
                if len(hist) > 63:
                    # Get the closing price from approximately 3 months ago
                    price_3m_ago = hist["Close"].iloc[-63]
                    # Check for valid price
                    if price_3m_ago > 0:
                        # Compute the percentage return over 3 months
                        evidence["price_return_3m"] = round((latest_price - price_3m_ago) / price_3m_ago, 4)
                # If less than 63 days of data, use the midpoint as a rough proxy
                elif len(hist) > 2:
                    # Use the midpoint of available data as a rough 3-month proxy
                    mid_idx = len(hist) // 2
                    # Get the price at the midpoint
                    price_mid = hist["Close"].iloc[mid_idx]
                    # Check for valid price
                    if price_mid > 0:
                        # Compute the return from midpoint to now
                        evidence["price_return_3m"] = round((latest_price - price_mid) / price_mid, 4)
        # Catch any errors accessing price history
        except Exception:
            # Leave default None values for price returns
            pass

    # Catch any top-level errors from yfinance (e.g., ticker not found)
    except Exception as e:
        # Print a warning about the yfinance failure
        print(f"    Warning: yfinance lookup failed for {yf_ticker}: {e}")
        # Return the evidence with defaults
        return evidence

    # Compute the evidence strength score from the structured data
    evidence["evidence_strength"] = compute_evidence_strength(evidence)
    # Auto-generate the evidence summary as a plain English string
    evidence["evidence_summary"] = build_evidence_summary(evidence)
    # Return the complete evidence dictionary
    return evidence


# Define a function to compute an evidence strength score (1-5) from structured yfinance data
def compute_evidence_strength(evidence):
    # Initialize the score at zero
    score = 0
    # Add 1 point if the company missed earnings at least once in the last 4 quarters
    if evidence.get("earnings_misses_last_4q", 0) >= 1:
        # Increment score for earnings misses
        score += 1
    # Add 1 point if revenue is trending downward
    if evidence.get("revenue_trend") == "declining":
        # Increment score for declining revenue
        score += 1
    # Add 1 point if there have been 2 or more analyst downgrades
    if evidence.get("recent_downgrades", 0) >= 2:
        # Increment score for analyst downgrades
        score += 1
    # Add 1 point if the stock has dropped more than 15% in 6 months
    if evidence.get("price_return_6m") is not None and evidence["price_return_6m"] < -0.15:
        # Increment score for poor price performance
        score += 1
    # Add 1 point if analyst consensus is sell or underweight
    if evidence.get("analyst_consensus") in ("sell", "underweight"):
        # Increment score for bearish consensus
        score += 1
    # Cap the score at a maximum of 5
    return min(score, 5)


# Define a function to auto-generate a plain English evidence summary from structured data
def build_evidence_summary(evidence):
    # Initialize a list to collect summary sentences
    parts = []
    # Add a sentence about earnings misses if any occurred
    if evidence.get("earnings_misses_last_4q", 0) > 0:
        # Build the earnings miss sentence
        parts.append(f"Missed earnings {evidence['earnings_misses_last_4q']} of last 4 quarters.")
    # Add a sentence about revenue trend if it's declining
    if evidence.get("revenue_trend") == "declining":
        # Build the revenue trend sentence
        parts.append("Revenue declining QoQ.")
    # Add a sentence about revenue trend if it's growing (positive signal)
    elif evidence.get("revenue_trend") == "growing":
        # Build the positive revenue sentence
        parts.append("Revenue growing QoQ.")
    # Add a sentence about analyst downgrades if any occurred
    if evidence.get("recent_downgrades", 0) > 0:
        # Build the downgrade sentence
        parts.append(f"{evidence['recent_downgrades']} analyst downgrade(s) in recent months.")
    # Add a sentence about analyst consensus
    if evidence.get("analyst_consensus") not in ("unknown", None):
        # Build the consensus sentence
        parts.append(f"Analyst consensus: {evidence['analyst_consensus']}.")
    # Add a sentence about 6-month price performance if available
    if evidence.get("price_return_6m") is not None:
        # Format the return as a percentage
        pct = round(evidence["price_return_6m"] * 100, 1)
        # Build the price performance sentence
        parts.append(f"Stock {'up' if pct >= 0 else 'down'} {abs(pct)}% in 6 months.")
    # If we have no data points at all, return the default message
    if not parts:
        # Return the no-data message
        return "No financial data available"
    # Join all the sentences into a single summary string
    return " ".join(parts)


# Define a function to fetch qualitative evidence using Claude + web search (Stage 3b)
def fetch_qualitative_evidence(client, ticker, company_name, startup_name, target_market, evidence_summary):
    # Build the prompt for qualitative research with web search
    prompt = f"""Research competitive pressure on {company_name} ({ticker}) from {startup_name} in the {target_market} space.

The company's financials already show: {evidence_summary}

Look for:
- Management commentary about competitive threats in recent earnings calls
- News about losing customers or contracts to the startup or similar competitors
- Industry reports about market share shifts in this space

Return ONLY a JSON object (no markdown fences):
{{
  "ticker": "{ticker}",
  "qualitative_findings": "2-3 sentence summary of what you found",
  "competitive_pressure_confirmed": true
}}"""
    # Call the API with web search enabled
    response_text = call_anthropic_api_with_search(client, prompt)
    # If the API call failed, return a default result
    if response_text is None:
        # Return an empty qualitative result
        return {"ticker": ticker, "qualitative_findings": "API call failed", "competitive_pressure_confirmed": False}
    # Try to parse the response as JSON
    try:
        # Strip whitespace from the response
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
        result = json.loads(cleaned)
        # Return the parsed result
        return result
    # Catch JSON parsing errors
    except (json.JSONDecodeError, ValueError) as e:
        # Print a warning about the parse failure
        print(f"    Warning: Could not parse qualitative response for {ticker}: {e}")
        # Return a default result with the raw response text truncated
        return {"ticker": ticker, "qualitative_findings": response_text[:300], "competitive_pressure_confirmed": False}


# Define a function to cross-reference threat pairs against portfolio holdings (Stage 4)
def cross_reference_holdings(threat_pairs, evidence_by_ticker, holdings):
    # Create a lookup from stripped ticker to holding data for matching
    holdings_lookup = {}
    # Loop through each holding to build the lookup
    for h in holdings:
        # Get the raw ticker
        raw_ticker = h["ticker"]
        # Strip the market suffix for matching
        stripped = strip_ticker_suffix(raw_ticker)
        # Store the holding data under the stripped ticker
        holdings_lookup[stripped] = h
        # Also store under the raw ticker for exact matches
        holdings_lookup[raw_ticker] = h
    # Initialize the list for threat pairs that match holdings
    holdings_view = []
    # Initialize the list for all threat pairs (broad market view)
    broad_view = []
    # Loop through each threat pair to classify it
    for pair in threat_pairs:
        # Get the ticker of the threatened public company
        ticker = pair.get("ticker", "")
        # Strip the suffix for matching
        stripped_ticker = strip_ticker_suffix(ticker)
        # Get the financial evidence for this ticker if it exists
        evidence = evidence_by_ticker.get(ticker, {})
        # Build the combined record with threat data and evidence
        record = {
            "startup_name": pair.get("startup_name", ""),
            "startup_description": pair.get("startup_description", ""),
            "target_market": pair.get("target_market", ""),
            "ticker": ticker,
            "company_name": pair.get("company_name", ""),
            "threat_type": pair.get("threat_type", ""),
            "threat_score": pair.get("threat_score", 0),
            "reasoning": pair.get("reasoning", ""),
            "evidence_strength": evidence.get("evidence_strength", 0),
            "evidence_summary": evidence.get("evidence_summary", "No data"),
            "qualitative_findings": evidence.get("qualitative_findings", ""),
        }
        # Add this record to the broad market view (always)
        broad_view.append(record)
        # Check if this ticker matches any of our holdings
        if ticker in holdings_lookup or stripped_ticker in holdings_lookup:
            # Get the matching holding record
            holding = holdings_lookup.get(ticker, holdings_lookup.get(stripped_ticker, {}))
            # Create a copy of the record for the holdings view so we don't mutate the broad view
            holdings_record = dict(record)
            # Add the holding side (long/short) to the holdings record
            holdings_record["holding_side"] = holding.get("side", "long")
            # Add the holding's portfolio name
            holdings_record["holding_name"] = holding.get("name", "")
            # Add this record to the holdings-filtered view
            holdings_view.append(holdings_record)
    # Print the cross-reference results
    print(f"  Holdings matches: {len(holdings_view)} threat pairs match current positions")
    # Print the broad market count
    print(f"  Broad market: {len(broad_view)} total threat pairs")
    # Return both views
    return holdings_view, broad_view


# Define a function to generate a markdown threat digest report
def generate_markdown_digest(threat_records, portfolio_name, output_dir, report_type="market"):
    # Get today's date formatted as YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    # Construct the output file name based on report type (holdings or market)
    filename = f"threat_digest_{report_type}_{today}.md"
    # Build the full output file path
    output_path = os.path.join(output_dir, filename)
    # Create the output directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)
    # Sort threat records by threat score descending so the most severe appear first
    sorted_records = sorted(threat_records, key=lambda x: x.get("threat_score", 0), reverse=True)
    # Count the total number of threat pairs
    total_threats = len(sorted_records)
    # Count unique startups in this report
    unique_startups = len(set(r.get("startup_name", "") for r in sorted_records))
    # Count unique threatened public companies
    unique_targets = len(set(r.get("ticker", "") for r in sorted_records))
    # Initialize a list to build the markdown content line by line
    lines = []
    # Build the report label based on whether this is the holdings or market view
    report_label = "Holdings" if report_type == "holdings" else "Broad Market"
    # Add the report title with the portfolio name and report type
    lines.append(f"# Disruption Monitor — {portfolio_name} ({report_label})")
    # Add the report date
    lines.append(f"\n**Date:** {today}\n")
    # Add the summary section header
    lines.append("## Summary\n")
    # Add the count of threat pairs identified
    lines.append(f"- **Threat pairs identified:** {total_threats}")
    # Add the count of unique startups
    lines.append(f"- **Unique startups:** {unique_startups}")
    # Add the count of unique threatened companies
    lines.append(f"- **Public companies threatened:** {unique_targets}")
    # If this is a holdings report, add short position info
    if report_type == "holdings":
        # Count threats to short positions (portfolio-positive)
        short_threats = sum(1 for r in sorted_records if r.get("holding_side") == "short")
        # Add the short position count
        lines.append(f"- **Short position threats (portfolio-positive):** {short_threats}")
    # Add a blank line before the detailed findings
    lines.append("")
    # Add the detailed findings section header
    lines.append("## Threat Pairs (by severity)\n")
    # Loop through each threat record to add it to the report
    for record in sorted_records:
        # Get the numeric threat score
        score = record.get("threat_score", 0)
        # Map numeric scores to human-readable severity labels
        severity_labels = {1: "Minor", 2: "Emerging", 3: "Moderate", 4: "Significant", 5: "Severe"}
        # Look up the severity label for this score
        severity = severity_labels.get(score, "Unknown")
        # Get the startup name
        startup = record.get("startup_name", "Unknown Startup")
        # Get the target company's ticker
        ticker = record.get("ticker", "???")
        # Get the target company's name
        company_name = record.get("company_name", "Unknown")
        # Add the threat pair header as a level-3 heading
        lines.append(f"### {startup} → {company_name} ({ticker})")
        # Add the threat score and severity
        lines.append(f"- **Threat Score:** {score}/5 ({severity})")
        # Add the threat type
        lines.append(f"- **Threat Type:** {record.get('threat_type', 'N/A')}")
        # Add the target market
        lines.append(f"- **Target Market:** {record.get('target_market', 'N/A')}")
        # Add the reasoning
        lines.append(f"- **Reasoning:** {record.get('reasoning', 'No reasoning provided')}")
        # Get the financial evidence summary
        evidence_summary = record.get("evidence_summary", "")
        # Check if there's evidence data to display
        if evidence_summary and evidence_summary != "No data":
            # Get the evidence strength score
            ev_strength = record.get("evidence_strength", 0)
            # Add the evidence line
            lines.append(f"- **Financial Evidence ({ev_strength}/5):** {evidence_summary}")
        # Get qualitative findings if available
        qual = record.get("qualitative_findings", "")
        # Check if there are qualitative findings to display
        if qual:
            # Add the qualitative findings line
            lines.append(f"- **Qualitative:** {qual}")
        # If this is a holdings report and the position is short, add a portfolio impact note
        if report_type == "holdings" and record.get("holding_side") == "short":
            # Add the portfolio-positive note for short positions
            lines.append("- **Portfolio Impact:** POSITIVE — threat to a short position")
        # Add a blank line between entries for readability
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
    print(f"  {report_label} digest written to: {output_path}")
    # Return the output file path
    return output_path


# Define a function to generate the combined CSV of all threat pairs and evidence
def generate_threats_csv(threat_records, companies_lookup, output_dir):
    # Get today's date formatted as YYYY-MM-DD
    today = datetime.now().strftime("%Y-%m-%d")
    # Construct the full output file path
    output_path = os.path.join(output_dir, f"threats_{today}.csv")
    # Create the output directory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)
    # Define the column headers for the CSV file
    fieldnames = [
        "startup_name",
        "target_market",
        "threatened_ticker",
        "threatened_company",
        "threat_score",
        "threat_type",
        "reasoning",
        "evidence_strength",
        "evidence_summary",
        "qualitative_findings",
        "holding_side",
        "in_portfolio",
        "startup_revenue",
        "startup_growth",
        "startup_funding",
        "date_identified",
    ]
    # Open the CSV file for writing
    with open(output_path, "w", newline="") as f:
        # Create a DictWriter with the defined column headers
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        # Write the header row to the CSV
        writer.writeheader()
        # Loop through each threat record to write one row per threat pair
        for record in threat_records:
            # Get the startup name for looking up additional data from the CSV source
            startup_name = record.get("startup_name", "")
            # Look up this startup's data from the private companies for enrichment
            startup_data = companies_lookup.get(startup_name, {})
            # Determine if this threat pair is in the portfolio
            in_portfolio = "yes" if record.get("holding_side") else "no"
            # Build the complete row with threat data, evidence, and enrichment data
            row = {
                "startup_name": startup_name,
                "target_market": record.get("target_market", ""),
                "threatened_ticker": record.get("ticker", ""),
                "threatened_company": record.get("company_name", ""),
                "threat_score": record.get("threat_score", ""),
                "threat_type": record.get("threat_type", ""),
                "reasoning": record.get("reasoning", ""),
                "evidence_strength": record.get("evidence_strength", ""),
                "evidence_summary": record.get("evidence_summary", ""),
                "qualitative_findings": record.get("qualitative_findings", ""),
                "holding_side": record.get("holding_side", ""),
                "in_portfolio": in_portfolio,
                "startup_revenue": startup_data.get("revenue", ""),
                "startup_growth": startup_data.get("growth", ""),
                "startup_funding": startup_data.get("funding", ""),
                "date_identified": today,
            }
            # Write this row to the CSV file
            writer.writerow(row)
    # Print where the CSV was saved and how many rows were written
    print(f"  Threats CSV written to: {output_path} ({len(threat_records)} threat pairs)")
    # Return the output file path
    return output_path


# Define the main function that orchestrates the entire pipeline
def main():
    # Parse command-line arguments provided by the user
    args = parse_args()
    # Print a startup banner
    print("\n=== Disruption Monitor ===\n")

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
    # Build a lookup dictionary from company name to company data for enriching output
    companies_lookup = {c["company_name"]: c for c in companies}

    # ─── Stage 2: Claude API Threat Mapping ───
    # Print the stage header
    print(f"\n[Stage 2] Running startup → public company threat mapping...")
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
    # Calculate how many batches we need based on the startups-per-batch setting
    batch_size = args.startups_per_batch
    # Calculate the total number of batches using ceiling division
    total_batches = (len(companies) + batch_size - 1) // batch_size
    # Print the batch plan
    print(f"  Batching {len(companies)} startups into {total_batches} batch(es) of up to {batch_size}")
    # Initialize a master list to collect all threat mappings from all batches
    all_mappings = []
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
        # Build the threat mapping prompt for this batch
        prompt = build_threat_mapping_prompt(batch)
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
        mappings = parse_threat_mapping_response(response_text)
        # Print how many startups returned threat mappings in this batch
        if not args.dry_run:
            # Count startups with at least one threatened company
            active = sum(1 for m in mappings if m.get("threatened_companies"))
            # Display the mapping count
            print(f"    {active} startup(s) with identified threats")
        # Add this batch's mappings to the master list
        all_mappings.extend(mappings)

    # If this was a dry run, show a summary and exit without generating reports
    if args.dry_run:
        # Print a dry run completion message
        print(f"\n=== DRY RUN COMPLETE ===")
        # Show how many API calls would have been made
        print(f"Would have made {total_batches} threat mapping API call(s)")
        # Tell the user how to run for real
        print("Remove --dry-run to execute the API calls.")
        # Exit
        return

    # Flatten the mappings into individual threat pairs and deduplicate
    threat_pairs = []
    # Track seen (startup_name, ticker) pairs for deduplication
    seen_pairs = set()
    # Loop through each startup's mapping result
    for mapping in all_mappings:
        # Get the startup name from this mapping
        startup_name = mapping.get("startup_name", "")
        # Get the startup description
        startup_desc = mapping.get("startup_description", "")
        # Get the target market
        target_market = mapping.get("target_market", "")
        # Loop through each threatened company in this mapping
        for threat in mapping.get("threatened_companies", []):
            # Get the ticker of the threatened company
            ticker = threat.get("ticker", "")
            # Create a deduplication key from startup name and ticker
            dedup_key = (startup_name.lower(), ticker.upper())
            # Check if we've already seen this pair
            if dedup_key in seen_pairs:
                # Skip this duplicate pair
                continue
            # Add this pair to the seen set
            seen_pairs.add(dedup_key)
            # Build a flat threat pair record
            pair = {
                "startup_name": startup_name,
                "startup_description": startup_desc,
                "target_market": target_market,
                "ticker": ticker,
                "company_name": threat.get("company_name", ""),
                "threat_type": threat.get("threat_type", ""),
                "threat_score": threat.get("threat_score", 0),
                "reasoning": threat.get("reasoning", ""),
            }
            # Add this pair to the master list
            threat_pairs.append(pair)
    # Print the deduplication results
    print(f"\n  Total unique threat pairs: {len(threat_pairs)}")

    # ─── Stage 3: Financial Evidence Layer ───
    # Initialize an evidence dictionary keyed by ticker
    evidence_by_ticker = {}
    # Check if the user wants to skip the evidence stage
    if args.skip_evidence:
        # Print that evidence gathering is being skipped
        print(f"\n[Stage 3] Skipping financial evidence (--skip-evidence flag set)")
    # If not skipping, gather financial evidence
    else:
        # Print the stage header
        print(f"\n[Stage 3a] Gathering yfinance financial evidence...")
        # Check if yfinance is available
        if yf is None:
            # Print a warning that yfinance is not installed
            print("  Warning: yfinance not installed. Install with: pip install yfinance")
            # Print that evidence gathering will be skipped
            print("  Skipping financial evidence layer.")
        # If yfinance is available, proceed with data gathering
        else:
            # Collect all unique tickers from the threat pairs
            unique_tickers = list(set(pair["ticker"] for pair in threat_pairs if pair.get("ticker")))
            # Print how many tickers we need to look up
            print(f"  Looking up financial data for {len(unique_tickers)} unique tickers...")
            # Loop through each unique ticker to fetch evidence
            for i, ticker in enumerate(unique_tickers):
                # Print progress for every 10 tickers
                if (i + 1) % 10 == 0 or i == 0:
                    # Print the progress count
                    print(f"    Processing ticker {i + 1}/{len(unique_tickers)}: {ticker}")
                # Fetch the yfinance evidence for this ticker
                evidence = fetch_yfinance_evidence(ticker)
                # Store the evidence in the lookup dictionary
                evidence_by_ticker[ticker] = evidence
                # Add a 0.5-second delay between tickers to avoid rate limiting
                if i < len(unique_tickers) - 1:
                    # Pause to be respectful of yfinance's rate limits
                    time.sleep(0.5)
            # Count how many tickers had financial red flags
            with_evidence = sum(1 for e in evidence_by_ticker.values() if e.get("evidence_strength", 0) > 0)
            # Print how many tickers had financial red flags
            print(f"  {with_evidence} of {len(unique_tickers)} tickers have financial red flags (evidence_strength > 0)")

        # ─── Stage 3b: Qualitative Overlay (optional) ───
        # Check if the user requested the qualitative overlay
        if args.qualitative:
            # Print the stage header
            print(f"\n[Stage 3b] Running Claude + web search qualitative overlay...")
            # Filter to tickers with evidence_strength >= 2 (don't waste API calls on clean companies)
            qual_tickers = [
                ticker for ticker, ev in evidence_by_ticker.items()
                if ev.get("evidence_strength", 0) >= 2
            ]
            # Print how many tickers qualify for qualitative research
            print(f"  {len(qual_tickers)} tickers qualify (evidence_strength >= 2)")
            # Loop through qualifying tickers to fetch qualitative evidence
            for i, ticker in enumerate(qual_tickers):
                # Find the first threat pair for this ticker to get context
                context_pair = next((p for p in threat_pairs if p["ticker"] == ticker), None)
                # Skip if we can't find context
                if context_pair is None:
                    # Continue to the next ticker
                    continue
                # Print progress
                print(f"    [{i + 1}/{len(qual_tickers)}] Researching {ticker} ({context_pair.get('company_name', '')})...")
                # Fetch qualitative evidence from Claude + web search
                qual_result = fetch_qualitative_evidence(
                    client,
                    ticker,
                    context_pair.get("company_name", ""),
                    context_pair.get("startup_name", ""),
                    context_pair.get("target_market", ""),
                    evidence_by_ticker[ticker].get("evidence_summary", ""),
                )
                # Merge the qualitative findings into the evidence dictionary
                evidence_by_ticker[ticker]["qualitative_findings"] = qual_result.get("qualitative_findings", "")
                # Store whether competitive pressure was confirmed
                evidence_by_ticker[ticker]["competitive_pressure_confirmed"] = qual_result.get("competitive_pressure_confirmed", False)
                # Add a 2-second delay between API calls to respect rate limits
                if i < len(qual_tickers) - 1:
                    # Pause to respect the API rate limit
                    time.sleep(2.0)
        # If qualitative flag is not set, skip this stage
        else:
            # Print that qualitative overlay is being skipped
            print(f"\n[Stage 3b] Skipping qualitative overlay (use --qualitative to enable)")

    # ─── Stage 4: Holdings Cross-Reference ───
    # Initialize variables for the two report views
    holdings_view = []
    # Initialize the broad market view
    broad_view = []
    # Check if we should skip the holdings filter
    if args.broad_only:
        # Print that holdings filtering is being skipped
        print(f"\n[Stage 4] Skipping holdings filter (--broad-only flag set)")
        # Build the broad view directly from threat pairs with evidence
        for pair in threat_pairs:
            # Get the evidence for this ticker
            evidence = evidence_by_ticker.get(pair["ticker"], {})
            # Start with a copy of the threat pair data
            record = dict(pair)
            # Add evidence strength to the record
            record["evidence_strength"] = evidence.get("evidence_strength", 0)
            # Add the evidence summary
            record["evidence_summary"] = evidence.get("evidence_summary", "No data")
            # Add qualitative findings if available
            record["qualitative_findings"] = evidence.get("qualitative_findings", "")
            # Add to the broad market view
            broad_view.append(record)
    # If not broad-only, read holdings and cross-reference
    else:
        # Print the stage header
        print(f"\n[Stage 4] Cross-referencing with portfolio holdings...")
        # Read the portfolio holdings from the Excel file
        holdings = read_holdings(args.holdings)
        # Perform the cross-reference to split into two views
        holdings_view, broad_view = cross_reference_holdings(threat_pairs, evidence_by_ticker, holdings)

    # ─── Stage 5: Output Reports ───
    # Print the stage header
    print(f"\n[Stage 5] Generating output reports...")
    # Generate the broad market digest (always)
    market_md_path = generate_markdown_digest(
        broad_view, args.portfolio_name, args.output_dir, report_type="market"
    )
    # Initialize the holdings markdown path variable
    holdings_md_path = None
    # Generate the holdings digest if we have holdings data
    if not args.broad_only and holdings_view:
        # Generate the holdings-filtered digest
        holdings_md_path = generate_markdown_digest(
            holdings_view, args.portfolio_name, args.output_dir, report_type="holdings"
        )
    # Generate the combined CSV with all threat pairs
    csv_path = generate_threats_csv(broad_view, companies_lookup, args.output_dir)

    # Print the final summary banner
    print(f"\n=== Analysis Complete ===")
    # Print the total number of unique threat pairs
    print(f"  Threat pairs: {len(broad_view)}")
    # Print the holdings match count if applicable
    if not args.broad_only:
        # Print how many threat pairs match holdings
        print(f"  Holdings matches: {len(holdings_view)}")
    # Print the path to the market digest
    print(f"  Market digest: {market_md_path}")
    # Print the path to the holdings digest if it was generated
    if holdings_md_path:
        # Print the holdings digest path
        print(f"  Holdings digest: {holdings_md_path}")
    # Print the path to the threats CSV
    print(f"  Threats CSV: {csv_path}")

    # Check if the user wants to send results via email
    if args.email:
        # Print the email step
        print(f"\n[Email] Sending digest email...")
        # Import the emailer module
        from emailer import load_config, send_email as send_threat_email
        # Load the email config
        email_config = load_config(args.config)
        # Determine which markdown report to email (holdings if available, otherwise market)
        md_to_email = holdings_md_path if holdings_md_path else market_md_path
        # Send the email with the CSV and markdown attachments
        send_threat_email(email_config, csv_path, md_to_email, test_mode=args.test)


# Run the main function only if this script is executed directly (not imported)
if __name__ == "__main__":
    # Call main to start the program
    main()
