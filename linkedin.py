import subprocess
import time
import requests
from time import sleep
from colorama import Fore
from patchright.sync_api import sync_playwright
green = Fore.GREEN
blue = Fore.BLUE
red = Fore.RED

# new version link ai mode so make it send msg to users for get more clinets
# fix locators and make it dynamic
# add sleep to avoid detection and make it more human like
# set connection limit to 100 per day and make it dynamic
# make a schedule to run the script every day at 9am and 5pm
# !!!!! today works !!!!!!
# locations locator label[for='_r_c6_']
# type people location #_r_cf_
# click serach button
# a[href*="/search/results/people/"] span:has-text("Show results")
# locator for add a note button button[aria-label="Add a note"]
# add people and location filter to search for specific people and location
# after people filter add a list of people to connect with and make it dynamic
# send first message to people after connecting with them and make it dynamic
# the msg will be add a note then send them a connection
# if user choice people it just for one page if user choice hashtag it will go to next page and connect with more people


DEBUG_URL = "http://127.0.0.1:9222"


def start_chrome():

    # Check if Chrome debugging is already running
    try:
        response = requests.get(
            f"{DEBUG_URL}/json/version",
            timeout=2
        )

        if response.status_code == 200:
            print("Chrome is already running.")
            return

    except requests.RequestException:
        pass

    # Launch Chrome with the automation profile
    chrome_path = (
        "/Applications/Google Chrome.app/"
        "Contents/MacOS/Google Chrome"
    )

    profile_path = "/Users/said1/Chrome-Automation"

    subprocess.Popen([
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_path}",
        "--profile-directory=Default",
        "--no-first-run"
    ])

    # Wait until Chrome debugging is ready
    for attempt in range(30):

        try:
            response = requests.get(
                f"{DEBUG_URL}/json/version",
                timeout=2
            )

            if response.status_code == 200:
                print("Chrome started successfully.")
                return

        except requests.RequestException:
            time.sleep(1)

    raise Exception("Chrome debugging server did not start.")


def setup_browser(playwright):

    browser = playwright.chromium.connect_over_cdp(
        DEBUG_URL
    )

    context = browser.contexts[0]

    page = (
        context.pages[0]
        if context.pages
        else context.new_page()
    )

    return browser, page


class Linkedin:
    def __init__(self, driver, playwright):
        self.page = driver
        self.playwright = playwright

    def main(self):
        self.search()

    def search(self):
        url = f'https://www.linkedin.com/search/results/all/?keywords=%23{hashtag}&origin=GLOBAL_SEARCH_HEADER&sid=NoW'
        print("Before:", self.page.url)

        response = self.page.goto(url, wait_until="domcontentloaded", timeout=60000)

        print("After:", self.page.url)
        print("Response:", response.status if response else None)
        sleep(2)
        self.page.locator("label[for='_r_3q_']").click()
        sleep(3)
        while True:

            connect_buttons = self.page.locator(
                'a[aria-label^="Invite"][href*="/preload/search-custom-invite/"]'
            )

            count = connect_buttons.count()

            print(f"Connect buttons found: {count}")

            for i in range(count):

                try:
                    button = connect_buttons.nth(i)

                    if not button.is_visible():
                        continue

                    button.click(timeout=3000)

                    print(f"Clicked Connect button {i + 1}")

                    send_button = self.page.get_by_text(
                        "Send without a note",
                        exact=True
                    )

                    try:
                        send_button.wait_for(
                            state="visible",
                            timeout=10000
                        )

                        send_button.click(timeout=5000)

                        print("Invitation sent.")

                        self.page.wait_for_timeout(1500)

                    except Exception:
                        print("Send button did not appear. Skipping...")

                        continue

                except Exception as e:

                    print(f"Error on button {i + 1}: {e}")

                    continue

            # Move to next page

            next_page = self.page.locator(
                'button[data-testid="pagination-controls-next-button-visible"]'
            )

            try:

                next_page.wait_for(
                    state="visible",
                    timeout=5000
                )

                print("Moving to next page...")

                next_page.click(timeout=5000)

                self.page.wait_for_timeout(3000)

            except Exception:

                print("Next page not available. Finished.")

                break


def main():

    start_chrome()

    with sync_playwright() as playwright:

        browser, driver = setup_browser(playwright)

        print("Connected to Chrome successfully.")
        print("Current page:", driver.url)

        linkedin = Linkedin(driver, playwright)

        linkedin.main()

        input("\nPress Enter to exit...")

        # Disconnect Playwright without closing Chrome
        browser.close()


if __name__ == "__main__":

    hashtag = input("Enter your hashtag: ").strip()

    hashtag = hashtag.lstrip("#")

    if not hashtag:
        print("Please enter a valid hashtag.")

    else:
        main()
