"""Monitors the Fansale website for specific tickets."""

import logging
import random
import sys
import time

import requests  # type: ignore
import undetected_chromedriver as uc  # type: ignore
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

URL_TO_MONITOR = "https://www.fansale.es/tickets/all/radiohead/494119"
EVENT_LIST_SELECTOR = ".js-EventEntryListNormal"
TARGET_DATE_STRING = "8 nov."
MAX_PRICE_EUROS = 150.0
CHECK_INTERVAL_SECONDS = 7
JITTER_SECONDS = 4  # How much to vary the sleep time (e.g., 7 +/- 4 seconds)
PAGE_LOAD_TIMEOUT = 30  # How long to wait for the page elements to load
NTFY_TOPIC = "radiohead-fansale-ticket-a5b2c8"


def check_for_tickets(
    driver: uc.Chrome, list_selector: str, target_string: str, max_price: float
) -> bool:
    """
    Scans the page for target event tickets within the price limit.
    """
    try:
        logging.info(
            "Waiting for event list to become visible (max %ds)...",
            PAGE_LOAD_TIMEOUT,
        )

        wait = WebDriverWait(driver, PAGE_LOAD_TIMEOUT)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, list_selector)))

        event_entries = driver.find_elements(By.CSS_SELECTOR, ".js-EventEntry")

        if not event_entries:
            logging.info(
                "Event list is present, but no individual event entries found."
            )
            return False

        logging.info(
            "Found %d event entries. Scanning for '%s' <= %.2f€...",
            len(event_entries),
            target_string,
            max_price,
        )

        for event in event_entries:
            try:
                event_text = event.get_attribute("innerText")

                if target_string.lower() in event_text.lower():
                    logging.info(
                        "  > Found event for '%s'. Checking price...",
                        target_string,
                    )

                    price_elements = event.find_elements(
                        By.CSS_SELECTOR,
                        (
                            ".EvEntryRow-moneyValueFormat, "
                            ".EvEntryRow-moneyValueFormatSmall"
                        ),
                    )

                    if not price_elements:
                        logging.warning(
                            "    - Found event but could not find price. Skipping."
                        )
                        continue

                    price_element = price_elements[0]
                    price_text = price_element.get_attribute("innerText")

                    price_clean = (
                        price_text.replace("€", "")
                        .replace(".", "")  # Thousands separator
                        .replace(",", ".")  # Decimal separator
                        .strip()
                    )
                    price_float = float(price_clean)

                    logging.info("    - Price found: %.2f€", price_float)

                    if price_float <= max_price:
                        logging.info(
                            "  !!! SUCCESS: Found '%s' at %.2f€ (<= %.2f€) !!!",
                            target_string,
                            price_float,
                            max_price,
                        )
                        return True
                    logging.info(
                        "    - Price %.2f€ is > %.2f€. Ignoring.",
                        price_float,
                        max_price,
                    )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logging.warning(
                    "  - Warning: could not parse an event entry. Error: %s", e
                )
                continue

        return False

    except TimeoutException:
        logging.error(
            "Timeout (%ds) exceeded waiting for element '%s'.",
            PAGE_LOAD_TIMEOUT,
            list_selector,
        )
        logging.error(
            "The page may be blocked by Akamai, showing a CAPTCHA, "
            "or the selector is wrong."
        )
        logging.error("Please check the browser window for any challenges.")
        return False
    except WebDriverException as e:
        logging.error("An error occurred with WebDriver: %s", e)
        return False
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("An unexpected error occurred in check_for_tickets: %s", e)
        return False


def send_notification(topic: str, message: str, title: str):
    """
    Sends a push notification via ntfy.sh.
    """
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=message,
            headers={
                "Title": title,
                "Priority": "high",
                "Tags": "loudspeaker",
            },
            timeout=10,
        )
        logging.info("Notification sent successfully!")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("Error: Failed to send notification: %s", e)


def main():
    """Main function to initialize and run the monitor."""
    logging.info("--- Website Change Monitor (Undetected-Chromedriver Edition) ---")

    logging.info("Monitoring URL: %s", URL_TO_MONITOR)
    logging.info(
        "Watching for text: '%s' with price <= %.2f€",
        TARGET_DATE_STRING,
        MAX_PRICE_EUROS,
    )
    logging.info(
        "Checking every ~%ds seconds (with +/- %ds jitter).",
        CHECK_INTERVAL_SECONDS,
        JITTER_SECONDS,
    )
    logging.info("Notifications will be sent to ntfy.sh topic: '%s'", NTFY_TOPIC)
    logging.info("-" * 55)
    logging.info("--- How to Receive Notifications ---")
    logging.info("1. On your phone, install the 'ntfy' app (iOS/Android).")
    logging.info("2. Open the app and 'Subscribe' to the topic: '%s'", NTFY_TOPIC)
    logging.info("3. Alternatively, view notifications in your browser at:")
    logging.info("   https://ntfy.sh/%s", NTFY_TOPIC)
    logging.info("-" * 34)
    logging.info("\n" + "--- Monitoring Log ---")

    driver = None
    ticket_was_available = False

    try:
        options = uc.ChromeOptions()
        options.headless = False

        driver = uc.Chrome(options=options, version_main=141)

        logging.info("Performing initial page load...")
        driver.get(URL_TO_MONITOR)

        logging.info("Performing initial check to establish a baseline...")
        date_found_initially = check_for_tickets(
            driver, EVENT_LIST_SELECTOR, TARGET_DATE_STRING, MAX_PRICE_EUROS
        )

        if date_found_initially:
            logging.info(
                "\n!!! TARGET DATE ('%s') FOUND on initial check! !!!",
                TARGET_DATE_STRING,
            )
            send_notification(
                NTFY_TOPIC,
                (
                    f"Tickets for '{TARGET_DATE_STRING}' (<= {MAX_PRICE_EUROS}€) "
                    f"found at {URL_TO_MONITOR}"
                ),
                "Tickets Found!",
            )
            ticket_was_available = True
        else:
            logging.info(
                "Baseline established. Target date '%s' not found.",
                TARGET_DATE_STRING,
            )

        check_count = 1

        while True:
            try:
                jitter = random.uniform(-JITTER_SECONDS, JITTER_SECONDS)
                sleep_time = max(1, CHECK_INTERVAL_SECONDS + jitter)
                logging.info(
                    "[%s] Check #%d: Sleeping for %.2fs before next refresh...",
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    check_count,
                    sleep_time,
                )
                time.sleep(sleep_time)

                logging.info("Refreshing page...")
                driver.refresh()

                date_found_now = check_for_tickets(
                    driver,
                    EVENT_LIST_SELECTOR,
                    TARGET_DATE_STRING,
                    MAX_PRICE_EUROS,
                )

                if date_found_now != ticket_was_available:
                    if date_found_now:
                        logging.info(
                            "\n!!! TARGET DATE ('%s') FOUND !!!",
                            TARGET_DATE_STRING,
                        )
                        send_notification(
                            NTFY_TOPIC,
                            (
                                f"Tickets for '{TARGET_DATE_STRING}' "
                                f"(<= {MAX_PRICE_EUROS}€) "
                                f"found at {URL_TO_MONITOR}"
                            ),
                            "Tickets Found!",
                        )
                    else:
                        logging.info(
                            "\n!!! TARGET DATE ('%s') IS NO LONGER AVAILABLE !!!",
                            TARGET_DATE_STRING,
                        )
                        send_notification(
                            NTFY_TOPIC,
                            (
                                f"Tickets for '{TARGET_DATE_STRING}' "
                                f"(<= {MAX_PRICE_EUROS}€) "
                                f"are no longer available."
                            ),
                            "Tickets Gone!",
                        )

                    ticket_was_available = date_found_now

                else:
                    if date_found_now:
                        logging.info(
                            "Matching tickets still available for '%s'. "
                            "No new notification.",
                            TARGET_DATE_STRING,
                        )
                    else:
                        logging.info(
                            "No matching tickets found for '%s' <= %.2f€.",
                            TARGET_DATE_STRING,
                            MAX_PRICE_EUROS,
                        )

                check_count += 1

            except KeyboardInterrupt:
                logging.info("\nMonitoring stopped by user. Exiting.")
                break

    except Exception as e:  # pylint: disable=broad-exception-caught
        logging.error("A critical error occurred in main: %s", e, exc_info=True)

    finally:
        if driver:
            driver.quit()
            logging.info("Browser closed.")


if __name__ == "__main__":
    main()
