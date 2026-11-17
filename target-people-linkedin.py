import subprocess
import time
import re
import requests
from time import sleep
from urllib.parse import quote
from colorama import Fore
from patchright.sync_api import sync_playwright

green = Fore.GREEN
blue = Fore.BLUE
red = Fore.RED

# Created By Said Atwa
# https://www.linkedin.com/in/saidatwa/

# new version link ai mode so make it send msg to users for get more clients
# set connection limit to 100 per day and make it dynamic
# make a schedule to run the script every day at 9am and 5pm



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
        # Dynamic config, set from main()
        self.search_type = None  # "hashtag" or "people"
        self.hashtag_value = ""  # keyword for hashtag mode
        self.location_filter = ""  # optional location filter text
        self.note_message = ""  # optional note text
        self.people_list = []  # list of names/URLs to target (people mode)
        # Exact name matching is enabled only in people mode
        self.filter_by_name = True

    # ------------------------------------------------------------------ #
    #  Search entry
    # ------------------------------------------------------------------ #
    def main(self):
        self.search()

    def _build_search_url(self):
        """Return the LinkedIn search URL for the chosen mode."""
        if self.search_type == "hashtag":
            # Hashtag must be URL-encoded as %23<tag>
            tag = self.hashtag_value
            return (
                "https://www.linkedin.com/search/results/all/"
                f"?keywords=%23{tag}&origin=GLOBAL_SEARCH_HEADER"
            )

        # people mode: search the people directory.
        # If a target name was given, use it as keyword to narrow results.
        name_keyword = self.people_list[0] if self.people_list else ""
        if name_keyword:
            # Properly URL-encode the name (supports Arabic and special chars)
            return (
                "https://www.linkedin.com/search/results/people/"
                f"?keywords={quote(name_keyword)}"
            )
        return "https://www.linkedin.com/search/results/people/"

    # ------------------------------------------------------------------ #
    #  Location filter
    # ------------------------------------------------------------------ #
    def _apply_filters(self):
        """Apply the location filter using the top-bar 'Locations' filter button."""
        if not self.location_filter:
            return

        print(f"Applying location filter: {self.location_filter!r}")

        # ---------------------------------------------------------------- #
        # 1) Click the "Locations" filter button (opens the dropdown)
        #    Matches: <div role="button" aria-label="Filter by Locations">
        # ---------------------------------------------------------------- #
        locations_btn = self.page.locator(
            '[role="button"][aria-label="Filter by Locations"]'
        )
        if locations_btn.count() == 0:
            # Fallback: the label text inside the button
            locations_btn = self.page.locator(
                '[role="button"]:has(label:has-text("Locations"))'
            )

        if locations_btn.count() == 0:
            print("'Locations' filter button not found. Skipping location filter.")
            return

        try:
            btn = locations_btn.first
            btn.scroll_into_view_if_needed()
            # Only click if not already expanded
            if btn.get_attribute("aria-expanded") != "true":
                btn.click()
                print("Opened 'Locations' dropdown.")
        except Exception as e:
            print(f"Clicking 'Locations' button failed: {e}")
            return

        # ---------------------------------------------------------------- #
        # 2) Wait for the location typeahead input to appear
        #    Matches: <input data-testid="typeahead-input" placeholder="Add a location">
        # ---------------------------------------------------------------- #
        location_input = self.page.locator(
            'input[data-testid="typeahead-input"][placeholder="Add a location"]'
        )
        try:
            location_input.first.wait_for(state="visible", timeout=10000)
        except Exception:
            # Fallback: any visible typeahead input with "location" in the placeholder
            location_input = self.page.locator(
                'input[data-testid="typeahead-input"]'
            )
            found = False
            for idx in range(location_input.count()):
                el = location_input.nth(idx)
                try:
                    if el.is_visible() and "location" in (el.get_attribute("placeholder") or "").lower():
                        found = True
                        break
                except Exception:
                    continue
            if not found:
                print("Location input did not appear after opening dropdown.")
                return

        # ---------------------------------------------------------------- #
        # 3) Type the location and pick the FIRST suggestion
        #    Suggestions are: div[role="option"] inside div[data-testid="lazy-column"]
        # ---------------------------------------------------------------- #
        try:
            inp = location_input.first
            inp.scroll_into_view_if_needed()
            inp.click()
            inp.fill(self.location_filter)
            print(f"Typed location: {self.location_filter!r}")
            sleep(1)

            # Wait for the suggestion list to render
            suggestion_list = self.page.locator(
                '[data-testid="lazy-column"] div[role="option"]'
            )
            try:
                suggestion_list.first.wait_for(state="visible", timeout=8000)
            except Exception:
                print("No suggestion list appeared after typing.")
                return

            n = suggestion_list.count()
            print(f"Found {n} location suggestion(s).")

            if n == 0:
                print("Suggestion list is empty. Skipping.")
                return

            # Log what we're about to pick (first suggestion text)
            first = suggestion_list.first
            try:
                first_text = first.inner_text(timeout=2000).strip().replace("\n", " ")
            except Exception:
                first_text = "<unknown>"
            print(f"Picking first suggestion: {first_text!r}")

            # Click it (the inner role="button" is the clickable element)
            clickable = first.locator('[role="button"]')
            if clickable.count() > 0:
                clickable.first.click()
            else:
                first.click()

            print("Location suggestion selected.")

            # Verify aria-selected flipped to true (optional sanity check)
            # sleep(1)
            try:
                selected = first.get_attribute("aria-selected", timeout=500)
                print(f"  aria-selected after click: {selected!r}")
            except Exception:
                pass

        except Exception as e:
            print(f"Filling location input / picking suggestion failed: {e}")
            return

        # ---------------------------------------------------------------- #
        # 4) Click "Show results"
        #    Use force=True to bypass Playwright's actionability checks,
        #    which can stall when an overlay or animation is present.
        # ---------------------------------------------------------------- #
        try:
            # Single query combining both selectors avoids two round-trips
            show_results = self.page.locator(
                '[data-view-name="search-filter-top-bar-menu-submit"], '
                'a:has-text("Show results"), '
                'button:has-text("Show results")'
            )

            # Wait for it to be attached, then force-click immediately.
            show_results.first.wait_for(state="attached", timeout=4000)
            show_results.first.click(force=True)
            print("Clicked 'Show results' (forced).")

            # Wait for results to render instead of a fixed sleep.
            try:
                self.page.wait_for_selector(
                    'li.reusable-search__result-container',
                    timeout=8000,
                )
                print("Search results loaded.")
            except Exception:
                self.page.wait_for_timeout(1000)

        except Exception as e:
            print(f"Clicking 'Show results' failed: {e}")

    # ------------------------------------------------------------------ #
    #  Exact name matching (people mode)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Normalize a name: remove extra spaces, unify case,
        and strip punctuation.
        """
        if not name:
            return ""
        # Remove symbols and collapse repeated whitespace
        name = re.sub(r"[^\w\s\u0600-\u06FF]", " ", name)
        name = re.sub(r"\s+", " ", name).strip().lower()
        print(name)
        return name

    @classmethod
    def _is_exact_name_match(cls, profile_name: str, target_name: str) -> bool:
        """
        Exact name match:
          - Single-word target matches the FIRST name only (so 'ahmed'
            matches 'Ahmed Alzaanin' but 'ali' does NOT match 'Alia').
          - Multi-word target requires the same set of words with the
            same word count.
        """
        if not profile_name or not target_name:
            return False

        p = cls._normalize_name(profile_name)
        t = cls._normalize_name(target_name)

        if not p or not t:
            return False

        if p == t:
            return True

        p_parts = p.split()
        t_parts = t.split()

        # Single-word target → match against the first name only
        if len(t_parts) == 1:
            return p_parts[0] == t_parts[0]

        # Multi-word target → same words, same count
        if set(t_parts).issubset(set(p_parts)) and len(p_parts) == len(t_parts):
            return True

        return False

    def _extract_card_name(self, card) -> str:
        """
        Extract the displayed profile name from a result card.
        Uses the stable 'search-result-lockup-title' attribute.
        """
        if card is None:
            return ""

        selectors = [
            'a[data-view-name="search-result-lockup-title"]',
            'span.entity-result__title-text a span[aria-hidden="true"]',
            'a[href*="/in/"] span[aria-hidden="true"]',
            'span[aria-hidden="true"]',
        ]
        for sel in selectors:
            try:
                el = card.locator(sel).first
                if el.count() == 0:
                    continue
                txt = el.inner_text(timeout=1500).strip()
                # Remove connection degree like "• 2nd"
                txt = re.sub(r"\s*[•·]\s*\d+(st|nd|rd|th)?$", "", txt).strip()
                if txt:
                    return txt
            except Exception:
                continue
        return ""

    def _card_matches(self, card_text: str, card_href: str, card, targets: list) -> bool:
        """
        Return True if a result card matches any target name/URL exactly.
        """
        if not targets:
            return True  # no list → allow all

        profile_name = self._extract_card_name(card)

        if not profile_name and card_text:
            skip_prefixes = (
                "linkedin member",
                "status is offline",
                "status is online",
                "follow",
                "connect",
                "message",
            )
            for line in card_text.splitlines():
                line = line.strip()
                if not line:
                    continue
                low = line.lower()
                if any(low.startswith(p) for p in skip_prefixes):
                    continue
                profile_name = line
                break

        print(f"  Card name extracted: {profile_name!r}")

        href_lc = (card_href or "").lower()

        for target in targets:
            t = (target or "").strip()
            if not t:
                continue

            if t.startswith("http") or "/in/" in t:
                if t.lower() in href_lc:
                    return True
                continue

            if self._is_exact_name_match(profile_name, t):
                return True
            else:
                print(f"    No match: {profile_name!r} != {t!r}")

        return False

    def _card_matches_by_name(self, profile_name: str, card_href: str, targets: list) -> bool:
        """
        Return True if the extracted profile name matches any target exactly.
        """
        if not targets:
            return True

        href_lc = (card_href or "").lower()

        for target in targets:
            t = (target or "").strip()
            if not t:
                continue

            # URL targets: match against href directly
            if t.startswith("http") or "/in/" in t:
                if t.lower() in href_lc:
                    return True
                continue

            if self._is_exact_name_match(profile_name, t):
                return True
            else:
                print(f"    No match: {profile_name!r} != {t!r}")

        return False
    # ------------------------------------------------------------------ #
    #  Main search loop
    # ------------------------------------------------------------------ #
    def search(self):
        url = self._build_search_url()
        print("Before:", self.page.url)

        response = self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print("After:", self.page.url)
        print("Response:", response.status if response else None)
        sleep(3)

        # Location filter (only meaningful when we're on a people/search results page)
        self._apply_filters()

        # People mode: only one page
        max_pages = None if self.search_type == "hashtag" else 1
        page_num = 0

        while True:
            page_num += 1
            print(f"\n--- Processing page {page_num} ---")

            connect_buttons = self.page.locator(
                'a[aria-label^="Invite"][href*="/preload/search-custom-invite/"]'
            )
            count = connect_buttons.count()
            print(f"Connect buttons found: {count}")

            for i in range(count):
                try:
                    button = connect_buttons.nth(i)
                    if not button.is_visible():
                        print(f"Skip button {i + 1}: not visible.")
                        continue

                    # Exact name filter (only when enabled and a target list exists)
                    # Exact name filter (only when enabled and a target list exists)
                    # Exact name filter (only when enabled and a target list exists)
                    if self.people_list and getattr(self, "filter_by_name", False):
                        # Always fetch href first (used both for name lookup and URL matching)
                        href = button.get_attribute("href") or ""

                        # Try to get the name from the Invite button's aria-label first.
                        # Example: aria-label="Invite Ahmed Alzaanin to connect"
                        aria = button.get_attribute("aria-label") or ""
                        profile_name = ""

                        m = re.search(r"Invite\s+(.+?)\s+to\s+connect", aria, re.IGNORECASE)
                        if m:
                            profile_name = m.group(1).strip()

                        # Fallback: search the page for the profile title link
                        # that shares the same /in/<slug>/ as the button's href
                        if not profile_name:
                            m2 = re.search(r"/in/([^/?#]+)", href)
                            if m2:
                                vanity = m2.group(1)
                                name_link = self.page.locator(
                                    f'a[data-view-name="search-result-lockup-title"][href*="/in/{vanity}/"]'
                                )
                                if name_link.count() > 0:
                                    try:
                                        profile_name = name_link.first.inner_text(timeout=1500).strip()
                                    except Exception:
                                        pass

                        print(f"  Card name extracted: {profile_name!r}")

                        if not self._card_matches_by_name(profile_name, href, self.people_list):
                            print(f"Skip button {i + 1}: name is not an exact match.")
                            continue
                    button.click(timeout=3000)
                    print(f"Clicked Connect button {i + 1}")

                    # Try with note first
                    if self.note_message:
                        if self._send_with_note():
                            print(f"  Invitation {i + 1} sent WITH note.")
                            continue
                        print(f"  Note failed for button {i + 1}; falling back to no-note.")

                    # Fallback: send without a note
                    if self._send_without_note():
                        print(f"  Invitation {i + 1} sent (no note).")
                    else:
                        print(f"  Send button did not appear for button {i + 1}; skipping.")

                except Exception as e:
                    print(f"Error on button {i + 1}: {e}")
                    continue

            # ---- pagination ----
            if max_pages is not None and page_num >= max_pages:
                print(f"People mode: finished after {page_num} page(s).")
                break

            next_page = self.page.locator(
                'button[data-testid="pagination-controls-next-button-visible"]'
            )
            try:
                next_page.wait_for(state="visible", timeout=5000)
                print("Moving to next page...")
                next_page.click(timeout=5000)
                self.page.wait_for_timeout(3000)
            except Exception:
                print("Next page not available. Finished.")
                break

    # ------------------------------------------------------------------ #
    #  Send helpers
    # ------------------------------------------------------------------ #
    def _send_with_note(self) -> bool:
        """Click 'Add a note', fill #custom-message, click 'Send invitation'."""
        try:
            # 1) Click "Add a note"
            add_note = self.page.locator('button[aria-label="Add a note"]')
            add_note.first.wait_for(state="visible", timeout=8000)
            add_note.first.click(timeout=3000)
            print("  Clicked 'Add a note'.")

            # 2) Wait for the note textarea by its stable id
            note_area = self.page.locator('textarea#custom-message[name="message"]')
            note_area.first.wait_for(state="visible", timeout=8000)

            # 3) Fill the note
            note_area.first.click()
            note_area.first.fill(self.note_message)
            print(f"  Note filled: {self.note_message[:40]!r}...")

            # 4) Wait until the Send button becomes enabled
            #    (LinkedIn keeps it disabled until the textarea has content)
            send_btn = self.page.locator('button[aria-label="Send invitation"]')
            send_btn.first.wait_for(state="visible", timeout=8000)

            # Poll until it's no longer disabled (max ~5s)
            for _ in range(25):
                try:
                    disabled = send_btn.first.get_attribute("disabled")
                    if disabled is None:
                        break
                except Exception:
                    pass
                sleep(0.2)
            else:
                print("  Send button stayed disabled. Aborting note send.")
                return False

            send_btn.first.click(timeout=5000)
            print("  Clicked 'Send invitation'.")
            self.page.wait_for_timeout(1500)
            return True

        except Exception as e:
            print(f"  Send-with-note failed: {e}")
            # Try to dismiss the modal so the outer loop can continue
            try:
                dismiss = self.page.locator(
                    'button[aria-label="Dismiss"], '
                    'button[aria-label="Cancel"], '
                    'button[aria-label="Close"]'
                )
                if dismiss.count() > 0 and dismiss.first.is_visible():
                    dismiss.first.click(timeout=2000)
                    sleep(1)
            except Exception:
                pass
            return False

    def _send_without_note(self) -> bool:
        """Click 'Send without a note'. Returns True on success."""
        try:
            btn = self.page.get_by_text("Send without a note", exact=True)
            btn.wait_for(state="visible", timeout=8000)
            btn.click(timeout=5000)
            self.page.wait_for_timeout(1500)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------- #
#  Entry point
# ---------------------------------------------------------------------- #
def main():
    # ---- gather inputs ----
    search_mode = input("Search mode (hashtag/people): ").strip().lower()
    if search_mode not in ("hashtag", "people"):
        print("Invalid mode. Use 'hashtag' or 'people'.")
        return

    location = input("Enter location filter (leave empty for none): ").strip()
    note_msg = input("Enter note message (leave empty to send without note): ").strip()

    people_list = []
    hashtag_val = ""

    if search_mode == "people":
        people_input = input(
            "Enter LinkedIn profile names/URLs to connect with "
            "(comma-separated, or leave empty for all on page): "
        ).strip()
        if people_input:
            people_list = [p.strip() for p in people_input.split(",") if p.strip()]
    else:
        hashtag_val = input("Enter your hashtag: ").strip().lstrip("#")
        if not hashtag_val:
            print("Please enter a valid hashtag.")
            return

    # ---- run ----
    start_chrome()

    with sync_playwright() as playwright:
        browser, driver = setup_browser(playwright)
        print("Connected to Chrome successfully.")
        print("Current page:", driver.url)

        linkedin = Linkedin(driver, playwright)
        linkedin.search_type = search_mode
        linkedin.hashtag_value = hashtag_val
        linkedin.location_filter = location
        linkedin.note_message = note_msg
        linkedin.people_list = people_list
        # Exact name matching is on by default in people mode
        linkedin.filter_by_name = True

        try:
            linkedin.main()
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            try:
                input("\nPress Enter to exit...")
            except (KeyboardInterrupt, EOFError):
                pass
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()