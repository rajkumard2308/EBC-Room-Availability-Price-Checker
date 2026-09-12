"""
Everest Base Camp - IPMS247 room availability client.

This Python version replaces the JavaScript fetch + Cheerio implementation
with requests + BeautifulSoup.

It directly calls the IPMS247 AJAX endpoint:
POST /booking/rmdetails

No Playwright or Chromium is required.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://live.ipms247.com/booking"
BOOKING_PAGE_URL = f"{BASE_URL}/book-rooms-everestbasecamp"
ROOM_DETAILS_URL = f"{BASE_URL}/rmdetails"

HOTEL_ID = "23400"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 45

ROOM_TYPE_ORDER = [
    "camper",
    "glamper",
    "surveyor",
    "surveyor_suite",
    "zenith",
    "twin_luxury",
    "villa",
]

MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


# ============================================================
# CUSTOM ERRORS
# ============================================================

class ValidationError(Exception):
    """Raised when user input is invalid."""


class UpstreamError(Exception):
    """Raised when the booking engine returns an error."""


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value: Any) -> str:
    """
    Normalize whitespace and trim text.
    """
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def money(value: int) -> str:
    """
    Format number using comma separators.

    Example:
        8450 -> "8,450"
    """
    return f"{value:,}"


# ============================================================
# DATE VALIDATION
# ============================================================

def parse_date(value: str, label: str) -> date:
    """
    Parse a date in DD-MM-YYYY format.
    """

    value = str(value or "").strip()

    if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", value):
        raise ValidationError(
            f"Invalid {label} date. Use DD-MM-YYYY."
        )

    try:
        parsed_date = datetime.strptime(
            value,
            "%d-%m-%Y",
        ).date()

    except ValueError as exc:
        raise ValidationError(
            f"Invalid {label} date. Use DD-MM-YYYY."
        ) from exc

    return parsed_date


def validate_dates(
    check_in: str,
    check_out: str,
) -> Dict[str, Any]:
    """
    Validate check-in and check-out dates.

    Returns:
        {
            "check_in_date": date,
            "check_out_date": date,
            "nights": int
        }
    """

    check_in_date = parse_date(
        check_in,
        "check-in",
    )

    check_out_date = parse_date(
        check_out,
        "check-out",
    )

    if check_out_date <= check_in_date:
        raise ValidationError(
            "Check-out must be after check-in."
        )

    nights = (check_out_date - check_in_date).days

    return {
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "nights": nights,
    }


# ============================================================
# DATE FORMATTING
# ============================================================

def format_short_date(value: date) -> str:
    """
    Convert date to:

        15 Sep
    """

    return f"{value.day:02d} {MONTHS[value.month - 1]}"


def format_date_range(
    check_in_date: date,
    check_out_date: date,
) -> str:
    """
    Convert dates to:

        15 Sep - 17 Sep
    """

    return (
        f"{format_short_date(check_in_date)} - "
        f"{format_short_date(check_out_date)}"
    )


def to_iso_date(value: date) -> str:
    """
    Convert date to YYYY-MM-DD.
    """

    return value.isoformat()


# ============================================================
# PRICE CONVERSION
# ============================================================

def convert_price(price_text: Any) -> Optional[int]:
    """
    Extract the first price from text and round DOWN
    to the nearest 100.

    Examples:

        Rs. 7,687.50 -> 7,600
        Rs. 9,225.00 -> 9,200
        Rs. 12,300 -> 12,300

    This implementation safely handles:

        Rs. 8,450

    without incorrectly reading the period in "Rs.".
    """

    if not price_text:
        return None

    text = str(price_text)

    # Extract the first complete number.
    match = re.search(
        r"(\d[\d,]*(?:\.\d+)?)",
        text,
    )

    if not match:
        return None

    number_text = match.group(1).replace(",", "")

    try:
        value = float(number_text)

    except ValueError:
        return None

    if value <= 0:
        return None

    rounded_value = int(value // 100) * 100

    if rounded_value <= 0:
        return None

    return rounded_value


# ============================================================
# ROOM TYPE DETECTION
# ============================================================

def detect_room_type(name: Any) -> Optional[str]:
    """
    Detect room type from room name.

    Surveyor Suite must be checked before Surveyor.
    """

    room_name = str(name or "").lower()

    if "surveyor suite" in room_name:
        return "surveyor_suite"

    if "surveyor" in room_name:
        return "surveyor"

    if "camper" in room_name:
        return "camper"

    if "glamper" in room_name:
        return "glamper"

    if "zenith" in room_name:
        return "zenith"

    if "twin luxury" in room_name:
        return "twin_luxury"

    if "villa" in room_name:
        return "villa"

    return None


# ============================================================
# HTML CARD HELPERS
# ============================================================

def get_card_name(card: Any) -> str:
    """
    Extract room name from one room card.
    """

    selectors = [
        "h3",
        ".room-name",
        ".room-title",
        '[class*="room-name"]',
        '[class*="room-title"]',
    ]

    for selector in selectors:
        element = card.select_one(selector)

        if element:
            text = clean_text(element.get_text(" ", strip=True))

            if text:
                return text

    # Fallback: scan card text for a known room keyword.
    card_text = clean_text(card.get_text(" ", strip=True))

    for line in card_text.split("\n"):
        line = clean_text(line)

        if detect_room_type(line):
            return line

    return ""


def get_card_price(card: Any) -> str:
    """
    Extract the average per-room-per-night price.

    The AJAX response is expected to contain the average price
    in the HTML, even though it may initially be hidden in the
    browser version.
    """

    selectors = [
        "#rmamt_avg_night",
        ".avg_cls",
        '[id*="rmamt_avg_night"]',
    ]

    for selector in selectors:
        element = card.select_one(selector)

        if element:
            text = clean_text(element.get_text(" ", strip=True))

            if text:
                return text

    # Fallback: find the last Rs. or ₹ amount in the card.
    card_text = clean_text(card.get_text(" ", strip=True))

    matches = re.findall(
        r"(?:Rs\.?|₹)\s*[\d,]+(?:\.\d+)?",
        card_text,
        flags=re.IGNORECASE,
    )

    if matches:
        return matches[-1]

    return ""


def get_rooms_left(card: Any) -> Optional[int]:
    """
    Extract room availability count from a card.

    Supported examples:

        3 rooms left
        Hurry! 2 rooms left
        Only 1 room left
    """

    card_text = clean_text(card.get_text(" ", strip=True))

    patterns = [
        r"(?:hurry!\s*)?(\d+)\s+rooms?\s+left",
        r"only\s+(\d+)\s+rooms?\s+left",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            card_text,
            flags=re.IGNORECASE,
        )

        if match:
            try:
                return int(match.group(1))

            except ValueError:
                return None

    return None


# ============================================================
# PARSE ROOM RESULTS
# ============================================================

def parse_rooms(html: str) -> List[Dict[str, Any]]:
    """
    Parse room cards from the IPMS247 results HTML.

    Logic:
    - Find all room cards.
    - Keep the first card for each room type.
    - Scan every card to find the highest rooms-left count.
    - Return rooms in the fixed display order.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    cards = soup.select(
        "div.card-list.otartrow"
    )

    first_cards: Dict[str, Any] = {}
    rooms_left_by_type: Dict[str, int] = {}

    for card in cards:
        name = get_card_name(card)

        if not name:
            continue

        room_type = detect_room_type(name)

        if not room_type:
            continue

        # Keep the first card for each room type.
        if room_type not in first_cards:
            first_cards[room_type] = card

        # Scan every card for the highest room count.
        rooms_left = get_rooms_left(card)

        if rooms_left is not None:
            previous_value = rooms_left_by_type.get(room_type)

            if (
                previous_value is None
                or rooms_left > previous_value
            ):
                rooms_left_by_type[room_type] = rooms_left

    rooms: List[Dict[str, Any]] = []

    for room_type in ROOM_TYPE_ORDER:
        card = first_cards.get(room_type)

        if card is None:
            continue

        name = get_card_name(card)
        price_text = get_card_price(card)
        price = convert_price(price_text)

        if not name or price is None:
            continue

        room: Dict[str, Any] = {
            "name": name,
            "price": price,
        }

        if room_type in rooms_left_by_type:
            room["rooms_left"] = rooms_left_by_type[room_type]

        rooms.append(room)

    return rooms


# ============================================================
# AVAILABILITY TEXT
# ============================================================

def format_room_availability(
    rooms: List[Dict[str, Any]],
    check_in_date: date,
    check_out_date: date,
) -> str:
    """
    Format room data into the same availability text
    used by the JavaScript implementation.
    """

    room_prices: Dict[str, int] = {}

    for room in rooms:
        name = room.get("name")
        price = room.get("price")

        if not name or price is None:
            continue

        room_type = detect_room_type(name)

        if room_type:
            room_prices[room_type] = price

    lines = [
        (
            f"For {format_date_range(check_in_date, check_out_date)}, "
            "Here is the Room availability with prices below:"
        )
    ]

    if "camper" in room_prices:
        lines.append(
            (
                "The Camper room (2 occupants) is available for "
                f"Rs. {money(room_prices['camper'])} "
                "plus taxes per night."
            )
        )

    if "glamper" in room_prices:
        glamper_rooms_left = None

        for room in rooms:
            if detect_room_type(room.get("name")) == "glamper":
                glamper_rooms_left = room.get("rooms_left")
                break

        message = (
            "The Glamper room (2 occupants) is available for "
            f"Rs. {money(room_prices['glamper'])} "
            "plus taxes per night."
        )

        if glamper_rooms_left is not None:
            message += (
                f" (We have {glamper_rooms_left} Glamper rooms)"
            )

        lines.append(message)

    if "surveyor" in room_prices:
        lines.append(
            (
                "The Surveyor room (2 occupants) is available for "
                f"Rs. {money(room_prices['surveyor'])} "
                "plus taxes per night."
            )
        )

    if "surveyor_suite" in room_prices:
        lines.append(
            (
                "The Surveyor suite room (2 occupants) is available for "
                f"Rs. {money(room_prices['surveyor_suite'])} "
                "plus taxes per night."
            )
        )

    if "zenith" in room_prices:
        lines.append(
            (
                "The Zenith luxury cottage (2 occupants) is available for "
                f"Rs. {money(room_prices['zenith'])} "
                "plus taxes per night."
            )
        )

    if "twin_luxury" in room_prices:
        lines.append(
            (
                "The twin luxury cottage "
                "(2 occupants / Room) is available for "
                f"Rs. {money(room_prices['twin_luxury'])} "
                "plus taxes per night. "
                "(2 Rooms next to each other)"
            )
        )

    if "villa" in room_prices:
        # Villa is quoted as a two-room unit.
        villa_price = room_prices["villa"] * 2

        lines.append(
            (
                "The Villa (2 occupants/room) is available for "
                f"Rs. {money(villa_price)} "
                "plus taxes per night. "
                "(2 Rooms villa)"
            )
        )

    return "\n".join(lines)


# ============================================================
# HTTP SESSION
# ============================================================

def create_session() -> requests.Session:
    """
    Create a requests session with browser-like headers.
    """

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-IN,en;q=0.9",
            "Connection": "keep-alive",
        }
    )

    return session


def open_session(session: requests.Session) -> None:
    """
    Open the public booking page first.

    IPMS247 may create a PHP session cookie on this page.
    The same session must then be used for the AJAX request.
    """

    try:
        response = session.get(
            BOOKING_PAGE_URL,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException as exc:
        raise UpstreamError(
            f"Unable to open booking page: {exc}"
        ) from exc

    if not response.ok:
        raise UpstreamError(
            "Booking engine returned "
            f"HTTP {response.status_code} "
            "when opening the booking page."
        )

    if not session.cookies:
        raise UpstreamError(
            "Booking engine did not issue a session cookie."
        )


def fetch_room_details(
    session: requests.Session,
    check_in: str,
    check_in_date: date,
    nights: int,
) -> str:
    """
    Call the IPMS247 AJAX room-details endpoint.
    """

    payload = {
        "checkin": check_in,
        "gridcolumn": "1",
        "adults": "1",
        "child": "0",
        "nonights": str(nights),
        "ShowSelectedNights": "true",
        "DefaultSelectedNights": str(nights),
        "calendarDateFormat": "dd-mm-yy",
        "rooms": "1",
        "promotion": "",
        "ArrvalDt": to_iso_date(check_in_date),
        "HotelId": HOTEL_ID,
        "isLogin": "lf",
        "selectedLang": "",
        "modifysearch": "false",
        "promotioncode": "",
        "layoutView": "2",
        "ShowMinNightsMatchedRatePlan": "false",
        "LayoutTheme": "2",
        "w_showadult": "false",
        "w_showchild_bb": "false",
        "ShowMoreLessOpt": "",
        "w_showchild": "true",
        "metasearch": "",
        "ischeckavailabilityclicked": "1",
    }

    headers = {
        "Content-Type": (
            "application/x-www-form-urlencoded; charset=UTF-8"
        ),
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BOOKING_PAGE_URL,
        "Origin": "https://live.ipms247.com",
        "Accept-Language": "en-IN,en;q=0.9",
    }

    try:
        response = session.post(
            ROOM_DETAILS_URL,
            data=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException as exc:
        raise UpstreamError(
            f"Unable to fetch room details: {exc}"
        ) from exc

    html = response.text or ""

    if not response.ok:
        if re.search(
            r"sucuri|access denied",
            html,
            flags=re.IGNORECASE,
        ):
            raise UpstreamError(
                "The booking engine firewall blocked this request. "
                "If this persists, ask IPMS247/eZee support to allow "
                "your deployment."
            )

        raise UpstreamError(
            "Booking engine returned "
            f"HTTP {response.status_code} "
            "for the room results."
        )

    return html


# ============================================================
# PUBLIC SCRAPER FUNCTION
# ============================================================

def scrape_availability(
    check_in: str,
    check_out: str,
) -> Dict[str, Any]:
    """
    Main public function.

    Example:

        result = scrape_availability(
            "15-09-2026",
            "17-09-2026",
        )
    """

    date_data = validate_dates(
        check_in,
        check_out,
    )

    check_in_date = date_data["check_in_date"]
    check_out_date = date_data["check_out_date"]
    nights = date_data["nights"]

    session = create_session()

    open_session(session)

    html = fetch_room_details(
        session=session,
        check_in=check_in,
        check_in_date=check_in_date,
        nights=nights,
    )

    rooms = parse_rooms(html)

    if not rooms:
        raise UpstreamError(
            "No rooms were returned for these dates. "
            "The property may be sold out, or the booking engine "
            "layout may have changed."
        )

    availability_text = format_room_availability(
        rooms=rooms,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
    )

    return {
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "rooms": rooms,
        "availability_text": availability_text,
    }


# ============================================================
# FILE EXPORT HELPERS
# ============================================================

def save_json(
    result: Dict[str, Any],
    filename: str = "availability.json",
) -> None:
    """
    Save result as JSON.
    """

    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False,
        )


def save_text(
    result: Dict[str, Any],
    filename: str = "availability.txt",
) -> None:
    """
    Save formatted availability text.
    """

    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            result.get("availability_text", "")
        )


def save_csv(
    result: Dict[str, Any],
    filename: str = "availability.csv",
) -> None:
    """
    Save room results as CSV.
    """

    import csv

    rooms = result.get("rooms", [])

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "name",
                "price",
                "rooms_left",
            ],
        )

        writer.writeheader()

        for room in rooms:
            writer.writerow(
                {
                    "name": room.get("name", ""),
                    "price": room.get("price", ""),
                    "rooms_left": room.get(
                        "rooms_left",
                        "",
                    ),
                }
            )


# ============================================================
# COMMAND-LINE INTERFACE
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape Everest Base Camp room availability "
            "from IPMS247."
        )
    )

    parser.add_argument(
        "--check-in",
        required=True,
        help="Check-in date in DD-MM-YYYY format.",
    )

    parser.add_argument(
        "--check-out",
        required=True,
        help="Check-out date in DD-MM-YYYY format.",
    )

    parser.add_argument(
        "--json",
        default="availability.json",
        help="JSON output filename.",
    )

    parser.add_argument(
        "--csv",
        default="availability.csv",
        help="CSV output filename.",
    )

    parser.add_argument(
        "--txt",
        default="availability.txt",
        help="Text output filename.",
    )

    args = parser.parse_args()

    try:
        result = scrape_availability(
            check_in=args.check_in,
            check_out=args.check_out,
        )

    except ValidationError as exc:
        print(f"Validation error: {exc}")
        raise SystemExit(1)

    except UpstreamError as exc:
        print(f"Booking engine error: {exc}")
        raise SystemExit(1)

    except Exception as exc:
        print(f"Unexpected error: {exc}")
        raise SystemExit(1)

    print(result["availability_text"])

    save_json(
        result,
        args.json,
    )

    save_csv(
        result,
        args.csv,
    )

    save_text(
        result,
        args.txt,
    )

    print()
    print(f"Saved JSON: {args.json}")
    print(f"Saved CSV:  {args.csv}")
    print(f"Saved TXT:  {args.txt}")

if __name__ == "__main__":
    main()