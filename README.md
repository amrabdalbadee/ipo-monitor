# 📊 IPO Monitor - Daily U.S. IPO Alert System

Automated workflow that monitors upcoming U.S. stock market IPOs daily at 9:00 AM Dubai time and sends email alerts for large offerings (>$200M).

## Features

- ✅ Monitors today's IPOs only (same-day, not future IPOs)
- ✅ Filters for offer amount > $200 million USD
- ✅ Sends formatted email with qualifying ticker details
- ✅ Free API tier support (Finnhub)
- ✅ Multiple deployment options (GitHub Actions, cron, cloud functions)

## Quick Start

### 1. Get Required API Keys

#### Finnhub API Key (Free)
1. Go to [https://finnhub.io](https://finnhub.io)
2. Sign up for a free account
3. Copy your API key from the dashboard

#### Gmail App Password (for email notifications)
1. Go to [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication (required)
3. Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Create an app password for "Mail"
5. Copy the 16-character password

### 2. Choose Your Deployment Method

---

## Option A: GitHub Actions (Recommended - Free & Serverless)

### Setup Steps:

1. **Fork or clone this repository to GitHub**

2. **Add secrets to your repository:**
   - Go to: `Settings` → `Secrets and variables` → `Actions`
   - Add these repository secrets:

   | Secret Name | Value | Required |
   |-------------|-------|----------|
   | `FINNHUB_API_KEY` | Your Finnhub API key | ✅ |
   | `EMAIL_SENDER` | your.email@gmail.com | ✅ |
   | `EMAIL_PASSWORD` | Your Gmail app password | ✅ |
   | `EMAIL_RECIPIENT` | recipient@email.com | ❌ (defaults to sender) |
   | `SMTP_SERVER` | smtp.gmail.com | ❌ (defaults to Gmail) |
   | `SMTP_PORT` | 587 | ❌ (defaults to 587) |

3. **Enable the workflow:**
   - Go to `Actions` tab in your repository
   - Click "I understand my workflows, go ahead and enable them"

4. **Test manually:**
   - Go to `Actions` → `IPO Monitor`
   - Click `Run workflow` → `Run workflow`

The workflow will automatically run daily at 9:00 AM Dubai time (5:00 AM UTC).

---

## Option B: Local Cron Job (Linux/macOS)

### Setup Steps:

1. **Clone and install dependencies:**
   ```bash
   git clone <your-repo-url>
   cd ipo-monitor
   pip install -r requirements.txt
   ```

2. **Create environment file:**
   ```bash
   cat > .env << 'EOF'
   export FINNHUB_API_KEY="your_finnhub_api_key"
   export EMAIL_SENDER="your.email@gmail.com"
   export EMAIL_PASSWORD="your_gmail_app_password"
   export EMAIL_RECIPIENT="recipient@email.com"
   export SMTP_SERVER="smtp.gmail.com"
   export SMTP_PORT="587"
   EOF
   chmod 600 .env
   ```

3. **Test the script:**
   ```bash
   source .env
   python ipo_monitor.py
   ```

4. **Add cron job for 9:00 AM Dubai time:**
   ```bash
   # Edit crontab
   crontab -e
   
   # Add this line (adjust timezone offset as needed)
   # For systems in UTC: 5:00 AM UTC = 9:00 AM Dubai
   0 5 * * * cd /path/to/ipo-monitor && source .env && /usr/bin/python3 ipo_monitor.py >> /var/log/ipo-monitor.log 2>&1
   ```

---

## Option C: AWS Lambda (Serverless)

### Setup Steps:

1. **Create Lambda function:**
   - Runtime: Python 3.11
   - Handler: `lambda_function.lambda_handler`

2. **Create `lambda_function.py`:**
   ```python
   import ipo_monitor

   def lambda_handler(event, context):
       ipo_monitor.main()
       return {'statusCode': 200, 'body': 'IPO Monitor completed'}
   ```

3. **Package and deploy:**
   ```bash
   pip install requests -t package/
   cp ipo_monitor.py lambda_function.py package/
   cd package && zip -r ../deployment.zip .
   ```

4. **Configure environment variables** in Lambda console

5. **Add EventBridge trigger:**
   - Cron expression: `cron(0 5 * * ? *)`  (9:00 AM Dubai = 5:00 AM UTC)

---

## Option D: Google Cloud Functions

### Setup Steps:

1. **Create `main.py`:**
   ```python
   import ipo_monitor
   from flask import jsonify

   def run_ipo_monitor(request):
       ipo_monitor.main()
       return jsonify({"status": "success"})
   ```

2. **Deploy:**
   ```bash
   gcloud functions deploy ipo-monitor \
     --runtime python311 \
     --trigger-http \
     --set-env-vars FINNHUB_API_KEY=xxx,EMAIL_SENDER=xxx,EMAIL_PASSWORD=xxx
   ```

3. **Create Cloud Scheduler job:**
   ```bash
   gcloud scheduler jobs create http ipo-monitor-daily \
     --schedule="0 5 * * *" \
     --uri="YOUR_FUNCTION_URL" \
     --http-method=GET \
     --time-zone="UTC"
   ```

---

## Configuration Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `FINNHUB_API_KEY` | Finnhub API key | (required) |
| `EMAIL_SENDER` | Sender email address | (required) |
| `EMAIL_PASSWORD` | Email app password | (required) |
| `EMAIL_RECIPIENT` | Recipient email | Same as sender |
| `SMTP_SERVER` | SMTP server address | smtp.gmail.com |
| `SMTP_PORT` | SMTP port | 587 |

## Sample Email Output

### When qualifying IPOs are found:
```
Subject: 🔔 IPO Alert: 2 Large IPO(s) Today - 2026-02-01

┌──────────┬─────────────────┬─────────┬──────────────┬──────────┐
│ Ticker   │ Company         │ Price   │ Offer Amount │ Exchange │
├──────────┼─────────────────┼─────────┼──────────────┼──────────┤
│ ABCD     │ Example Corp    │ $25.00  │ $500.00M     │ NASDAQ   │
│ XYZ      │ Tech Holdings   │ $42.00  │ $1.20B       │ NYSE     │
└──────────┴─────────────────┴─────────┴──────────────┴──────────┘
```

### When no qualifying IPOs:
```
Subject: 📊 IPO Monitor Report - 2026-02-01

No IPOs with offer amount > $200M scheduled for today.
```

## Customization

### Adjust Offer Amount Threshold

Edit `ipo_monitor.py` line 36:
```python
OFFER_AMOUNT_THRESHOLD = 200_000_000  # Change to desired amount in USD
```

### Change Execution Time

For GitHub Actions, edit `.github/workflows/ipo-monitor.yml`:
```yaml
schedule:
  - cron: '0 5 * * *'  # Format: minute hour * * * (UTC)
```

Common Dubai times to UTC:
| Dubai Time | UTC Cron |
|------------|----------|
| 6:00 AM | `0 2 * * *` |
| 8:00 AM | `0 4 * * *` |
| 9:00 AM | `0 5 * * *` |
| 10:00 AM | `0 6 * * *` |

## Troubleshooting

### "Failed to fetch IPO calendar"
- Check your Finnhub API key is valid
- Verify you haven't exceeded API rate limits (60 calls/minute on free tier)

### "Failed to send email"
- For Gmail: Ensure you're using an App Password, not your regular password
- Verify 2FA is enabled on your Google account
- Check SMTP settings are correct

### GitHub Actions not running
- Verify the workflow is enabled in the Actions tab
- Check repository settings allow scheduled workflows
- Note: GitHub may delay scheduled runs during high-load periods

## API Data Source

This tool uses [Finnhub's IPO Calendar API](https://finnhub.io/docs/api/ipo-calendar) which provides:
- IPO date
- Company name and ticker
- Price and share count
- Exchange information

The free tier includes up to 60 API calls/minute, which is more than sufficient for daily monitoring.

## License

MIT License - Feel free to modify and use for your own purposes.
