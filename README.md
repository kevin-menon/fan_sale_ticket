# Fansale Ticket Monitor

An automated Python script that monitors ticket availability on Fansale.es and sends instant notifications when tickets matching your criteria become available.

## Features

- 🔍 **Automated Monitoring**: Continuously checks for ticket availability
- 💰 **Price Filtering**: Only alerts for tickets below your maximum price
- 📱 **Push Notifications**: Real-time alerts via ntfy.sh to your phone or browser
- 🤖 **Bot Detection Evasion**: Uses undetected-chromedriver to bypass anti-bot measures
- 🎭 **Headless Operation**: Runs invisibly in the background
- ⏱️ **Human-like Behavior**: Random intervals between checks to avoid detection

## Prerequisites

- Python 3.7 or higher
- Google Chrome browser installed
- Internet connection

## Installation

1. **Clone or download this repository**

2. **Install required Python packages:**
   ```bash
   pip install undetected-chromedriver selenium requests
   ```

3. **Verify Chrome is installed** (the script will automatically download the matching ChromeDriver)

## Configuration

Edit the following constants at the top of the script to match your needs:

```python
URL_TO_MONITOR = "https://www.fansale.es/tickets/all/radiohead/494119"
TARGET_DATE_STRING = "8 nov."
MAX_PRICE_EUROS = 150.0
CHECK_INTERVAL_SECONDS = 7
JITTER_SECONDS = 4
NTFY_TOPIC = "radiohead-fansale-ticket-a5b2c8"
```

### Configuration Options

| Variable | Description | Example |
|----------|-------------|---------|
| `URL_TO_MONITOR` | The Fansale event page URL | `"https://www.fansale.es/tickets/all/radiohead/494119"` |
| `TARGET_DATE_STRING` | Date text to search for (as shown on page) | `"8 nov."` |
| `MAX_PRICE_EUROS` | Maximum price you're willing to pay | `150.0` |
| `CHECK_INTERVAL_SECONDS` | Base time between checks | `7` |
| `JITTER_SECONDS` | Random variation in check interval | `4` |
| `NTFY_TOPIC` | Your unique ntfy.sh notification topic | `"radiohead-fansale-ticket-a5b2c8"` |

## Setting Up Notifications

### Option 1: Mobile App (Recommended)

1. Install the **ntfy** app:
   - [iOS App Store](https://apps.apple.com/us/app/ntfy/id1625396347)
   - [Android Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy)

2. Open the app and tap "Subscribe to topic"

3. Enter your `NTFY_TOPIC` value (e.g., `radiohead-fansale-ticket-a5b2c8`)

4. Enable notifications on your device

### Option 2: Browser

Visit `https://ntfy.sh/your-topic-name` (replace with your topic) in your browser to see notifications.

## First-Time Setup

⚠️ **IMPORTANT**: On the first run, Akamai's anti-bot system may present a CAPTCHA challenge.

### Initial CAPTCHA Resolution

1. **Edit the script** and set:
   ```python
   options.headless = False
   ```

2. **Run the script:**
   ```bash
   python monitor.py
   ```

3. **A browser window will open** - manually solve any CAPTCHA that appears

4. **Wait** until you see "Baseline established." in the console

5. **Stop the script** (Ctrl+C)

6. **Re-enable headless mode:**
   ```python
   options.headless = True
   ```

7. **Run the script again** - it will now work invisibly using your verified session

## Usage

### Basic Usage

Simply run the script:

```bash
python monitor.py
```

### Running in the Background (Linux/Mac)

```bash
nohup python monitor.py &
```

### Running as a Background Service (Windows)

Use Task Scheduler or run in a minimized terminal window.

### Stopping the Monitor

Press `Ctrl+C` in the terminal where the script is running.

## How It Works

1. **Initial Load**: Opens the Fansale event page and establishes a baseline
2. **Continuous Monitoring**: Refreshes the page at randomized intervals
3. **Smart Parsing**: 
   - Searches for your target date string
   - Extracts and validates ticket prices
   - Handles multiple price formats
4. **Instant Alerts**: Sends push notification when matching tickets are found
5. **Auto-Stop**: Stops monitoring after finding matching tickets

## Troubleshooting

### "Timeout 60s exceeded" Error

- The page is likely blocked by Akamai's bot detection
- Follow the [First-Time Setup](#first-time-setup) instructions to solve the CAPTCHA
- Make sure Chrome is up to date

### Script Crashes Immediately

- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check that Chrome browser is installed
- Try updating undetected-chromedriver: `pip install --upgrade undetected-chromedriver`

### No Notifications Received

- Verify you're subscribed to the correct ntfy.sh topic
- Check your phone's notification settings
- Test by visiting `https://ntfy.sh/your-topic-name` in a browser

### Price Not Detected Correctly

- The script handles Spanish price formats (e.g., "150,00€")
- If prices aren't being detected, the CSS selectors may have changed
- Check the browser console for parsing errors

## Customization

### Monitoring Multiple Events

Create separate copies of the script with different configuration values for each event.

### Adjusting Check Frequency

- Lower `CHECK_INTERVAL_SECONDS` for faster checks (higher bot detection risk)
- Higher values reduce server load and detection risk
- `JITTER_SECONDS` adds randomness to appear more human-like

### Custom Notification Services

Replace the `send_notification()` function to use:
- Email (SMTP)
- SMS (Twilio)
- Discord webhooks
- Telegram bots

## Legal and Ethical Considerations

- This script is for **personal use only**
- Respect Fansale.es Terms of Service
- Don't abuse the service with excessive requests
- Use reasonable check intervals (5+ seconds recommended)
- Don't attempt to bypass purchase limits or resell tickets

## License

This script is provided as-is for educational and personal use.

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review the console output for error messages
3. Ensure all prerequisites are met

---

**Happy ticket hunting! 🎫**