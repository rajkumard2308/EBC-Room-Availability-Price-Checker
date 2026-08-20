import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
import os
import platform

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
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

# Individual offer card
ROOM_CARD_SELECTOR = "div.card-list.otartrow"

# Price inside each card
PRICE_SELECTOR = "#rmamt_avg_night"


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

JSON_FILE = OUTPUT_DIR / "rooms.json"
CSV_FILE = OUTPUT_DIR / "rooms.csv"

SCREENSHOT_BEFORE = (
    OUTPUT_DIR / "before_availability.png"
)

SCREENSHOT_AFTER = (
    OUTPUT_DIR / "per_room_per_night.png"
)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# ============================================================
# DATE VALIDATION
# ============================================================

def validate_dates(
    check_in,
    check_out
):

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

    return (
        check_in_date,
        check_out_date
    )


# ============================================================
# DATE PICKER
# ============================================================

def wait_for_calendar(page):

    selectors = [
        "#ui-datepicker-div",
        ".ui-datepicker",
        ".ui-datepicker-calendar",
        "[class*='datepicker']"
    ]

    for _ in range(20):

        for selector in selectors:

            try:

                calendars = page.locator(
                    selector
                )

                for i in range(
                    calendars.count()
                ):

                    calendar = calendars.nth(i)

                    if calendar.is_visible():

                        return calendar

            except Exception:

                continue

        page.wait_for_timeout(300)

    raise RuntimeError(
        "Date calendar was not found."
    )


def get_calendar_month_year(
    calendar
):

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

                year = int(
                    year_text
                )

    except Exception:

        pass

    return (
        month_name,
        year
    )


def get_calendar_current_date(
    calendar
):

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
        "December"
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

        return (
            year,
            month
        )

    now = datetime.now()

    return (
        now.year,
        now.month
    )


def click_calendar_navigation(
    calendar,
    direction
):

    if direction == "next":

        selectors = [
            ".ui-datepicker-next",
            "a.ui-datepicker-next"
        ]

    else:

        selectors = [
            ".ui-datepicker-prev",
            "a.ui-datepicker-prev"
        ]

    for selector in selectors:

        try:

            buttons = calendar.locator(
                selector
            )

            for i in range(
                buttons.count()
            ):

                button = buttons.nth(i)

                if not button.is_visible():
                    continue

                if not button.is_enabled():
                    continue

                button.click()

                return True

        except Exception:

            continue

    return False


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
        +
        (target_month - current_month)
    )

    print(
        f"Current calendar: "
        f"{current_month:02d}/{current_year}"
    )

    print(
        f"Target calendar: "
        f"{target_month:02d}/{target_year}"
    )

    print(
        f"Month difference: "
        f"{difference}"
    )

    if difference == 0:

        return

    direction = (
        "next"
        if difference > 0
        else "previous"
    )

    for _ in range(
        abs(difference)
    ):

        calendar = wait_for_calendar(
            page
        )

        clicked = click_calendar_navigation(
            calendar,
            direction
        )

        if not clicked:

            raise RuntimeError(
                f"Could not click "
                f"calendar {direction}."
            )

        page.wait_for_timeout(400)


def click_calendar_day(
    page,
    calendar,
    target_date
):

    target_day = str(
        target_date.day
    )

    print(
        f"Selecting day: {target_day}"
    )

    links = calendar.locator(
        "a.ui-state-default"
    )

    for i in range(
        links.count()
    ):

        try:

            link = links.nth(i)

            if not link.is_visible():

                continue

            text = clean_text(
                link.inner_text()
            )

            if text != target_day:

                continue

            classes = (
                link.get_attribute(
                    "class"
                )
                or ""
            )

            if (
                "ui-priority-secondary"
                in classes
            ):

                continue

            link.click()

            page.wait_for_timeout(
                700
            )

            print(
                f"✓ Selected "
                f"{target_date.strftime('%d-%m-%Y')}"
            )

            return

        except Exception:

            continue

    raise RuntimeError(
        f"Day {target_day} "
        f"was not found."
    )


def select_date(
    page,
    input_xpath,
    target_date,
    field_name
):

    print("\n")
    print("=" * 70)

    print(
        f"SELECTING {field_name}"
    )

    print("=" * 70)

    date_input = page.locator(
        f"xpath={input_xpath}"
    )

    date_input.wait_for(
        state="visible",
        timeout=30000
    )

    date_input.scroll_into_view_if_needed()

    date_input.click()

    page.wait_for_timeout(
        700
    )

    calendar = wait_for_calendar(
        page
    )

    navigate_calendar(
        page,
        calendar,
        target_date
    )

    calendar = wait_for_calendar(
        page
    )

    click_calendar_day(
        page,
        calendar,
        target_date
    )

    page.wait_for_timeout(
        500
    )

    actual_value = (
        date_input.input_value()
    )

    print(
        f"{field_name} value: "
        f"{actual_value}"
    )

    return actual_value


def enter_dates(
    page,
    check_in,
    check_out
):

    check_in_date = datetime.strptime(
        check_in,
        "%d-%m-%Y"
    )

    check_out_date = datetime.strptime(
        check_out,
        "%d-%m-%Y"
    )

    actual_checkin = select_date(
        page,
        CHECKIN_XPATH,
        check_in_date,
        "CHECK-IN"
    )

    actual_checkout = select_date(
        page,
        CHECKOUT_XPATH,
        check_out_date,
        "CHECK-OUT"
    )

    print("\n")
    print("=" * 70)
    print("DATE VERIFICATION")
    print("=" * 70)

    print(
        f"Expected Check-in : "
        f"{check_in}"
    )

    print(
        f"Actual Check-in   : "
        f"{actual_checkin}"
    )

    print(
        f"Expected Check-out: "
        f"{check_out}"
    )

    print(
        f"Actual Check-out  : "
        f"{actual_checkout}"
    )

    if (
        not actual_checkin
        or not actual_checkout
    ):

        raise RuntimeError(
            "Date selection failed."
        )

    print(
        "\n✓ Dates selected successfully."
    )


# ============================================================
# CHECK AVAILABILITY
# ============================================================

def click_check_availability(
    page
):

    print("\n")
    print("=" * 70)
    print("CHECK AVAILABILITY")
    print("=" * 70)

    button = page.locator(
        f"xpath={AVAILABILITY_XPATH}"
    )

    button.wait_for(
        state="visible",
        timeout=30000
    )

    button.scroll_into_view_if_needed()

    page.wait_for_timeout(
        500
    )

    button.click()

    print(
        "✓ Check Availability clicked."
    )


# ============================================================
# WAIT FOR ROOM RESULTS
# ============================================================

def wait_for_results(
    page
):

    print("\n")
    print("=" * 70)
    print("WAITING FOR ROOM RESULTS")
    print("=" * 70)

    try:

        page.wait_for_load_state(
            "domcontentloaded",
            timeout=30000
        )

    except PlaywrightTimeoutError:

        pass

    try:

        page.wait_for_load_state(
            "networkidle",
            timeout=30000
        )

    except PlaywrightTimeoutError:

        pass

    page.locator(
        ROOM_CARD_SELECTOR
    ).first.wait_for(
        state="visible",
        timeout=60000
    )

    page.wait_for_timeout(
        2000
    )

    print(
        "✓ Room results loaded."
    )


# ============================================================
# PER ROOM PER NIGHT
# ============================================================

def click_per_room_per_night(
    page
):

    print("\n")
    print("=" * 70)
    print("PER ROOM PER NIGHT")
    print("=" * 70)

    button = page.locator(
        PER_ROOM_NIGHT_SELECTOR
    )

    button.wait_for(
        state="visible",
        timeout=30000
    )

    button.scroll_into_view_if_needed()

    page.wait_for_timeout(
        1000
    )

    print(
        "Clicking #pnl_avg_blk ..."
    )

    button.click()

    page.wait_for_timeout(
        2000
    )

    print(
        "✓ Per Room Per Night selected."
    )


# ============================================================
# LOAD ALL CARDS
# ============================================================

def load_all_rooms(
    page
):

    print("\n")
    print("=" * 70)
    print("LOADING ALL ROOM CARDS")
    print("=" * 70)

    previous_height = 0
    stable_rounds = 0

    for scroll_number in range(
        60
    ):

        card_count = page.locator(
            ROOM_CARD_SELECTOR
        ).count()

        print(
            f"Scroll "
            f"{scroll_number + 1:02d} | "
            f"Cards: {card_count}"
        )

        page.evaluate(
            """
            () => {
                window.scrollBy(
                    0,
                    Math.floor(
                        window.innerHeight * 0.85
                    )
                );
            }
            """
        )

        page.wait_for_timeout(
            800
        )

        current_height = page.evaluate(
            """
            () =>
                document.documentElement.scrollHeight
            """
        )

        if current_height == previous_height:

            stable_rounds += 1

        else:

            stable_rounds = 0

        previous_height = current_height

        at_bottom = page.evaluate(
            """
            () => (
                window.innerHeight +
                window.scrollY >=
                document.documentElement.scrollHeight - 30
            )
            """
        )

        if (
            at_bottom
            and stable_rounds >= 2
        ):

            break

    page.wait_for_timeout(
        1000
    )

    total = page.locator(
        ROOM_CARD_SELECTOR
    ).count()

    print(
        f"\n✓ Total cards loaded: "
        f"{total}"
    )

    return total


# ============================================================
# GET CARD NAME
# ============================================================

def get_card_name(
    card
):

    try:

        heading = card.locator(
            "h3"
        ).first

        if heading.count() == 0:

            return ""

        return clean_text(
            heading.inner_text()
        )

    except Exception:

        return ""


# ============================================================
# GET CARD PRICE
# ============================================================

def get_card_price(
    card
):

    try:

        price_element = card.locator(
            PRICE_SELECTOR
        ).first

        if price_element.count() == 0:

            return ""

        if not price_element.is_visible():

            return ""

        return clean_text(
            price_element.inner_text()
        )

    except Exception:

        return ""


# ============================================================
# CONVERT PRICE
# ============================================================

def convert_price(
    price_text
):

    if not price_text:

        return None

    cleaned = (
        price_text
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

    # Round DOWN to the nearest 100.
    #
    # 7680  -> 7600
    # 9220  -> 9200
    # 11530 -> 11500
    # 12300 -> 12300
    # 15370 -> 15300
    # 33050 -> 33000

    return (
        int(value) // 100
    ) * 100


# ============================================================
# FIND ROOM SECTIONS
# ============================================================

def find_room_sections(
    page
):
    """
    Find containers containing the offer cards
    for each physical room.

    The scraper does NOT use offer names to decide
    which card is first.

    Each detected section is processed separately.
    """

    cards = page.locator(
        ROOM_CARD_SELECTOR
    )

    total = cards.count()

    sections = []
    seen = set()

    for i in range(total):

        try:

            card = cards.nth(i)

            ancestors = card.locator(
                "xpath=ancestor::*"
            )

            candidates = []

            for j in range(
                ancestors.count()
            ):

                ancestor = ancestors.nth(j)

                try:

                    inside_cards = ancestor.locator(
                        ROOM_CARD_SELECTOR
                    )

                    count = inside_cards.count()

                    # A room section normally has
                    # multiple offer cards.
                    #
                    # Do not accept a container holding
                    # all 28 cards.
                    if (
                        2 <= count <= 6
                    ):

                        candidates.append(
                            ancestor
                        )

                except Exception:

                    continue

            if not candidates:

                continue

            # Smallest suitable container
            section = candidates[0]

            try:

                key = section.evaluate(
                    """
                    (element) => {

                        if (!element.dataset.roomScraperId) {

                            element.dataset.roomScraperId =
                                "room_" +
                                Math.random()
                                    .toString(36)
                                    .substring(2, 12);
                        }

                        return element.dataset.roomScraperId;
                    }
                    """
                )

            except Exception:

                key = str(
                    id(section)
                )

            if key in seen:

                continue

            seen.add(key)

            sections.append(
                section
            )

        except Exception:

            continue

    return sections


# ============================================================
# SCRAPE FIRST CARD OF EVERY ROOM
# ============================================================

def scrape_rooms(
    page
):

    print("\n")
    print("=" * 70)
    print(
        "SCRAPING FIRST CARD OF EVERY ROOM"
    )
    print("=" * 70)

    load_all_rooms(
        page
    )

    sections = find_room_sections(
        page
    )

    print(
        f"\nRoom sections detected: "
        f"{len(sections)}"
    )

    rooms = []

    for section_index, section in enumerate(
        sections,
        start=1
    ):

        try:

            cards = section.locator(
                ROOM_CARD_SELECTOR
            )

            card_count = cards.count()

            if card_count == 0:

                continue

            print("\n")
            print("=" * 70)

            print(
                f"ROOM SECTION #{section_index}"
            )

            print(
                f"Cards in section: "
                f"{card_count}"
            )

            # =================================================
            # VERY IMPORTANT
            #
            # ONLY FIRST CARD.
            #
            # We DO NOT search card 2/3/4.
            # =================================================

            first_card = cards.first

            name = get_card_name(
                first_card
            )

            website_price = get_card_price(
                first_card
            )

            price = convert_price(
                website_price
            )

            print(
                "Selected: FIRST CARD ONLY"
            )

            print(
                f"Name: {name}"
            )

            print(
                f"Website price: "
                f"{website_price}"
            )

            # ------------------------------------------------
            # If first card unavailable:
            # skip the room entirely.
            # ------------------------------------------------

            if not name:

                print(
                    "SKIPPED - no room name."
                )

                continue

            if price is None:

                print(
                    "SKIPPED - first card "
                    "has no valid price."
                )

                continue

            # ------------------------------------------------
            # ONLY name + price
            # ------------------------------------------------

            rooms.append(
                {
                    "name": name,
                    "price": price
                }
            )

            print(
                f"Stored price: {price}"
            )

            print("=" * 70)

        except Exception as error:

            print(
                f"Error processing "
                f"section #{section_index}: "
                f"{error}"
            )

    print("\n")
    print("=" * 70)
    print("FINAL ROOM RESULT")
    print("=" * 70)

    print(
        f"Rooms stored: "
        f"{len(rooms)}"
    )

    print("=" * 70)

    for index, room in enumerate(
        rooms,
        start=1
    ):

        print(
            f"{index}. "
            f"{room['name']} "
            f"-> "
            f"{room['price']}"
        )

    return rooms


# ============================================================
# FORMAT FINAL ROOM AVAILABILITY
# ============================================================

def format_room_availability(
    data
):
    """
    Convert scraped JSON into the required
    natural-language room availability response.

    Villa price is multiplied by 2.
    """

    rooms = data.get(
        "rooms",
        []
    )

    room_prices = {}

    for room in rooms:

        name = room.get(
            "name",
            ""
        )

        price = room.get(
            "price"
        )

        # Never process invalid records
        if not name:
            continue

        if price is None:
            continue

        name_lower = name.lower()

        # IMPORTANT:
        # Check specific room names first.

        if "surveyor suite" in name_lower:

            room_prices[
                "surveyor_suite"
            ] = price

        elif "surveyor" in name_lower:

            room_prices[
                "surveyor"
            ] = price

        elif "camper" in name_lower:

            room_prices[
                "camper"
            ] = price

        elif "glamper" in name_lower:

            room_prices[
                "glamper"
            ] = price

        elif "zenith" in name_lower:

            room_prices[
                "zenith"
            ] = price

        elif "twin luxury" in name_lower:

            room_prices[
                "twin_luxury"
            ] = price

        elif "villa" in name_lower:

            room_prices[
                "villa"
            ] = price

    # --------------------------------------------------------
    # Format numbers
    # --------------------------------------------------------

    def money(value):

        return f"{value:,}"

    # --------------------------------------------------------
    # Build response
    # --------------------------------------------------------

    lines = [
        "For , Here is the Room availability with prices below:"
    ]

    # Camper
    if "camper" in room_prices:

        lines.append(
            "The Camper room (2 occupants) "
            "is available for "
            f"Rs. {money(room_prices['camper'])} "
            "plus taxes per night."
        )

    # Glamper
    if "glamper" in room_prices:

        lines.append(
            "The Glamper room (2 occupants) "
            "is available for "
            f"Rs. {money(room_prices['glamper'])} "
            "plus taxes per night. "
            "(We have 4 Glamper rooms)"
        )

    # Surveyor
    if "surveyor" in room_prices:

        lines.append(
            "The Surveyor room (2 occupants) "
            "is available for "
            f"Rs. {money(room_prices['surveyor'])} "
            "plus taxes per night."
        )

    # Surveyor Suite
    if "surveyor_suite" in room_prices:

        lines.append(
            "The Surveyor suite room (2 occupants) "
            "is available for "
            f"Rs. {money(room_prices['surveyor_suite'])} "
            "plus taxes per night."
        )

    # Zenith
    if "zenith" in room_prices:

        lines.append(
            "The Zenith luxury cottage (2 occupants) "
            "is available for "
            f"Rs. {money(room_prices['zenith'])} "
            "plus taxes per night."
        )

    # Twin Luxury
    if "twin_luxury" in room_prices:

        lines.append(
            "The twin luxury cottage "
            "(2 occupants / Room) "
            "is available for "
            f"Rs. {money(room_prices['twin_luxury'])} "
            "plus taxes per night. "
            "(2 Rooms next to each other)"
        )

    # Villa
    if "villa" in room_prices:

        # IMPORTANT:
        # Villa price = scraped price × 2

        villa_price = (
            room_prices["villa"] * 2
        )

        lines.append(
            "The Villa (2 occupants/room) "
            "is available for "
            f"Rs. {money(villa_price)} "
            "plus taxes per night. "
            "(2 Rooms villa)"
        )

    return "\n".join(
        lines
    )


# ============================================================
# SAVE JSON
# ============================================================

def save_json(
    rooms,
    check_in,
    check_out
):

    output = {
        "check_in": check_in,
        "check_out": check_out,
        "rooms": rooms
    }

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\n✓ JSON saved: "
        f"{JSON_FILE}"
    )


# ============================================================
# SAVE CSV
# ============================================================

def save_csv(
    rooms
):

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
                "price"
            ]
        )

        writer.writeheader()

        for room in rooms:

            writer.writerow(
                room
            )

    print(
        f"✓ CSV saved: "
        f"{CSV_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():
    # Keep console output UTF-8 on Windows.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


    parser = argparse.ArgumentParser(
        description=(
            "Everest Base Camp "
            "Room Price Scraper"
        )
    )

    parser.add_argument(
        "--check-in",
        required=True,
        help="Check-in date DD-MM-YYYY"
    )

    parser.add_argument(
        "--check-out",
        required=True,
        help="Check-out date DD-MM-YYYY"
    )

    args = parser.parse_args()

    check_in = args.check_in
    check_out = args.check_out

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validate_dates(
        check_in,
        check_out
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)

    print(
        "EVEREST BASE CAMP"
    )

    print(
        "ROOM PRICE SCRAPER"
    )

    print("=" * 70)

    print(
        f"\nCheck-in : {check_in}"
    )

    print(
        f"Check-out: {check_out}"
    )

    print("\nRULE:")

    print(
        "Camper       -> FIRST CARD"
    )

    print(
        "Glamper      -> FIRST CARD"
    )

    print(
        "Surveyor     -> FIRST CARD"
    )

    print(
        "Surveyor Suite -> FIRST CARD"
    )

    print(
        "Zenith       -> FIRST CARD"
    )

    print(
        "Twin Luxury  -> FIRST CARD"
    )

    print(
        "Villa        -> FIRST CARD"
    )

    print(
        "Unavailable room -> NOT STORED"
    )

    print(
        "No NULL / None values"
    )

    # ========================================================
    # PLAYWRIGHT
    # ========================================================

    with sync_playwright() as playwright:

        # ============================================================
        # LAUNCH BROWSER
        # Works on both Windows localhost and Streamlit Cloud Linux
        # ============================================================

        system_name = platform.system()

        if system_name == "Windows":

            print("Running on Windows")

            browser = playwright.chromium.launch(
                headless=False
            )

        else:

            print("Running on Linux / Streamlit Cloud")

            chromium_path = "/usr/bin/chromium"

            browser = playwright.chromium.launch(
                executable_path=chromium_path,
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )

        context = browser.new_context(
            viewport={
                "width": 1440,
                "height": 900
            },
            locale="en-IN"
        )

        page = context.new_page()

        # ====================================================
        # OPEN WEBSITE
        # ====================================================

        print(
            "\nOpening website..."
        )

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        print(
            "✓ Website opened."
        )

        page.wait_for_timeout(
            5000
        )

        # ====================================================
        # SELECT DATES
        # ====================================================

        enter_dates(
            page,
            check_in,
            check_out
        )

        page.screenshot(
            path=str(
                SCREENSHOT_BEFORE
            ),
            full_page=True
        )

        # ====================================================
        # CHECK AVAILABILITY
        # ====================================================

        click_check_availability(
            page
        )

        # ====================================================
        # WAIT FOR RESULTS
        # ====================================================

        wait_for_results(
            page
        )

        # ====================================================
        # PER ROOM PER NIGHT
        # ====================================================

        click_per_room_per_night(
            page
        )

        page.screenshot(
            path=str(
                SCREENSHOT_AFTER
            ),
            full_page=True
        )

        # ====================================================
        # SCRAPE ROOMS
        # ====================================================

        rooms = scrape_rooms(
            page
        )

        # ====================================================
        # SAVE RAW ROOM DATA
        # ====================================================

        save_json(
            rooms,
            check_in,
            check_out
        )

        save_csv(
            rooms
        )

        # ====================================================
        # CREATE FINAL TEXT
        # ====================================================

        data = {
            "check_in": check_in,
            "check_out": check_out,
            "rooms": rooms
        }

        availability_text = (
            format_room_availability(
                data
            )
        )

        # ====================================================
        # PRINT FINAL TEXT
        # ====================================================

        print("\n")
        print("=" * 70)
        print(
            "ROOM AVAILABILITY"
        )
        print("=" * 70)

        print(
            availability_text
        )

        print("=" * 70)

        # ====================================================
        # SAVE TEXT
        # ====================================================

        TEXT_FILE = (
            OUTPUT_DIR /
            "room_availability.txt"
        )

        with open(
            TEXT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                availability_text
            )

        print(
            f"\n✓ Availability text saved: "
            f"{TEXT_FILE}"
        )

        # ====================================================
        # COMPLETED
        # ====================================================

        print("\n")
        print("=" * 70)
        print(
            "SCRAPING COMPLETED"
        )
        print("=" * 70)

        print(
            f"Total rooms stored: "
            f"{len(rooms)}"
        )

        browser.close()

        print(
            "✓ Browser closed."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()