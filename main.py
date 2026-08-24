import argparse
import csv
import json
import os
import platform
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# ============================================================
# CONFIGURATION
# ============================================================

URL = (
    "https://live.ipms247.com/booking/"
    "book-rooms-everestbasecamp"
)

CHECKIN_XPATH = '//*[@id="eZ_chkin"]'
CHECKOUT_XPATH = '//*[@id="eZ_chkout"]'
AVAILABILITY_XPATH = '//*[@id="book"]'

PER_ROOM_NIGHT_SELECTOR = "#pnl_avg_blk"

# Room cards
ROOM_CARD_SELECTOR = "div.card-list.otartrow"

# Price shown after "Per Room Per Night"
PRICE_SELECTOR = "#rmamt_avg_night"


# ============================================================
# PERFORMANCE SETTINGS
# ============================================================

# Maximum number of lazy-load scrolls.
MAX_SCROLLS = 12

# Small delay after scrolling.
SCROLL_WAIT_MS = 250

# Maximum wait for room cards.
RESULT_TIMEOUT_MS = 45000

# Maximum page navigation timeout.
PAGE_TIMEOUT_MS = 60000


# ============================================================
# ROOM ORDER
# ============================================================

ROOM_TYPE_ORDER = [
    "camper",
    "glamper",
    "surveyor",
    "surveyor_suite",
    "zenith",
    "twin_luxury",
    "villa",
]


# ============================================================
# OPTIONAL OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

JSON_FILE = OUTPUT_DIR / "rooms.json"
CSV_FILE = OUTPUT_DIR / "rooms.csv"
TEXT_FILE = OUTPUT_DIR / "room_availability.txt"


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text)
    ).strip()


# ============================================================
# DATE VALIDATION
# ============================================================

def validate_dates(check_in, check_out):

    try:
        check_in_date = datetime.strptime(
            check_in,
            "%d-%m-%Y"
        )
    except ValueError:
        raise ValueError(
            "Invalid check-in date. "
            "Use DD-MM-YYYY."
        )

    try:
        check_out_date = datetime.strptime(
            check_out,
            "%d-%m-%Y"
        )
    except ValueError:
        raise ValueError(
            "Invalid check-out date. "
            "Use DD-MM-YYYY."
        )

    if check_out_date <= check_in_date:
        raise ValueError(
            "Check-out must be after check-in."
        )

    return check_in_date, check_out_date


# ============================================================
# DATE DISPLAY
# ============================================================

def format_short_date(date_text):
    """
    23-08-2026 -> 23Aug
    """

    date_obj = datetime.strptime(
        date_text,
        "%d-%m-%Y"
    )

    return date_obj.strftime("%d%b")


def format_date_range(check_in, check_out):
    """
    23-08-2026, 25-08-2026
    ->
    23Aug-25Aug
    """

    return (
        f"{format_short_date(check_in)}-"
        f"{format_short_date(check_out)}"
    )


# ============================================================
# CALENDAR
# ============================================================

def wait_for_calendar(page):

    selectors = [
        "#ui-datepicker-div",
        ".ui-datepicker",
        ".ui-datepicker-calendar",
        "[class*='datepicker']",
    ]

    for _ in range(15):

        for selector in selectors:

            try:

                calendars = page.locator(
                    selector
                )

                count = calendars.count()

                for i in range(count):

                    calendar = calendars.nth(i)

                    if calendar.is_visible():
                        return calendar

            except Exception:
                continue

        page.wait_for_timeout(150)

    raise RuntimeError(
        "Date calendar was not found."
    )


# ============================================================
# CALENDAR MONTH / YEAR
# ============================================================

def get_calendar_month_year(calendar):

    month_name = None
    year = None

    try:

        element = calendar.locator(
            ".ui-datepicker-month"
        ).first

        if element.count():

            month_name = clean_text(
                element.inner_text()
            )

    except Exception:
        pass

    try:

        element = calendar.locator(
            ".ui-datepicker-year"
        ).first

        if element.count():

            year_text = clean_text(
                element.inner_text()
            )

            if year_text.isdigit():
                year = int(year_text)

    except Exception:
        pass

    return month_name, year


# ============================================================
# CURRENT CALENDAR DATE
# ============================================================

def get_calendar_current_date(calendar):

    month_name, year = (
        get_calendar_month_year(
            calendar
        )
    )

    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    if (
        month_name
        and year
        and month_name in months
    ):

        month = (
            months.index(
                month_name
            ) + 1
        )

        return year, month

    now = datetime.now()

    return now.year, now.month


# ============================================================
# CALENDAR NAVIGATION
# ============================================================

def click_calendar_navigation(
    calendar,
    direction
):

    if direction == "next":

        selectors = [
            ".ui-datepicker-next",
            "a.ui-datepicker-next",
        ]

    else:

        selectors = [
            ".ui-datepicker-prev",
            "a.ui-datepicker-prev",
        ]

    for selector in selectors:

        try:

            buttons = calendar.locator(
                selector
            )

            count = buttons.count()

            for i in range(count):

                button = buttons.nth(i)

                if not button.is_visible():
                    continue

                if not button.is_enabled():
                    continue

                button.click(
                    timeout=3000
                )

                return True

        except Exception:
            continue

    return False


# ============================================================
# NAVIGATE TO TARGET MONTH
# ============================================================

def navigate_calendar(
    page,
    calendar,
    target_date
):

    target_year = target_date.year
    target_month = target_date.month

    current_year, current_month = (
        get_calendar_current_date(
            calendar
        )
    )

    difference = (
        (target_year - current_year) * 12
        + (target_month - current_month)
    )

    if difference == 0:
        return

    direction = (
        "next"
        if difference > 0
        else "previous"
    )

    for _ in range(abs(difference)):

        calendar = wait_for_calendar(page)

        if not click_calendar_navigation(
            calendar,
            direction
        ):
            raise RuntimeError(
                "Could not navigate calendar."
            )

        page.wait_for_timeout(100)


# ============================================================
# SELECT DATE
# ============================================================

def select_date(
    page,
    input_xpath,
    date_text
):

    target_date = datetime.strptime(
        date_text,
        "%d-%m-%Y"
    )

    # Click input
    field = page.locator(
        f"xpath={input_xpath}"
    )

    field.wait_for(
        state="visible",
        timeout=15000
    )

    field.click()

    page.wait_for_timeout(150)

    # Find calendar
    calendar = wait_for_calendar(page)

    # Navigate month
    navigate_calendar(
        page,
        calendar,
        target_date
    )

    calendar = wait_for_calendar(page)

    # --------------------------------------------------------
    # Find correct day
    # --------------------------------------------------------

    day = target_date.day

    selectors = [
        f"td[data-handler='selectDay'] a:text-is('{day}')",
        f"td a:text-is('{day}')",
        f"td[data-handler='selectDay'] a:has-text('{day}')",
    ]

    selected = False

    for selector in selectors:

        try:

            elements = calendar.locator(
                selector
            )

            count = elements.count()

            for i in range(count):

                element = elements.nth(i)

                if not element.is_visible():
                    continue

                # Avoid days belonging to
                # previous/next month.
                try:

                    parent = element.locator(
                        ".."
                    )

                    class_name = (
                        parent.get_attribute(
                            "class"
                        )
                        or ""
                    )

                    if (
                        "ui-datepicker-other-month"
                        in class_name
                    ):
                        continue

                except Exception:
                    pass

                element.click(
                    timeout=5000
                )

                selected = True
                break

            if selected:
                break

        except Exception:
            continue

    if not selected:
        raise RuntimeError(
            f"Could not select date {date_text}"
        )

    page.wait_for_timeout(200)

    # Verify value
    actual_value = clean_text(
        field.input_value()
    )

    if actual_value != date_text:

        # Sometimes the website formats
        # the date slightly differently.
        # Check normalized dates.
        try:

            actual_date = datetime.strptime(
                actual_value,
                "%d-%m-%Y"
            )

            if actual_date.date() != target_date.date():

                raise RuntimeError(
                    f"Date verification failed. "
                    f"Expected {date_text}, "
                    f"got {actual_value}"
                )

        except ValueError:

            raise RuntimeError(
                f"Date verification failed. "
                f"Expected {date_text}, "
                f"got {actual_value}"
            )

    return actual_value


# ============================================================
# ENTER DATES
# ============================================================

def enter_dates(
    page,
    check_in,
    check_out
):

    select_date(
        page,
        CHECKIN_XPATH,
        check_in
    )

    select_date(
        page,
        CHECKOUT_XPATH,
        check_out
    )

    # Final verification
    actual_check_in = clean_text(
        page.locator(
            f"xpath={CHECKIN_XPATH}"
        ).input_value()
    )

    actual_check_out = clean_text(
        page.locator(
            f"xpath={CHECKOUT_XPATH}"
        ).input_value()
    )

    if actual_check_in != check_in:
        raise RuntimeError(
            f"Check-in verification failed: "
            f"{actual_check_in}"
        )

    if actual_check_out != check_out:
        raise RuntimeError(
            f"Check-out verification failed: "
            f"{actual_check_out}"
        )


# ============================================================
# CHECK AVAILABILITY
# ============================================================

def click_check_availability(page):

    button = page.locator(
        f"xpath={AVAILABILITY_XPATH}"
    )

    button.wait_for(
        state="visible",
        timeout=15000
    )

    button.click(
        timeout=10000
    )


# ============================================================
# WAIT FOR ROOM RESULTS
# ============================================================

def wait_for_rooms(page):

    # DO NOT use networkidle.
    #
    # Booking websites often keep making
    # background requests.
    #
    # We only wait for the actual room card.

    cards = page.locator(
        ROOM_CARD_SELECTOR
    )

    try:

        cards.first.wait_for(
            state="visible",
            timeout=RESULT_TIMEOUT_MS
        )

    except PlaywrightTimeoutError:

        raise RuntimeError(
            "Room results did not load "
            "within the allowed time."
        )

    # Small stabilization delay.
    page.wait_for_timeout(700)


# ============================================================
# PER ROOM PER NIGHT
# ============================================================

def select_per_room_per_night(page):

    selector = page.locator(
        PER_ROOM_NIGHT_SELECTOR
    )

    selector.wait_for(
        state="visible",
        timeout=15000
    )

    selector.click(
        timeout=5000
    )

    page.wait_for_timeout(500)

    # Wait until at least one price exists.
    try:

        page.locator(
            PRICE_SELECTOR
        ).first.wait_for(
            state="visible",
            timeout=15000
        )

    except PlaywrightTimeoutError:

        # The price may still exist inside
        # cards even if the direct selector
        # isn't immediately visible.
        page.wait_for_timeout(1000)


# ============================================================
# LOAD ALL ROOMS
# ============================================================

def load_all_rooms(page):

    cards = page.locator(
        ROOM_CARD_SELECTOR
    )

    previous_count = 0
    stable_rounds = 0

    for scroll_number in range(
        MAX_SCROLLS
    ):

        current_count = cards.count()

        # Scroll near bottom.
        page.evaluate(
            """
            () => {
                window.scrollTo(
                    0,
                    document.body.scrollHeight
                );
            }
            """
        )

        page.wait_for_timeout(
            SCROLL_WAIT_MS
        )

        new_count = cards.count()

        if new_count == previous_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        previous_count = new_count

        # Once no new cards appear twice,
        # stop scrolling.
        if stable_rounds >= 2:
            break

    return cards.count()


# ============================================================
# CARD NAME
# ============================================================

def get_card_name(card):

    selectors = [
        "h3",
        ".room-name",
        ".room-title",
        "[class*='room-name']",
        "[class*='room-title']",
    ]

    for selector in selectors:

        try:

            element = card.locator(
                selector
            ).first

            if element.count() == 0:
                continue

            if not element.is_visible():
                continue

            text = clean_text(
                element.inner_text()
            )

            if text:
                return text

        except Exception:
            continue

    # Fallback:
    # Search text around likely title.
    try:

        text = clean_text(
            card.inner_text()
        )

        lines = [
            clean_text(x)
            for x in text.split("\n")
            if clean_text(x)
        ]

        for line in lines:

            lower = line.lower()

            if any(
                word in lower
                for word in [
                    "camper",
                    "glamper",
                    "surveyor",
                    "zenith",
                    "twin luxury",
                    "villa",
                ]
            ):
                return line

    except Exception:
        pass

    return ""


# ============================================================
# CARD PRICE
# ============================================================

def get_card_price(card):

    selectors = [
        PRICE_SELECTOR,
        "#rmamt_avg_night",
        ".rmamt_avg_night",
        "[id*='rmamt_avg_night']",
    ]

    for selector in selectors:

        try:

            element = card.locator(
                selector
            ).first

            if element.count() == 0:
                continue

            text = clean_text(
                element.inner_text()
            )

            if text:
                return text

        except Exception:
            continue

    # Fallback:
    # Search card text for Rs price.
    try:

        text = clean_text(
            card.inner_text()
        )

        matches = re.findall(
            r"(?:Rs\.?|₹)\s*[\d,]+(?:\.\d+)?",
            text,
            flags=re.IGNORECASE
        )

        if matches:
            return matches[-1]

    except Exception:
        pass

    return ""


# ============================================================
# CONVERT PRICE
# ============================================================

def convert_price(price_text):

    if not price_text:
        return None

    cleaned = (
        str(price_text)
        .replace(",", "")
        .strip()
    )

    cleaned = re.sub(
        r"[^\d.]",
        "",
        cleaned
    )

    if not cleaned:
        return None

    try:

        value = float(
            cleaned
        )

    except ValueError:

        return None

    if value <= 0:
        return None

    # Round DOWN to nearest 100.
    #
    # 7687.50 -> 7600
    # 9225.00 -> 9200
    # 11530   -> 11500
    # 12300   -> 12300
    # 15370   -> 15300

    return (
        int(value) // 100
    ) * 100


# ============================================================
# ROOM TYPE
# ============================================================

def detect_room_type(name):

    name_lower = (
        name or ""
    ).lower()

    # IMPORTANT:
    # Surveyor Suite BEFORE Surveyor.
    if "surveyor suite" in name_lower:
        return "surveyor_suite"

    if "surveyor" in name_lower:
        return "surveyor"

    if "camper" in name_lower:
        return "camper"

    if "glamper" in name_lower:
        return "glamper"

    if "zenith" in name_lower:
        return "zenith"

    if "twin luxury" in name_lower:
        return "twin_luxury"

    if "villa" in name_lower:
        return "villa"

    return None


# ============================================================
# SCRAPE FIRST CARD PER ROOM TYPE
# ============================================================

def scrape_rooms(page):

    load_all_rooms(page)

    cards = page.locator(
        ROOM_CARD_SELECTOR
    )

    total_cards = cards.count()

    # Store ONLY first card for every room type.
    first_cards = {}

    for index in range(total_cards):

        try:

            card = cards.nth(index)

            name = get_card_name(
                card
            )

            if not name:
                continue

            room_type = detect_room_type(
                name
            )

            if not room_type:
                continue

            # Already got first card.
            if room_type in first_cards:
                continue

            first_cards[
                room_type
            ] = card

        except Exception:
            continue

    rooms = []

    # Fixed room order.
    for room_type in ROOM_TYPE_ORDER:

        if room_type not in first_cards:
            continue

        card = first_cards[
            room_type
        ]

        name = get_card_name(
            card
        )

        website_price = get_card_price(
            card
        )

        price = convert_price(
            website_price
        )

        # Never store null.
        if not name:
            continue

        if price is None:
            continue

        rooms.append(
            {
                "name": name,
                "price": price,
            }
        )

    return rooms


# ============================================================
# FORMAT AVAILABILITY
# ============================================================

def format_room_availability(
    rooms,
    check_in,
    check_out
):

    room_prices = {}

    for room in rooms:

        name = room.get(
            "name",
            ""
        )

        price = room.get(
            "price"
        )

        if not name:
            continue

        if price is None:
            continue

        room_type = detect_room_type(
            name
        )

        if room_type:
            room_prices[
                room_type
            ] = price

    def money(value):
        return f"{value:,}"

    date_range = format_date_range(
        check_in,
        check_out
    )

    lines = [
        f"For {date_range}, "
        "Here is the Room availability "
        "with prices below:"
    ]

    # Camper
    if "camper" in room_prices:

        lines.append(
            "The Camper room "
            "(2 occupants) is available "
            f"for Rs. {money(room_prices['camper'])} "
            "plus taxes per night."
        )

    # Glamper
    if "glamper" in room_prices:

        lines.append(
            "The Glamper room "
            "(2 occupants) is available "
            f"for Rs. {money(room_prices['glamper'])} "
            "plus taxes per night. "
            "(We have 4 Glamper rooms)"
        )

    # Surveyor
    if "surveyor" in room_prices:

        lines.append(
            "The Surveyor room "
            "(2 occupants) is available "
            f"for Rs. {money(room_prices['surveyor'])} "
            "plus taxes per night."
        )

    # Surveyor Suite
    if "surveyor_suite" in room_prices:

        lines.append(
            "The Surveyor suite room "
            "(2 occupants) is available "
            f"for Rs. "
            f"{money(room_prices['surveyor_suite'])} "
            "plus taxes per night."
        )

    # Zenith
    if "zenith" in room_prices:

        lines.append(
            "The Zenith luxury cottage "
            "(2 occupants) is available "
            f"for Rs. {money(room_prices['zenith'])} "
            "plus taxes per night."
        )

    # Twin Luxury
    if "twin_luxury" in room_prices:

        lines.append(
            "The twin luxury cottage "
            "(2 occupants / Room) is available "
            f"for Rs. "
            f"{money(room_prices['twin_luxury'])} "
            "plus taxes per night. "
            "(2 Rooms next to each other)"
        )

    # Villa
    if "villa" in room_prices:

        villa_price = (
            room_prices["villa"] * 2
        )

        lines.append(
            "The Villa "
            "(2 occupants/room) is available "
            f"for Rs. {money(villa_price)} "
            "plus taxes per night. "
            "(2 Rooms villa)"
        )

    return "\n".join(lines)


# ============================================================
# BROWSER LAUNCH
# ============================================================

def launch_browser(playwright):

    # Streamlit Cloud is Linux.
    #
    # Always run headless.
    #
    # First try system Chromium.
    # Then fallback to Playwright Chromium.

    chromium_paths = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]

    chromium_path = None

    for path in chromium_paths:

        if os.path.exists(path):

            chromium_path = path
            break

    browser_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-features=Translate",
        "--disable-extensions",
    ]

    if chromium_path:

        return playwright.chromium.launch(
            executable_path=chromium_path,
            headless=True,
            args=browser_args,
        )

    return playwright.chromium.launch(
        headless=True,
        args=browser_args,
    )


# ============================================================
# BLOCK UNNECESSARY RESOURCES
# ============================================================

def optimize_page(page):

    def handle_route(route):

        request = route.request

        resource_type = request.resource_type

        # We don't need these resources
        # for room names/prices.
        #
        # IMPORTANT:
        # Do NOT block scripts/XHR/fetch.
        # The booking system needs them.

        if resource_type in {
            "image",
            "media",
            "font",
        }:

            route.abort()
            return

        route.continue_()

    page.route(
        "**/*",
        handle_route
    )


# ============================================================
# SCRAPE AVAILABILITY
# ============================================================

def scrape_availability(
    check_in,
    check_out
):

    validate_dates(
        check_in,
        check_out
    )

    with sync_playwright() as playwright:

        browser = None

        try:

            browser = launch_browser(
                playwright
            )

            context = browser.new_context(
                viewport={
                    "width": 1366,
                    "height": 768,
                },
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                user_agent=(
                    "Mozilla/5.0 "
                    "(X11; Linux x86_64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/131.0.0.0 "
                    "Safari/537.36"
                ),
            )

            page = context.new_page()

            page.set_default_timeout(
                15000
            )

            page.set_default_navigation_timeout(
                PAGE_TIMEOUT_MS
            )

            # Optimize unnecessary resources.
            optimize_page(page)

            # ------------------------------------------------
            # OPEN WEBSITE
            # ------------------------------------------------

            page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=PAGE_TIMEOUT_MS
            )

            # Small initial wait only.
            page.wait_for_timeout(1000)

            # ------------------------------------------------
            # DATES
            # ------------------------------------------------

            enter_dates(
                page,
                check_in,
                check_out
            )

            # ------------------------------------------------
            # AVAILABILITY
            # ------------------------------------------------

            click_check_availability(
                page
            )

            # ------------------------------------------------
            # WAIT FOR ROOMS
            # ------------------------------------------------

            wait_for_rooms(
                page
            )

            # ------------------------------------------------
            # PER ROOM PER NIGHT
            # ------------------------------------------------

            select_per_room_per_night(
                page
            )

            # ------------------------------------------------
            # SCRAPE
            # ------------------------------------------------

            rooms = scrape_rooms(
                page
            )

            # ------------------------------------------------
            # FORMAT RESULT
            # ------------------------------------------------

            availability_text = (
                format_room_availability(
                    rooms,
                    check_in,
                    check_out
                )
            )

            result = {
                "check_in": check_in,
                "check_out": check_out,
                "rooms": rooms,
                "availability_text": availability_text,
            }

            return result

        finally:

            if browser:

                try:
                    browser.close()
                except Exception:
                    pass


# ============================================================
# SAVE JSON
# ============================================================

def save_json(result):

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(rooms):

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "name",
                "price",
            ]
        )

        writer.writeheader()

        for room in rooms:

            writer.writerow(
                room
            )


# ============================================================
# SAVE TEXT
# ============================================================

def save_text(text):

    with open(
        TEXT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(text)


# ============================================================
# COMMAND LINE VERSION
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Everest Base Camp "
            "Room Availability Scraper"
        )
    )

    parser.add_argument(
        "--check-in",
        required=True,
        help="DD-MM-YYYY"
    )

    parser.add_argument(
        "--check-out",
        required=True,
        help="DD-MM-YYYY"
    )

    args = parser.parse_args()

    result = scrape_availability(
        args.check_in,
        args.check_out
    )

    save_json(result)

    save_csv(
        result["rooms"]
    )

    save_text(
        result["availability_text"]
    )

    print()
    print("=" * 70)
    print("EVEREST BASE CAMP")
    print("=" * 70)

    print(
        result["availability_text"]
    )

    print()
    print(
        f"Rooms stored: "
        f"{len(result['rooms'])}"
    )

    print("=" * 70)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()