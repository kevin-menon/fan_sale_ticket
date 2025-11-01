import time
import hashlib
import sys
import requests
import random
import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
)

URL_TO_MONITOR = "https://www.fansale.es/tickets/all/radiohead/494119"
EVENT_LIST_SELECTOR = ".js-EventEntryListNormal"
TARGET_DATE_STRING = "8 nov."
MAX_PRICE_EUROS = 150.0
CHECK_INTERVAL_SECONDS = 7
JITTER_SECONDS = 4  # How much to vary the sleep time (e.g., 5 +/- 3 seconds)
NTFY_TOPIC = "radiohead-fansale-ticket-a5b2c8"


def check_for_tickets(
    driver: uc.Chrome, list_selector: str, target_string: str, max_price: float
) -> bool:
    try:
        print("Waiting for event list to become visible...")

        wait = WebDriverWait(driver, 60)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, list_selector)))

        event_entries = driver.find_elements(By.CSS_SELECTOR, ".js-EventEntry")

        if not event_entries:
            print("Event list is present, but no individual event entries found.")
            return False

        print(
            f"Found {len(event_entries)} event entries. Scanning for '{target_string}' <= {max_price}€..."
        )

        for event in event_entries:
            try:
                event_text = event.get_attribute("innerText")

                if target_string.lower() in event_text.lower():
                    print(f"  > Found event for '{target_string}'. Checking price...")

                    try:
                        price_element = event.find_element(
                            By.CSS_SELECTOR, ".EvEntryRow-moneyValueFormat"
                        )
                    except NoSuchElementException:
                        price_element = event.find_element(
                            By.CSS_SELECTOR, ".EvEntryRow-moneyValueFormatSmall"
                        )

                    price_text = price_element.get_attribute("innerText")

                    price_clean = (
                        price_text.replace("€", "")
                        .replace(".", "")
                        .replace(",", ".")
                        .strip()
                    )
                    price_float = float(price_clean)

                    print(f"    - Price found: {price_float}€")

                    if price_float <= max_price:
                        print(
                            f"  !!! SUCCESS: Found '{target_string}' at {price_float}€ (<= {max_price}€) !!!"
                        )
                        return True
                    else:
                        print(
                            f"    - Price {price_float}€ is > {max_price}€. Ignoring."
                        )

            except Exception as e:
                print(
                    f"  - Warning: could not parse an event entry. Error: {e}",
                    file=sys.stderr,
                )
                continue

        return False

    except TimeoutException:
        print(f"\nAn error occurred: Timeout 60s exceeded.", file=sys.stderr)
        print(
            f"The element '{list_selector}' was not found. The page may be blocked by Akamai or showing a CAPTCHA.",
            file=sys.stderr,
        )
        print("Please check the browser window for any challenges.", file=sys.stderr)
        return False
    except WebDriverException as e:
        print(f"\nAn error occurred with WebDriver: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return False


def send_notification(topic: str, message: str, title: str):
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": title.encode("utf-8"),
                "Priority": "high",
                "Tags": "loudspeaker",
            },
        )
        print("Notification sent successfully!")
    except Exception as e:
        print(f"Error: Failed to send notification: {e}", file=sys.stderr)


def main():
    print("--- Website Change Monitor (Undetected-Chromedriver Edition) ---")
    print(f"Monitoring URL: {URL_TO_MONITOR}")
    print(f"Watching for text: '{TARGET_DATE_STRING}' with price <= {MAX_PRICE_EUROS}€")
    print(
        f"Checking every ~{CHECK_INTERVAL_SECONDS} seconds (with +/- {JITTER_SECONDS}s jitter)."
    )
    print(f"Notifications will be sent to ntfy.sh topic: '{NTFY_TOPIC}'")
    print("-" * 55 + "\n")

    print("--- How to Receive Notifications ---")
    print(f"1. On your phone, install the 'ntfy' app (iOS/Android).")
    print(f"2. Open the app and 'Subscribe' to the topic: '{NTFY_TOPIC}'")
    print("3. Alternatively, view notifications in your browser at:")
    print(f"   https://ntfy.sh/{NTFY_TOPIC}")
    print("-" * 34 + "\n")

    print("\n" + "--- Monitoring Log ---")

    driver = None
    try:
        options = uc.ChromeOptions()

        # --- HEADLESS STRATEGY ---
        # Run in headless mode (invisible) to avoid bot detection based on lack of mouse movement.
        #
        # ** IMPORTANT "FIRST RUN" INSTRUCTIONS: **
        # If the script fails on its first-ever run, Akamai may be issuing a one-time
        # CAPTCHA. To solve it:
        # 1. Temporarily set: `options.headless = False`
        # 2. Run the script. A browser will open.
        # 3. Manually solve the CAPTCHA in the browser.
        # 4. Wait for the script to print "Baseline established."
        # 5. Stop the script (Ctrl+C).
        # 6. Set `options.headless = True` again and restart.
        #
        # The script will now use your saved, verified session cookies to run invisibly.
        options.headless = True

        driver = uc.Chrome(options=options, version_main=141)

        print("Performing initial page load...")
        driver.get(URL_TO_MONITOR)

        print("Performing initial check to establish a baseline...")
        date_found_initially = check_for_tickets(
            driver, EVENT_LIST_SELECTOR, TARGET_DATE_STRING, MAX_PRICE_EUROS
        )

        if date_found_initially:
            print(
                f"\n!!! TARGET DATE ('{TARGET_DATE_STRING}') FOUND on initial check! !!!"
            )
            send_notification(
                NTFY_TOPIC,
                f"Tickets for '{TARGET_DATE_STRING}' (<= {MAX_PRICE_EUROS}€) found at {URL_TO_MONITOR}",
                "Tickets Found!",
            )
            print("Exiting.")
            return

        print(f"Baseline established. Target date '{TARGET_DATE_STRING}' not found.")
        check_count = 1

        while True:
            try:
                # Human-like refresh behavior: vary the sleep time
                jitter = random.uniform(-JITTER_SECONDS, JITTER_SECONDS)
                sleep_time = max(
                    1, CHECK_INTERVAL_SECONDS + jitter
                )  # Ensure at least 1 sec sleep

                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Check #{check_count}: Sleeping for {sleep_time:.2f}s before next refresh..."
                )
                time.sleep(sleep_time)

                print("Refreshing page...")
                driver.refresh()
                date_found_now = check_for_tickets(
                    driver, EVENT_LIST_SELECTOR, TARGET_DATE_STRING, MAX_PRICE_EUROS
                )

                if date_found_now:
                    print(f"\n!!! TARGET DATE ('{TARGET_DATE_STRING}') FOUND !!!")
                    send_notification(
                        NTFY_TOPIC,
                        f"Tickets for '{TARGET_DATE_STRING}' (<= {MAX_PRICE_EUROS}€) found at {URL_TO_MONITOR}",
                        "Tickets Found!",
                    )
                    print("\nMonitoring has stopped after detecting the date.")
                    break
                else:
                    print(
                        f"No matching tickets found for '{TARGET_DATE_STRING}' <= {MAX_PRICE_EUROS}€."
                    )

                check_count += 1

            except KeyboardInterrupt:
                print("\nMonitoring stopped by user. Exiting.")
                break

    except Exception as e:
        print(f"A critical error occurred: {e}", file=sys.stderr)

    finally:
        if driver:
            driver.quit()
            print("Browser closed.")


if __name__ == "__main__":
    main()
