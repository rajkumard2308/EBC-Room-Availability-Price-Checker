# import argparse
# import csv
# import json
# import os
# import platform
# import re
# import sys
# from datetime import datetime
# from pathlib import Path
#
# from playwright.sync_api import (
#     sync_playwright,
#     TimeoutError as PlaywrightTimeoutError,
# )
#
#
# # ============================================================
# # CONFIGURATION
# # ============================================================
#
# URL = (
#     "https://live.ipms247.com/booking/"
#     "book-rooms-everestbasecamp"
# )
#
# CHECKIN_XPATH = '//*[@id="eZ_chkin"]'
# CHECKOUT_XPATH = '//*[@id="eZ_chkout"]'
# AVAILABILITY_XPATH = '//*[@id="book"]'
#
# PER_ROOM_NIGHT_SELECTOR = "#pnl_avg_blk"
#
# ROOM_CARD_SELECTOR = "div.card-list.otartrow"
#
# PRICE_SELECTOR = "#rmamt_avg_night"
#
#
# # ============================================================
# # OUTPUT
# # ============================================================
#
# OUTPUT_DIR = Path("data")
# OUTPUT_DIR.mkdir(exist_ok=True)
#
# JSON_FILE = OUTPUT_DIR / "rooms.json"
# CSV_FILE = OUTPUT_DIR / "rooms.csv"
# TEXT_FILE = OUTPUT_DIR / "room_availability.txt"
#
#
# # ============================================================
# # SETTINGS
# # ============================================================
#
# # Maximum scroll attempts.
# # Previous version used 60.
# MAX_SCROLLS = 18
#
# # Small wait after each lazy-load scroll.
# SCROLL_WAIT_MS = 350
#
# # Maximum time waiting for first room.
# RESULT_TIMEOUT_MS = 60000
#
#
# # ============================================================
# # TEXT CLEANING
# # ============================================================
#
# def clean_text(text):
#     if not text:
#         return ""
#
#     return re.sub(
#         r"\s+",
#         " ",
#         text
#     ).strip()
#
#
# # ============================================================
# # DATE VALIDATION
# # ============================================================
#
# def validate_dates(
#     check_in,
#     check_out
# ):
#     try:
#         check_in_date = datetime.strptime(
#             check_in,
#             "%d-%m-%Y"
#         )
#     except ValueError:
#         raise ValueError(
#             "Invalid check-in date. "
#             "Use DD-MM-YYYY."
#         )
#
#     try:
#         check_out_date = datetime.strptime(
#             check_out,
#             "%d-%m-%Y"
#         )
#     except ValueError:
#         raise ValueError(
#             "Invalid check-out date. "
#             "Use DD-MM-YYYY."
#         )
#
#     if check_out_date <= check_in_date:
#         raise ValueError(
#             "Check-out must be after check-in."
#         )
#
#     return (
#         check_in_date,
#         check_out_date
#     )
#
#
# # ============================================================
# # CALENDAR
# # ============================================================
#
# def wait_for_calendar(page):
#
#     selectors = [
#         "#ui-datepicker-div",
#         ".ui-datepicker",
#         ".ui-datepicker-calendar",
#         "[class*='datepicker']",
#     ]
#
#     for _ in range(15):
#
#         for selector in selectors:
#
#             try:
#                 calendars = page.locator(
#                     selector
#                 )
#
#                 count = calendars.count()
#
#                 for i in range(count):
#
#                     calendar = calendars.nth(i)
#
#                     if calendar.is_visible():
#                         return calendar
#
#             except Exception:
#                 continue
#
#         page.wait_for_timeout(200)
#
#     raise RuntimeError(
#         "Date calendar was not found."
#     )
#
#
# def get_calendar_month_year(calendar):
#
#     month_name = None
#     year = None
#
#     try:
#
#         element = calendar.locator(
#             ".ui-datepicker-month"
#         ).first
#
#         if element.count():
#
#             month_name = clean_text(
#                 element.inner_text()
#             )
#
#     except Exception:
#         pass
#
#     try:
#
#         element = calendar.locator(
#             ".ui-datepicker-year"
#         ).first
#
#         if element.count():
#
#             year_text = clean_text(
#                 element.inner_text()
#             )
#
#             if year_text.isdigit():
#                 year = int(year_text)
#
#     except Exception:
#         pass
#
#     return (
#         month_name,
#         year
#     )
#
#
# def get_calendar_current_date(calendar):
#
#     month_name, year = (
#         get_calendar_month_year(
#             calendar
#         )
#     )
#
#     months = [
#         "January",
#         "February",
#         "March",
#         "April",
#         "May",
#         "June",
#         "July",
#         "August",
#         "September",
#         "October",
#         "November",
#         "December",
#     ]
#
#     if (
#         month_name
#         and year
#         and month_name in months
#     ):
#
#         month = (
#             months.index(
#                 month_name
#             ) + 1
#         )
#
#         return (
#             year,
#             month
#         )
#
#     now = datetime.now()
#
#     return (
#         now.year,
#         now.month
#     )
#
#
# def click_calendar_navigation(
#     calendar,
#     direction
# ):
#
#     if direction == "next":
#
#         selectors = [
#             ".ui-datepicker-next",
#             "a.ui-datepicker-next",
#         ]
#
#     else:
#
#         selectors = [
#             ".ui-datepicker-prev",
#             "a.ui-datepicker-prev",
#         ]
#
#     for selector in selectors:
#
#         try:
#
#             buttons = calendar.locator(
#                 selector
#             )
#
#             for i in range(
#                 buttons.count()
#             ):
#
#                 button = buttons.nth(i)
#
#                 if not button.is_visible():
#                     continue
#
#                 if not button.is_enabled():
#                     continue
#
#                 button.click()
#
#                 return True
#
#         except Exception:
#             continue
#
#     return False
#
#
# def navigate_calendar(
#     page,
#     calendar,
#     target_date
# ):
#
#     target_year = target_date.year
#     target_month = target_date.month
#
#     current_year, current_month = (
#         get_calendar_current_date(
#             calendar
#         )
#     )
#
#     difference = (
#         (target_year - current_year) * 12
#         + (target_month - current_month)
#     )
#
#     print(
#         f"Current calendar: "
#         f"{current_month:02d}/{current_year}"
#     )
#
#     print(
#         f"Target calendar: "
#         f"{target_month:02d}/{target_year}"
#     )
#
#     print(
#         f"Month difference: "
#         f"{difference}"
#     )
#
#     if difference == 0:
#         return
#
#     direction = (
#         "next"
#         if difference > 0
#         else "previous"
#     )
#
#     for _ in range(
#         abs(difference)
#     ):
#
#         calendar = wait_for_calendar(
#             page
#         )
#
#         if not click_calendar_navigation(
#             calendar,
#             direction
#         ):
#
#             raise RuntimeError(
#                 f"Could not click "
#                 f"calendar {direction}."
#             )
#
#         # Faster than the old 400 ms.
#         page.wait_for_timeout(250)
#
#
# def click_calendar_day(
#     page,
#     calendar,
#     target_date
# ):
#
#     target_day = str(
#         target_date.day
#     )
#
#     print(
#         f"Selecting day: {target_day}"
#     )
#
#     links = calendar.locator(
#         "a.ui-state-default"
#     )
#
#     for i in range(
#         links.count()
#     ):
#
#         try:
#
#             link = links.nth(i)
#
#             if not link.is_visible():
#                 continue
#
#             text = clean_text(
#                 link.inner_text()
#             )
#
#             if text != target_day:
#                 continue
#
#             classes = (
#                 link.get_attribute(
#                     "class"
#                 )
#                 or ""
#             )
#
#             # Ignore days from adjacent month.
#             if (
#                 "ui-priority-secondary"
#                 in classes
#             ):
#                 continue
#
#             link.click()
#
#             page.wait_for_timeout(350)
#
#             print(
#                 f"✓ Selected "
#                 f"{target_date.strftime('%d-%m-%Y')}"
#             )
#
#             return
#
#         except Exception:
#             continue
#
#     raise RuntimeError(
#         f"Day {target_day} "
#         f"was not found."
#     )
#
#
# def select_date(
#     page,
#     input_xpath,
#     target_date,
#     field_name
# ):
#
#     print("\n")
#     print("=" * 70)
#     print(
#         f"SELECTING {field_name}"
#     )
#     print("=" * 70)
#
#     date_input = page.locator(
#         f"xpath={input_xpath}"
#     )
#
#     date_input.wait_for(
#         state="visible",
#         timeout=30000
#     )
#
#     date_input.scroll_into_view_if_needed()
#
#     date_input.click()
#
#     page.wait_for_timeout(350)
#
#     calendar = wait_for_calendar(
#         page
#     )
#
#     navigate_calendar(
#         page,
#         calendar,
#         target_date
#     )
#
#     calendar = wait_for_calendar(
#         page
#     )
#
#     click_calendar_day(
#         page,
#         calendar,
#         target_date
#     )
#
#     page.wait_for_timeout(250)
#
#     actual_value = (
#         date_input.input_value()
#     )
#
#     print(
#         f"{field_name} value: "
#         f"{actual_value}"
#     )
#
#     return actual_value
#
#
# def enter_dates(
#     page,
#     check_in,
#     check_out
# ):
#
#     check_in_date = datetime.strptime(
#         check_in,
#         "%d-%m-%Y"
#     )
#
#     check_out_date = datetime.strptime(
#         check_out,
#         "%d-%m-%Y"
#     )
#
#     actual_checkin = select_date(
#         page,
#         CHECKIN_XPATH,
#         check_in_date,
#         "CHECK-IN"
#     )
#
#     actual_checkout = select_date(
#         page,
#         CHECKOUT_XPATH,
#         check_out_date,
#         "CHECK-OUT"
#     )
#
#     print("\n")
#     print("=" * 70)
#     print("DATE VERIFICATION")
#     print("=" * 70)
#
#     print(
#         f"Expected Check-in : "
#         f"{check_in}"
#     )
#
#     print(
#         f"Actual Check-in   : "
#         f"{actual_checkin}"
#     )
#
#     print(
#         f"Expected Check-out: "
#         f"{check_out}"
#     )
#
#     print(
#         f"Actual Check-out  : "
#         f"{actual_checkout}"
#     )
#
#     if (
#         not actual_checkin
#         or not actual_checkout
#     ):
#
#         raise RuntimeError(
#             "Date selection failed."
#         )
#
#     print(
#         "\n✓ Dates selected successfully."
#     )
#
#
# # ============================================================
# # CHECK AVAILABILITY
# # ============================================================
#
# def click_check_availability(page):
#
#     print("\n")
#     print("=" * 70)
#     print("CHECK AVAILABILITY")
#     print("=" * 70)
#
#     button = page.locator(
#         f"xpath={AVAILABILITY_XPATH}"
#     )
#
#     button.wait_for(
#         state="visible",
#         timeout=30000
#     )
#
#     button.scroll_into_view_if_needed()
#
#     button.click()
#
#     print(
#         "✓ Check Availability clicked."
#     )
#
#
# # ============================================================
# # WAIT FOR RESULTS
# #
# # IMPORTANT:
# # Do NOT wait for networkidle.
# #
# # Hotel websites often keep network requests
# # open for analytics / advertisements.
# # ============================================================
#
# def wait_for_results(page):
#
#     print("\n")
#     print("=" * 70)
#     print("WAITING FOR ROOM RESULTS")
#     print("=" * 70)
#
#     try:
#
#         page.locator(
#             ROOM_CARD_SELECTOR
#         ).first.wait_for(
#             state="visible",
#             timeout=RESULT_TIMEOUT_MS
#         )
#
#     except PlaywrightTimeoutError:
#
#         raise RuntimeError(
#             "Room results did not load "
#             "within the timeout."
#         )
#
#     print(
#         "✓ Room results loaded."
#     )
#
#
# # ============================================================
# # PER ROOM PER NIGHT
# # ============================================================
#
# def click_per_room_per_night(page):
#
#     print("\n")
#     print("=" * 70)
#     print("PER ROOM PER NIGHT")
#     print("=" * 70)
#
#     button = page.locator(
#         PER_ROOM_NIGHT_SELECTOR
#     )
#
#     button.wait_for(
#         state="visible",
#         timeout=30000
#     )
#
#     button.scroll_into_view_if_needed()
#
#     print(
#         "Clicking #pnl_avg_blk ..."
#     )
#
#     button.click()
#
#     # Wait only until price is available.
#     try:
#
#         page.locator(
#             ROOM_CARD_SELECTOR
#         ).first.locator(
#             PRICE_SELECTOR
#         ).wait_for(
#             state="visible",
#             timeout=10000
#         )
#
#     except PlaywrightTimeoutError:
#
#         # Some pages update prices slightly later.
#         page.wait_for_timeout(700)
#
#     print(
#         "✓ Per Room Per Night selected."
#     )
#
#
# # ============================================================
# # FAST LAZY-LOAD
# #
# # Previous:
# #   60 scrolls
# #   800 ms each
# #
# # New:
# #   max 18 scrolls
# #   350 ms each
# #   stop as soon as card count stabilizes
# # ============================================================
#
# def load_all_rooms(page):
#
#     print("\n")
#     print("=" * 70)
#     print("LOADING ALL ROOM CARDS")
#     print("=" * 70)
#
#     previous_count = 0
#     stable_count_rounds = 0
#
#     for scroll_number in range(
#         MAX_SCROLLS
#     ):
#
#         cards = page.locator(
#             ROOM_CARD_SELECTOR
#         )
#
#         current_count = cards.count()
#
#         print(
#             f"Scroll "
#             f"{scroll_number + 1:02d} | "
#             f"Cards: {current_count}"
#         )
#
#         # Scroll directly to the bottom.
#         page.evaluate(
#             """
#             () => {
#                 window.scrollTo(
#                     0,
#                     document.documentElement.scrollHeight
#                 );
#             }
#             """
#         )
#
#         page.wait_for_timeout(
#             SCROLL_WAIT_MS
#         )
#
#         new_count = page.locator(
#             ROOM_CARD_SELECTOR
#         ).count()
#
#         if new_count == previous_count:
#
#             stable_count_rounds += 1
#
#         else:
#
#             stable_count_rounds = 0
#
#         previous_count = new_count
#
#         # Once card count stops changing for
#         # two bottom-of-page checks, stop.
#         if stable_count_rounds >= 2:
#
#             break
#
#     total = page.locator(
#         ROOM_CARD_SELECTOR
#     ).count()
#
#     print(
#         f"\n✓ Total cards loaded: "
#         f"{total}"
#     )
#
#     return total
#
#
# # ============================================================
# # CARD NAME
# # ============================================================
#
# def get_card_name(card):
#
#     try:
#
#         heading = card.locator(
#             "h3"
#         ).first
#
#         if heading.count() == 0:
#             return ""
#
#         return clean_text(
#             heading.inner_text()
#         )
#
#     except Exception:
#
#         return ""
#
#
# # ============================================================
# # CARD PRICE
# # ============================================================
#
# def get_card_price(card):
#
#     try:
#
#         price_element = card.locator(
#             PRICE_SELECTOR
#         ).first
#
#         if price_element.count() == 0:
#             return ""
#
#         return clean_text(
#             price_element.inner_text()
#         )
#
#     except Exception:
#
#         return ""
#
#
# # ============================================================
# # CONVERT PRICE
# # ============================================================
#
# def convert_price(price_text):
#
#     if not price_text:
#         return None
#
#     cleaned = (
#         price_text
#         .replace(",", "")
#         .strip()
#     )
#
#     cleaned = re.sub(
#         r"[^\d.]",
#         "",
#         cleaned
#     )
#
#     if not cleaned:
#         return None
#
#     try:
#
#         value = float(
#             cleaned
#         )
#
#     except ValueError:
#
#         return None
#
#     if value <= 0:
#         return None
#
#     # Round DOWN to nearest 100.
#     #
#     # 7687.50 -> 7600
#     # 9225.00 -> 9200
#     # 11530   -> 11500
#     # 12300   -> 12300
#     # 15370   -> 15300
#
#     return (
#         int(value) // 100
#     ) * 100
#
#
# # ============================================================
# # ROOM TYPE DETECTION
# #
# # This replaces the expensive ancestor-searching logic.
# #
# # We use room TYPE only.
# # We do NOT use "Limited Time Deal", "Early Bird", etc.
# # ============================================================
#
# ROOM_TYPE_ORDER = [
#     "camper",
#     "glamper",
#     "surveyor_suite",
#     "surveyor",
#     "zenith",
#     "twin_luxury",
#     "villa",
# ]
#
#
# def detect_room_type(name):
#
#     name_lower = name.lower()
#
#     # IMPORTANT:
#     # Surveyor Suite must be checked BEFORE Surveyor.
#
#     if "surveyor suite" in name_lower:
#         return "surveyor_suite"
#
#     if "surveyor" in name_lower:
#         return "surveyor"
#
#     if "camper" in name_lower:
#         return "camper"
#
#     if "glamper" in name_lower:
#         return "glamper"
#
#     if "zenith" in name_lower:
#         return "zenith"
#
#     if "twin luxury" in name_lower:
#         return "twin_luxury"
#
#     if "villa" in name_lower:
#         return "villa"
#
#     return None
#
#
# # ============================================================
# # SCRAPE FIRST CARD PER ROOM TYPE
# #
# # Example:
# #
# # Camper:
# #   Card 1 -> TAKE
# #   Card 2 -> IGNORE
# #
# # Glamper:
# #   Card 1 -> TAKE
# #   Card 2 -> IGNORE
# #
# # Surveyor:
# #   Card 1 -> TAKE
# #   Card 2 -> IGNORE
# #
# # etc.
# # ============================================================
#
# def scrape_rooms(page):
#
#     print("\n")
#     print("=" * 70)
#     print(
#         "SCRAPING FIRST CARD "
#         "OF EVERY ROOM TYPE"
#     )
#     print("=" * 70)
#
#     load_all_rooms(page)
#
#     cards = page.locator(
#         ROOM_CARD_SELECTOR
#     )
#
#     total_cards = cards.count()
#
#     print(
#         f"\nCards available: "
#         f"{total_cards}"
#     )
#
#     # --------------------------------------------------------
#     # Keep ONLY the first card encountered
#     # for each room type.
#     # --------------------------------------------------------
#
#     first_cards = {}
#
#     for index in range(
#         total_cards
#     ):
#
#         try:
#
#             card = cards.nth(index)
#
#             name = get_card_name(
#                 card
#             )
#
#             if not name:
#                 continue
#
#             room_type = detect_room_type(
#                 name
#             )
#
#             if not room_type:
#                 continue
#
#             # Already found the first card
#             # for this room type.
#             if room_type in first_cards:
#                 continue
#
#             first_cards[
#                 room_type
#             ] = card
#
#         except Exception:
#             continue
#
#     print(
#         f"Room types found: "
#         f"{len(first_cards)}"
#     )
#
#     rooms = []
#
#     # --------------------------------------------------------
#     # Process in fixed room order.
#     # --------------------------------------------------------
#
#     for room_type in ROOM_TYPE_ORDER:
#
#         if room_type not in first_cards:
#
#             print(
#                 f"\n{room_type}: "
#                 f"NOT AVAILABLE"
#             )
#
#             continue
#
#         card = first_cards[
#             room_type
#         ]
#
#         name = get_card_name(
#             card
#         )
#
#         website_price = get_card_price(
#             card
#         )
#
#         price = convert_price(
#             website_price
#         )
#
#         print("\n")
#         print("=" * 70)
#
#         print(
#             f"ROOM TYPE: "
#             f"{room_type}"
#         )
#
#         print(
#             "SELECTED: FIRST CARD ONLY"
#         )
#
#         print(
#             f"Name: {name}"
#         )
#
#         print(
#             f"Website price: "
#             f"{website_price}"
#         )
#
#         # ----------------------------------------------------
#         # No price = unavailable.
#         # Do NOT store null.
#         # ----------------------------------------------------
#
#         if price is None:
#
#             print(
#                 "SKIPPED - no valid price."
#             )
#
#             continue
#
#         rooms.append(
#             {
#                 "name": name,
#                 "price": price,
#             }
#         )
#
#         print(
#             f"Stored price: "
#             f"{price}"
#         )
#
#         print("=" * 70)
#
#     # --------------------------------------------------------
#     # FINAL RESULT
#     # --------------------------------------------------------
#
#     print("\n")
#     print("=" * 70)
#     print("FINAL ROOM RESULT")
#     print("=" * 70)
#
#     print(
#         f"Total cards found: "
#         f"{total_cards}"
#     )
#
#     print(
#         f"Rooms stored: "
#         f"{len(rooms)}"
#     )
#
#     print("=" * 70)
#
#     for index, room in enumerate(
#         rooms,
#         start=1
#     ):
#
#         print(
#             f"{index}. "
#             f"{room['name']} "
#             f"-> "
#             f"{room['price']}"
#         )
#
#     return rooms
#
#
# # ============================================================
# # FORMAT ROOM AVAILABILITY
# # ============================================================
#
# def format_room_availability(data):
#
#     rooms = data.get(
#         "rooms",
#         []
#     )
#
#     room_prices = {}
#
#     for room in rooms:
#
#         name = room.get(
#             "name",
#             ""
#         )
#
#         price = room.get(
#             "price"
#         )
#
#         if not name:
#             continue
#
#         if price is None:
#             continue
#
#         room_type = detect_room_type(
#             name
#         )
#
#         if room_type:
#
#             room_prices[
#                 room_type
#             ] = price
#
#     def money(value):
#         return f"{value:,}"
#
#     lines = [
#         "For , Here is the Room availability "
#         "with prices below:"
#     ]
#
#     # --------------------------------------------------------
#     # Camper
#     # --------------------------------------------------------
#
#     if "camper" in room_prices:
#
#         lines.append(
#             "The Camper room (2 occupants) "
#             "is available for "
#             f"Rs. {money(room_prices['camper'])} "
#             "plus taxes per night."
#         )
#
#     # --------------------------------------------------------
#     # Glamper
#     # --------------------------------------------------------
#
#     if "glamper" in room_prices:
#
#         lines.append(
#             "The Glamper room (2 occupants) "
#             "is available for "
#             f"Rs. {money(room_prices['glamper'])} "
#             "plus taxes per night. "
#             "(We have 4 Glamper rooms)"
#         )
#
#     # --------------------------------------------------------
#     # Surveyor
#     # --------------------------------------------------------
#
#     if "surveyor" in room_prices:
#
#         lines.append(
#             "The Surveyor room (2 occupants) "
#             "is available for "
#             f"Rs. {money(room_prices['surveyor'])} "
#             "plus taxes per night."
#         )
#
#     # --------------------------------------------------------
#     # Surveyor Suite
#     # --------------------------------------------------------
#
#     if "surveyor_suite" in room_prices:
#
#         lines.append(
#             "The Surveyor suite room "
#             "(2 occupants) is available for "
#             f"Rs. {money(room_prices['surveyor_suite'])} "
#             "plus taxes per night."
#         )
#
#     # --------------------------------------------------------
#     # Zenith
#     # --------------------------------------------------------
#
#     if "zenith" in room_prices:
#
#         lines.append(
#             "The Zenith luxury cottage "
#             "(2 occupants) is available for "
#             f"Rs. {money(room_prices['zenith'])} "
#             "plus taxes per night."
#         )
#
#     # --------------------------------------------------------
#     # Twin Luxury
#     # --------------------------------------------------------
#
#     if "twin_luxury" in room_prices:
#
#         lines.append(
#             "The twin luxury cottage "
#             "(2 occupants / Room) is available "
#             f"for Rs. {money(room_prices['twin_luxury'])} "
#             "plus taxes per night. "
#             "(2 Rooms next to each other)"
#         )
#
#     # --------------------------------------------------------
#     # Villa
#     # --------------------------------------------------------
#
#     if "villa" in room_prices:
#
#         # Villa price = room price × 2.
#
#         villa_price = (
#             room_prices["villa"] * 2
#         )
#
#         lines.append(
#             "The Villa (2 occupants/room) "
#             "is available for "
#             f"Rs. {money(villa_price)} "
#             "plus taxes per night. "
#             "(2 Rooms villa)"
#         )
#
#     return "\n".join(
#         lines
#     )
#
#
# # ============================================================
# # SAVE JSON
# # ============================================================
#
# def save_json(
#     rooms,
#     check_in,
#     check_out
# ):
#
#     output = {
#         "check_in": check_in,
#         "check_out": check_out,
#         "rooms": rooms,
#     }
#
#     with open(
#         JSON_FILE,
#         "w",
#         encoding="utf-8"
#     ) as file:
#
#         json.dump(
#             output,
#             file,
#             indent=4,
#             ensure_ascii=False
#         )
#
#     print(
#         f"✓ JSON saved: "
#         f"{JSON_FILE}"
#     )
#
#
# # ============================================================
# # SAVE CSV
# # ============================================================
#
# def save_csv(rooms):
#
#     with open(
#         CSV_FILE,
#         "w",
#         newline="",
#         encoding="utf-8-sig"
#     ) as file:
#
#         writer = csv.DictWriter(
#             file,
#             fieldnames=[
#                 "name",
#                 "price",
#             ]
#         )
#
#         writer.writeheader()
#
#         for room in rooms:
#
#             writer.writerow(
#                 room
#             )
#
#     print(
#         f"✓ CSV saved: "
#         f"{CSV_FILE}"
#     )
#
#
# # ============================================================
# # SAVE TEXT
# # ============================================================
#
# def save_text(text):
#
#     with open(
#         TEXT_FILE,
#         "w",
#         encoding="utf-8"
#     ) as file:
#
#         file.write(text)
#
#     print(
#         f"✓ Availability text saved: "
#         f"{TEXT_FILE}"
#     )
#
#
# # ============================================================
# # BROWSER LAUNCH
# #
# # Windows:
# #   Uses Playwright Chromium.
# #
# # Streamlit Cloud / Linux:
# #   Uses /usr/bin/chromium.
# # ============================================================
#
# def launch_browser(playwright):
#
#     system_name = platform.system()
#
#     print(
#         f"Operating system: "
#         f"{system_name}"
#     )
#
#     if system_name == "Windows":
#
#         print(
#             "Browser mode: "
#             "Windows Chromium"
#         )
#
#         return playwright.chromium.launch(
#             headless=False
#         )
#
#     # --------------------------------------------------------
#     # Linux / Streamlit Cloud
#     # --------------------------------------------------------
#
#     chromium_paths = [
#         "/usr/bin/chromium",
#         "/usr/bin/chromium-browser",
#     ]
#
#     chromium_path = None
#
#     for path in chromium_paths:
#
#         if os.path.exists(path):
#
#             chromium_path = path
#             break
#
#     if chromium_path:
#
#         print(
#             f"Browser mode: "
#             f"Headless Chromium "
#             f"({chromium_path})"
#         )
#
#         return playwright.chromium.launch(
#             executable_path=chromium_path,
#             headless=True,
#             args=[
#                 "--no-sandbox",
#                 "--disable-dev-shm-usage",
#                 "--disable-gpu",
#                 "--disable-software-rasterizer",
#             ],
#         )
#
#     # Fallback.
#     print(
#         "Browser mode: "
#         "Playwright bundled Chromium"
#     )
#
#     return playwright.chromium.launch(
#         headless=True,
#         args=[
#             "--no-sandbox",
#             "--disable-dev-shm-usage",
#             "--disable-gpu",
#         ],
#     )
#
#
# # ============================================================
# # MAIN
# # ============================================================
#
# def main():
#
#     # --------------------------------------------------------
#     # UTF-8 console
#     # --------------------------------------------------------
#
#     try:
#
#         sys.stdout.reconfigure(
#             encoding="utf-8"
#         )
#
#         sys.stderr.reconfigure(
#             encoding="utf-8"
#         )
#
#     except Exception:
#         pass
#
#     # --------------------------------------------------------
#     # Arguments
#     # --------------------------------------------------------
#
#     parser = argparse.ArgumentParser(
#         description=(
#             "Everest Base Camp "
#             "Room Price Scraper"
#         )
#     )
#
#     parser.add_argument(
#         "--check-in",
#         required=True,
#         help="Check-in date DD-MM-YYYY"
#     )
#
#     parser.add_argument(
#         "--check-out",
#         required=True,
#         help="Check-out date DD-MM-YYYY"
#     )
#
#     args = parser.parse_args()
#
#     check_in = args.check_in
#     check_out = args.check_out
#
#     # --------------------------------------------------------
#     # Validate
#     # --------------------------------------------------------
#
#     validate_dates(
#         check_in,
#         check_out
#     )
#
#     # --------------------------------------------------------
#     # Header
#     # --------------------------------------------------------
#
#     print("\n")
#     print("=" * 70)
#     print("EVEREST BASE CAMP")
#     print("ROOM PRICE SCRAPER")
#     print("=" * 70)
#
#     print(
#         f"\nCheck-in : "
#         f"{check_in}"
#     )
#
#     print(
#         f"Check-out: "
#         f"{check_out}"
#     )
#
#     print("\nRULE:")
#
#     print(
#         "Camper        -> FIRST CARD"
#     )
#
#     print(
#         "Glamper       -> FIRST CARD"
#     )
#
#     print(
#         "Surveyor      -> FIRST CARD"
#     )
#
#     print(
#         "Surveyor Suite -> FIRST CARD"
#     )
#
#     print(
#         "Zenith        -> FIRST CARD"
#     )
#
#     print(
#         "Twin Luxury   -> FIRST CARD"
#     )
#
#     print(
#         "Villa         -> FIRST CARD"
#     )
#
#     print(
#         "Unavailable room -> NOT STORED"
#     )
#
#     print(
#         "No NULL / None values"
#     )
#
#     # ========================================================
#     # PLAYWRIGHT
#     # ========================================================
#
#     with sync_playwright() as playwright:
#
#         browser = None
#         context = None
#
#         try:
#
#             # ------------------------------------------------
#             # Launch
#             # ------------------------------------------------
#
#             browser = launch_browser(
#                 playwright
#             )
#
#             # ------------------------------------------------
#             # Context
#             # ------------------------------------------------
#
#             context = browser.new_context(
#                 viewport={
#                     "width": 1440,
#                     "height": 900,
#                 },
#                 locale="en-IN",
#             )
#
#             page = context.new_page()
#
#             page.set_default_timeout(
#                 15000
#             )
#
#             page.set_default_navigation_timeout(
#                 45000
#             )
#
#             # ------------------------------------------------
#             # OPEN WEBSITE
#             # ------------------------------------------------
#
#             print(
#                 "\nOpening website..."
#             )
#
#             page.goto(
#                 URL,
#                 wait_until="domcontentloaded",
#                 timeout=45000
#             )
#
#             print(
#                 "✓ Website opened."
#             )
#
#             # ------------------------------------------------
#             # Small initial wait.
#             # ------------------------------------------------
#
#             page.wait_for_timeout(
#                 1200
#             )
#
#             # ------------------------------------------------
#             # DATE SELECTION
#             # ------------------------------------------------
#
#             enter_dates(
#                 page,
#                 check_in,
#                 check_out
#             )
#
#             # ------------------------------------------------
#             # CHECK AVAILABILITY
#             # ------------------------------------------------
#
#             click_check_availability(
#                 page
#             )
#
#             # ------------------------------------------------
#             # WAIT FOR RESULTS
#             # ------------------------------------------------
#
#             wait_for_results(
#                 page
#             )
#
#             # ------------------------------------------------
#             # PER ROOM PER NIGHT
#             # ------------------------------------------------
#
#             click_per_room_per_night(
#                 page
#             )
#
#             # ------------------------------------------------
#             # SCRAPE
#             # ------------------------------------------------
#
#             rooms = scrape_rooms(
#                 page
#             )
#
#             # ------------------------------------------------
#             # SAVE JSON
#             # ------------------------------------------------
#
#             save_json(
#                 rooms,
#                 check_in,
#                 check_out
#             )
#
#             # ------------------------------------------------
#             # SAVE CSV
#             # ------------------------------------------------
#
#             save_csv(
#                 rooms
#             )
#
#             # ------------------------------------------------
#             # FORMAT FINAL MESSAGE
#             # ------------------------------------------------
#
#             data = {
#                 "check_in": check_in,
#                 "check_out": check_out,
#                 "rooms": rooms,
#             }
#
#             availability_text = (
#                 format_room_availability(
#                     data
#                 )
#             )
#
#             # ------------------------------------------------
#             # SAVE TEXT
#             # ------------------------------------------------
#
#             save_text(
#                 availability_text
#             )
#
#             # ------------------------------------------------
#             # PRINT FINAL
#             # ------------------------------------------------
#
#             print("\n")
#             print("=" * 70)
#             print("ROOM AVAILABILITY")
#             print("=" * 70)
#
#             print(
#                 availability_text
#             )
#
#             print("=" * 70)
#
#             print("\n")
#             print("=" * 70)
#             print("SCRAPING COMPLETED")
#             print("=" * 70)
#
#             print(
#                 f"Total rooms stored: "
#                 f"{len(rooms)}"
#             )
#
#         finally:
#
#             # ------------------------------------------------
#             # IMPORTANT:
#             # No 10-second wait.
#             # Close immediately.
#             # ------------------------------------------------
#
#             try:
#
#                 if context:
#                     context.close()
#
#             except Exception:
#                 pass
#
#             try:
#
#                 if browser:
#                     browser.close()
#
#             except Exception:
#                 pass
#
#             print(
#                 "\n✓ Browser closed."
#             )
#
#
# # ============================================================
# # ENTRY POINT
# # ============================================================
#
# if __name__ == "__main__":
#     main()

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

    return date_obj.strftime("%d %b")


def format_date_range(check_in, check_out):
    """
    23-08-2026, 25-08-2026
    ->
    23Aug-25Aug
    """

    return (
        f"{format_short_date(check_in)} - "
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