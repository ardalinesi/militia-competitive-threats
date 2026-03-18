#!/usr/bin/env python3
"""
Email module for the Competitive Threat Tracker.
Sends weekly digest emails with threat CSV attachment and HTML summary.
"""

# Import smtplib for sending emails via SMTP
import smtplib

# Import os for reading environment variables and file paths
import os

# Import csv for reading the threats CSV file
import csv

# Import datetime for date formatting in emails
from datetime import datetime

# Import MIME modules for constructing multipart emails with attachments
from email.mime.multipart import MIMEMultipart

# Import MIMEText for the HTML email body
from email.mime.text import MIMEText

# Import MIMEBase for binary file attachments
from email.mime.base import MIMEBase

# Import encoders for base64 encoding of attachments
from email import encoders

# Import yaml for reading the config file
import yaml


# Define a function to load the config.yaml file
def load_config(config_path="config.yaml"):
    # Open the config file for reading
    with open(config_path, "r") as f:
        # Parse the YAML content and return it as a dictionary
        config = yaml.safe_load(f)
    # Return the parsed config
    return config


# Define a function to read threats from the CSV file and return them as a list of dicts
def read_threats_csv(csv_path):
    # Check if the CSV file exists
    if not os.path.exists(csv_path):
        # Print a warning and return empty list
        print(f"  Warning: Threats CSV not found at {csv_path}")
        # Return an empty list
        return []
    # Open the CSV file for reading
    with open(csv_path, "r") as f:
        # Create a DictReader to parse each row as a dictionary
        reader = csv.DictReader(f)
        # Read all rows into a list
        threats = list(reader)
    # Return the list of threat dictionaries
    return threats


# Define a function to build the HTML email body from the threats data
def build_email_html(threats, portfolio_name, date_str):
    # Start the HTML document with inline CSS styling
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 14px; color: #333; }}
            h1 {{ color: #1a1a2e; font-size: 22px; }}
            h2 {{ color: #16213e; font-size: 18px; margin-top: 24px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
            th {{ background-color: #4472C4; color: white; padding: 8px 12px; text-align: left; font-size: 13px; }}
            td {{ padding: 6px 12px; border-bottom: 1px solid #ddd; font-size: 13px; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .score-1 {{ color: #666; }}
            .score-2 {{ color: #b8860b; }}
            .score-3 {{ color: #e67e00; font-weight: bold; }}
            .score-4 {{ color: #d32f2f; font-weight: bold; }}
            .score-5 {{ color: #b71c1c; font-weight: bold; }}
            .short-tag {{ background-color: #e8f5e9; color: #2e7d32; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold; }}
            .long-tag {{ background-color: #fff3e0; color: #e65100; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
            .summary {{ background-color: #f5f5f5; padding: 12px 16px; border-radius: 6px; margin: 12px 0; }}
            .footer {{ color: #999; font-size: 11px; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <h1>Competitive Threat Digest &mdash; {portfolio_name}</h1>
        <p><strong>Date:</strong> {date_str}</p>
    """
    # Add the summary section with threat counts
    total_threats = len(threats)
    # Count unique holdings that have threats
    unique_holdings = len(set(t.get("holding_ticker", "") for t in threats))
    # Count threats to short positions (portfolio-positive)
    short_threats = sum(1 for t in threats if t.get("holding_side") == "short")
    # Build the summary box
    html += f"""
        <div class="summary">
            <strong>Total threats identified:</strong> {total_threats} &nbsp;|&nbsp;
            <strong>Holdings affected:</strong> {unique_holdings} &nbsp;|&nbsp;
            <strong>Short position threats (portfolio-positive):</strong> {short_threats}
        </div>
    """
    # Check if there are any threats to display
    if threats:
        # Add the threats table header
        html += """
        <h2>Identified Threats</h2>
        <table>
            <tr>
                <th>Holding</th>
                <th>Side</th>
                <th>Threat Company</th>
                <th>Score</th>
                <th>Type</th>
                <th>Reasoning</th>
                <th>Threat Growth</th>
                <th>Threat Funding</th>
            </tr>
        """
        # Loop through each threat to add a table row
        for t in threats:
            # Get the threat score for CSS class assignment
            score = t.get("threat_score", "")
            # Map the score to a severity label
            severity_map = {"1": "Minor", "2": "Emerging", "3": "Moderate", "4": "Significant", "5": "Severe"}
            # Get the severity label for this score
            severity = severity_map.get(str(score), "")
            # Determine the CSS class for the score color
            score_class = f"score-{score}" if str(score) in "12345" else ""
            # Determine the side tag (short = green/positive, long = orange/warning)
            side = t.get("holding_side", "long")
            # Build the side tag HTML
            if side == "short":
                # Short positions: threats are portfolio-positive
                side_html = '<span class="short-tag">SHORT &#x2714;</span>'
            else:
                # Long positions: threats are a concern
                side_html = '<span class="long-tag">LONG</span>'
            # Build the holding display name
            holding = f"{t.get('holding_name', '')} ({t.get('holding_ticker', '')})"
            # Add this threat as a table row
            html += f"""
            <tr>
                <td>{holding}</td>
                <td>{side_html}</td>
                <td><strong>{t.get('threat_company', '')}</strong></td>
                <td class="{score_class}">{score}/5 ({severity})</td>
                <td>{t.get('threat_type', '')}</td>
                <td>{t.get('reasoning', '')}</td>
                <td>{t.get('threat_growth', '') + '%' if t.get('threat_growth') else 'N/A'}</td>
                <td>{t.get('threat_funding', '') if t.get('threat_funding') else 'N/A'}</td>
            </tr>
            """
        # Close the table
        html += "</table>"
    # If no threats were found
    else:
        # Add a no-threats message
        html += "<p>No competitive threats identified this week.</p>"
    # Add the attachment note and footer
    html += """
        <p style="margin-top: 16px;"><em>See attached CSV for full details.</em></p>
        <p class="footer">Generated by Competitive Threat Tracker</p>
    </body>
    </html>
    """
    # Return the complete HTML string
    return html


# Define the main function to send the threat digest email
def send_email(config, csv_path, md_path, test_mode=False):
    # Read SMTP credentials from environment variables
    smtp_host = os.environ.get("SMTP_HOST", "")
    # Read the SMTP port, defaulting to 587 for TLS
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    # Read the SMTP username
    smtp_user = os.environ.get("SMTP_USER", "")
    # Read the SMTP password
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    # Check if SMTP credentials are configured
    if not smtp_host or not smtp_user or not smtp_password:
        # Print an error about missing SMTP config
        print("  Error: SMTP credentials not set. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD env vars.")
        # Return without sending
        return False
    # Build the recipient list based on test mode
    recipients = [config["email_to_always"]]
    # If not in test mode, add the production recipients
    if not test_mode:
        # Loop through each production recipient
        for addr in config.get("email_to_production", []):
            # Add this recipient to the list
            recipients.append(addr)
        # Print the full recipient list
        print(f"  Sending to: {', '.join(recipients)}")
    # If in test mode, only send to ardal
    else:
        # Print test mode message
        print(f"  [TEST MODE] Sending only to: {recipients[0]}")
    # Get today's date for the email subject
    today = datetime.now().strftime("%Y-%m-%d")
    # Build the email subject line
    subject = f"{config.get('email_subject', 'Weekly Competitive Threat Digest')} — {today}"
    # Add test mode prefix if applicable
    if test_mode:
        # Prepend [TEST] to the subject
        subject = f"[TEST] {subject}"
    # Read the threats from the CSV file
    threats = read_threats_csv(csv_path)
    # Build the HTML email body
    portfolio_name = config.get("portfolio_name", "Portfolio")
    # Generate the HTML content from the threats data
    html_body = build_email_html(threats, portfolio_name, today)
    # Create the MIME multipart message
    msg = MIMEMultipart()
    # Set the From header
    msg["From"] = f"{config.get('email_from_name', 'Threat Tracker')} <{smtp_user}>"
    # Set the To header (comma-separated for display)
    msg["To"] = ", ".join(recipients)
    # Set the Subject header
    msg["Subject"] = subject
    # Attach the HTML body
    msg.attach(MIMEText(html_body, "html"))
    # Attach the threats CSV file if it exists
    if os.path.exists(csv_path):
        # Open the CSV file in binary mode for attachment
        with open(csv_path, "rb") as f:
            # Create a MIME base attachment object
            attachment = MIMEBase("application", "octet-stream")
            # Read the file content into the attachment
            attachment.set_payload(f.read())
        # Encode the attachment as base64
        encoders.encode_base64(attachment)
        # Set the filename header for the attachment
        csv_filename = os.path.basename(csv_path)
        # Set the Content-Disposition header with the filename
        attachment.add_header("Content-Disposition", f"attachment; filename={csv_filename}")
        # Attach the file to the email message
        msg.attach(attachment)
    # Also attach the markdown digest if it exists
    if md_path and os.path.exists(md_path):
        # Open the markdown file in binary mode for attachment
        with open(md_path, "rb") as f:
            # Create a MIME base attachment object for the markdown
            md_attachment = MIMEBase("application", "octet-stream")
            # Read the file content into the attachment
            md_attachment.set_payload(f.read())
        # Encode the attachment as base64
        encoders.encode_base64(md_attachment)
        # Set the filename header for the markdown attachment
        md_filename = os.path.basename(md_path)
        # Set the Content-Disposition header with the filename
        md_attachment.add_header("Content-Disposition", f"attachment; filename={md_filename}")
        # Attach the markdown file to the email message
        msg.attach(md_attachment)
    # Try to send the email via SMTP
    try:
        # Connect to the SMTP server
        server = smtplib.SMTP(smtp_host, smtp_port)
        # Initiate TLS encryption
        server.starttls()
        # Authenticate with the SMTP server
        server.login(smtp_user, smtp_password)
        # Send the email to all recipients
        server.sendmail(smtp_user, recipients, msg.as_string())
        # Close the SMTP connection
        server.quit()
        # Print success message
        print(f"  Email sent successfully to {len(recipients)} recipient(s)")
        # Return True to indicate success
        return True
    # Catch any SMTP errors
    except Exception as e:
        # Print the error details
        print(f"  Error sending email: {e}")
        # Return False to indicate failure
        return False
