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


# Define a function to build the HTML email body from the classification data
def build_email_html(startups, portfolio_name, date_str):
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
            .ai-core {{ background-color: #e3f2fd; color: #1565c0; padding: 2px 6px; border-radius: 3px; font-size: 11px; font-weight: bold; }}
            .ai-significant {{ background-color: #f3e5f5; color: #7b1fa2; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
            .ai-moderate {{ color: #666; font-size: 11px; }}
            .ai-minimal {{ color: #999; font-size: 11px; }}
            .strategy-tag {{ background-color: #fff3e0; color: #e65100; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
            .summary {{ background-color: #f5f5f5; padding: 12px 16px; border-radius: 6px; margin: 12px 0; }}
            .footer {{ color: #999; font-size: 11px; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <h1>Startup Intelligence Report &mdash; {portfolio_name}</h1>
        <p><strong>Date:</strong> {date_str}</p>
    """
    # Add the summary section with classification counts
    total = len(startups)
    # Count unique industries from the CSV data
    unique_industries = len(set(t.get("industry", "") for t in startups))
    # Count AI-core startups
    ai_core = sum(1 for t in startups if t.get("ai_dependency") == "core")
    # Build the summary box
    html += f"""
        <div class="summary">
            <strong>Startups classified:</strong> {total} &nbsp;|&nbsp;
            <strong>Industries:</strong> {unique_industries} &nbsp;|&nbsp;
            <strong>AI-core startups:</strong> {ai_core}
        </div>
    """
    # Check if there are any startups to display
    if startups:
        # Add the classification table header
        html += """
        <h2>Startup Classifications</h2>
        <table>
            <tr>
                <th>Startup</th>
                <th>Industry / Subsector</th>
                <th>Strategy</th>
                <th>Product/Service</th>
                <th>TAM</th>
                <th>AI Dependency</th>
                <th>Competitive Advantage</th>
                <th>Est. ARR</th>
                <th>Employee Growth (%)</th>
                <th>Funding</th>
            </tr>
        """
        # Loop through each startup to add a table row
        for t in startups:
            # Get the startup name
            name = t.get("startup_name", "")
            # Get the industry and subsector
            industry = t.get("industry", "")
            # Get the subsector
            subsector = t.get("subsector", "")
            # Build the industry display string
            industry_display = f"{industry}<br><small>{subsector}</small>" if subsector else industry
            # Get the strategy and build a styled tag
            strategy = t.get("strategy", "")
            # Build the strategy tag HTML
            strategy_html = f'<span class="strategy-tag">{strategy}</span>' if strategy else ""
            # Get the product/service description, truncated for the table
            product = t.get("product_service", "")
            # Truncate long descriptions to 120 chars for the email table
            product_display = product[:120] + "..." if len(product) > 120 else product
            # Get the TAM estimate
            tam = t.get("tam_estimate", "")
            # Get the AI dependency level and build styled output
            ai_dep = t.get("ai_dependency", "")
            # Map AI dependency to a CSS class
            ai_class_map = {"core": "ai-core", "significant": "ai-significant", "moderate": "ai-moderate", "minimal": "ai-minimal"}
            # Get the appropriate CSS class
            ai_class = ai_class_map.get(ai_dep, "ai-minimal")
            # Build the AI dependency HTML
            ai_html = f'<span class="{ai_class}">{ai_dep}</span>' if ai_dep else ""
            # Get the competitive advantage, truncated
            moat = t.get("competitive_advantage", "")
            # Truncate long moat descriptions
            moat_display = moat[:100] + "..." if len(moat) > 100 else moat
            # Get the estimated ARR
            est_arr = t.get("estimated_arr", "")
            # Format ARR display
            arr_display = est_arr if est_arr else "N/A"
            # Get the growth rate (employee growth from Growjo)
            growth = t.get("growth", "")
            # Format growth display
            growth_display = growth if growth else "N/A"
            # Get the funding amount
            funding = t.get("funding", "")
            # Format funding display
            funding_display = funding if funding else "N/A"
            # Add this startup as a table row
            html += f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{industry_display}</td>
                <td>{strategy_html}</td>
                <td>{product_display}</td>
                <td>{tam}</td>
                <td>{ai_html}</td>
                <td>{moat_display}</td>
                <td>{arr_display}</td>
                <td>{growth_display}</td>
                <td>{funding_display}</td>
            </tr>
            """
        # Close the table
        html += "</table>"
    # If no startups were classified
    else:
        # Add a no-data message
        html += "<p>No startups classified this week.</p>"
    # Add the attachment note and footer
    html += """
        <p style="margin-top: 16px;"><em>See attached CSV for full classification details.</em></p>
        <p class="footer">Generated by Disruption Monitor</p>
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
