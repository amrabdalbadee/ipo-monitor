#!/usr/bin/env python3
"""
IPO Monitor - Daily Automation Script
Monitors U.S. IPOs and sends email alerts for large offerings (>$200M)

Features:
- Fetches today's IPOs from Finnhub API (free tier)
- Filters for offer amount > $200 million
- Sends email notification with qualifying tickers
- Designed for daily execution at 9:00 AM Dubai time (UTC+4)

Usage:
    python ipo_monitor.py

Environment Variables Required:
    FINNHUB_API_KEY     - Free API key from https://finnhub.io
    EMAIL_SENDER        - Your email address (Gmail recommended)
    EMAIL_PASSWORD      - App password (for Gmail, generate at https://myaccount.google.com/apppasswords)
    EMAIL_RECIPIENT     - Recipient email address (can be same as sender)
    SMTP_SERVER         - SMTP server (default: smtp.gmail.com)
    SMTP_PORT           - SMTP port (default: 587)
"""

import os
import sys
import json
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dataclasses import dataclass

# Try to import requests, provide helpful error if not available
try:
    import requests
except ImportError:
    print("Error: 'requests' module not found. Install it with: pip install requests")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
OFFER_AMOUNT_THRESHOLD = 200_000_000  # $200 million USD
DUBAI_TZ_OFFSET = timedelta(hours=4)  # UTC+4


@dataclass
class IPOData:
    """Represents an IPO event with relevant details"""
    symbol: str
    name: str
    ipo_date: str
    price: Optional[float]
    shares: Optional[int]
    offer_amount: Optional[float]
    exchange: Optional[str]
    
    @classmethod
    def from_finnhub(cls, data: dict) -> 'IPOData':
        """Create IPOData from Finnhub API response"""
        price = data.get('price')
        shares = data.get('numberOfShares')
        
        # Calculate offer amount (price × shares)
        offer_amount = None
        if price and shares:
            offer_amount = price * shares
        
        return cls(
            symbol=data.get('symbol', 'N/A'),
            name=data.get('name', 'Unknown'),
            ipo_date=data.get('date', ''),
            price=price,
            shares=shares,
            offer_amount=offer_amount,
            exchange=data.get('exchange', 'N/A')
        )
    
    def format_offer_amount(self) -> str:
        """Format offer amount in human-readable form"""
        if self.offer_amount is None:
            return "N/A"
        if self.offer_amount >= 1_000_000_000:
            return f"${self.offer_amount / 1_000_000_000:.2f}B"
        elif self.offer_amount >= 1_000_000:
            return f"${self.offer_amount / 1_000_000:.2f}M"
        else:
            return f"${self.offer_amount:,.2f}"


class FinnhubClient:
    """Client for Finnhub IPO Calendar API"""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Finnhub-Token': api_key
        })
    
    def get_ipo_calendar(self, from_date: str, to_date: str) -> list[dict]:
        """
        Fetch IPO calendar from Finnhub
        
        Args:
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            
        Returns:
            List of IPO events
        """
        endpoint = f"{self.BASE_URL}/calendar/ipo"
        params = {
            'from': from_date,
            'to': to_date
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('ipoCalendar', [])
        except requests.RequestException as e:
            logger.error(f"Failed to fetch IPO calendar: {e}")
            return []


class EmailNotifier:
    """Handles email notifications"""
    
    def __init__(
        self,
        sender: str,
        password: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587
    ):
        self.sender = sender
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
    
    def send_email(
        self,
        recipient: str,
        subject: str,
        body_html: str,
        body_text: str
    ) -> bool:
        """
        Send an email notification
        
        Args:
            recipient: Email recipient
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body content
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender
            msg['To'] = recipient
            
            # Attach both plain text and HTML versions
            part1 = MIMEText(body_text, 'plain')
            part2 = MIMEText(body_html, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, recipient, msg.as_string())
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


def get_today_date() -> str:
    """Get today's date in YYYY-MM-DD format (Dubai time)"""
    utc_now = datetime.utcnow()
    dubai_time = utc_now + DUBAI_TZ_OFFSET
    return dubai_time.strftime('%Y-%m-%d')


def filter_todays_large_ipos(ipos: list[IPOData], target_date: str) -> list[IPOData]:
    """
    Filter IPOs for today's date with offer amount > $200M
    
    Args:
        ipos: List of IPO data objects
        target_date: Target date in YYYY-MM-DD format
        
    Returns:
        Filtered list of qualifying IPOs
    """
    qualifying_ipos = []
    
    for ipo in ipos:
        # Check if IPO is for today
        if ipo.ipo_date != target_date:
            continue
        
        # Check if offer amount exceeds threshold
        if ipo.offer_amount and ipo.offer_amount > OFFER_AMOUNT_THRESHOLD:
            qualifying_ipos.append(ipo)
            logger.info(
                f"Found qualifying IPO: {ipo.symbol} - {ipo.name} "
                f"(Offer: {ipo.format_offer_amount()})"
            )
    
    return qualifying_ipos


def create_email_content(ipos: list[IPOData], date: str) -> tuple[str, str]:
    """
    Create email content for IPO notification
    
    Args:
        ipos: List of qualifying IPOs
        date: Report date
        
    Returns:
        Tuple of (HTML content, plain text content)
    """
    if not ipos:
        text = f"IPO Monitor Report - {date}\n\n"
        text += "No IPOs with offer amount > $200M scheduled for today.\n"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">📊 IPO Monitor Report - {date}</h2>
            <p style="color: #7f8c8d;">No IPOs with offer amount > $200M scheduled for today.</p>
            <hr style="border: 1px solid #ecf0f1;">
            <p style="font-size: 12px; color: #95a5a6;">
                This is an automated report from your IPO Monitor.
            </p>
        </body>
        </html>
        """
        return html, text
    
    # Build plain text version
    text = f"IPO Monitor Report - {date}\n"
    text += f"Found {len(ipos)} IPO(s) with offer amount > $200M\n"
    text += "=" * 50 + "\n\n"
    
    for ipo in ipos:
        text += f"Ticker: {ipo.symbol}\n"
        text += f"Company: {ipo.name}\n"
        text += f"IPO Date: {ipo.ipo_date}\n"
        text += f"Price: ${ipo.price:.2f}\n" if ipo.price else "Price: TBD\n"
        text += f"Shares: {ipo.shares:,}\n" if ipo.shares else "Shares: TBD\n"
        text += f"Offer Amount: {ipo.format_offer_amount()}\n"
        text += f"Exchange: {ipo.exchange}\n"
        text += "-" * 30 + "\n\n"
    
    # Build HTML version
    rows_html = ""
    for ipo in ipos:
        rows_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #ecf0f1;">
                <strong style="color: #2980b9; font-size: 16px;">{ipo.symbol}</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #ecf0f1;">{ipo.name}</td>
            <td style="padding: 12px; border-bottom: 1px solid #ecf0f1;">
                ${ipo.price:.2f} if ipo.price else 'TBD'
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #ecf0f1;">
                <strong style="color: #27ae60;">{ipo.format_offer_amount()}</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #ecf0f1;">{ipo.exchange}</td>
        </tr>
        """
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">📊 IPO Monitor Report - {date}</h2>
        <p style="background-color: #d4edda; padding: 15px; border-radius: 5px; color: #155724;">
            <strong>🔔 Alert:</strong> Found <strong>{len(ipos)}</strong> IPO(s) with offer amount > $200M today!
        </p>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead>
                <tr style="background-color: #3498db; color: white;">
                    <th style="padding: 12px; text-align: left;">Ticker</th>
                    <th style="padding: 12px; text-align: left;">Company</th>
                    <th style="padding: 12px; text-align: left;">Price</th>
                    <th style="padding: 12px; text-align: left;">Offer Amount</th>
                    <th style="padding: 12px; text-align: left;">Exchange</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        
        <hr style="border: 1px solid #ecf0f1; margin-top: 30px;">
        <p style="font-size: 12px; color: #95a5a6;">
            This is an automated report from your IPO Monitor.<br>
            Threshold: Offer Amount > $200,000,000
        </p>
    </body>
    </html>
    """
    
    return html, text


def main():
    """Main execution function"""
    logger.info("=" * 50)
    logger.info("IPO Monitor Starting...")
    logger.info("=" * 50)
    
    # Load configuration from environment variables
    # Note: Use `or` to handle empty strings from CI/CD systems
    finnhub_api_key = os.environ.get('FINNHUB_API_KEY') or None
    email_sender = os.environ.get('EMAIL_SENDER') or None
    email_password = os.environ.get('EMAIL_PASSWORD') or None
    email_recipient = os.environ.get('EMAIL_RECIPIENT') or email_sender
    smtp_server = os.environ.get('SMTP_PORT') or 'smtp.gmail.com'
    smtp_port = int(os.environ.get('SMTP_PORT') or '587')
    
    # Validate required environment variables
    missing_vars = []
    if not finnhub_api_key:
        missing_vars.append('FINNHUB_API_KEY')
    if not email_sender:
        missing_vars.append('EMAIL_SENDER')
    if not email_password:
        missing_vars.append('EMAIL_PASSWORD')
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables before running the script.")
        sys.exit(1)
    
    # Get today's date
    today = get_today_date()
    logger.info(f"Checking IPOs for date: {today}")
    
    # Initialize clients
    finnhub = FinnhubClient(finnhub_api_key)
    notifier = EmailNotifier(email_sender, email_password, smtp_server, smtp_port)
    
    # Fetch IPO calendar for today
    logger.info("Fetching IPO calendar from Finnhub...")
    raw_ipos = finnhub.get_ipo_calendar(today, today)
    logger.info(f"Received {len(raw_ipos)} total IPO entries")
    
    # Parse and filter IPOs
    ipos = [IPOData.from_finnhub(data) for data in raw_ipos]
    qualifying_ipos = filter_todays_large_ipos(ipos, today)
    
    logger.info(f"Found {len(qualifying_ipos)} IPO(s) meeting criteria (>$200M)")
    
    # Create and send email
    html_body, text_body = create_email_content(qualifying_ipos, today)
    
    if qualifying_ipos:
        subject = f"🔔 IPO Alert: {len(qualifying_ipos)} Large IPO(s) Today - {today}"
    else:
        subject = f"📊 IPO Monitor Report - {today}"
    
    success = notifier.send_email(
        recipient=email_recipient,
        subject=subject,
        body_html=html_body,
        body_text=text_body
    )
    
    if success:
        logger.info("IPO Monitor completed successfully!")
    else:
        logger.error("IPO Monitor completed with email delivery failure")
        sys.exit(1)


if __name__ == "__main__":
    main()