import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Everest Base Camp | Room Availability",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MAIN_FILE = BASE_DIR / "main.py"

DATA_DIR = BASE_DIR / "data"

JSON_FILE = DATA_DIR / "rooms.json"

TEXT_FILE = DATA_DIR / "room_availability.txt"


# ============================================================
# SESSION STATE
# ============================================================

if "searched" not in st.session_state:
    st.session_state.searched = False

if "availability_text" not in st.session_state:
    st.session_state.availability_text = ""

if "rooms_found" not in st.session_state:
    st.session_state.rooms_found = 0

if "search_check_in" not in st.session_state:
    st.session_state.search_check_in = None

if "search_check_out" not in st.session_state:
    st.session_state.search_check_out = None


# ============================================================
# CENTERED HEADER
#
# IMPORTANT:
# No HTML is used here.
# ============================================================

left_space, center, right_space = st.columns(
    [1, 2, 1]
)

with center:

    st.title(
        "🏔️ Everest Base Camp"
    )

    st.subheader(
        "Room Availability & Price Checker"
    )

    st.write(
        "Check live room availability and per-night pricing "
        "for your selected stay dates."
    )


st.divider()


# ============================================================
# DATE SELECTION
# ============================================================

st.header(
    "Select Your Stay Dates"
)


date_col1, date_col2, button_col = st.columns(
    [1, 1, 0.55]
)


# ============================================================
# CHECK-IN
# ============================================================

with date_col1:

    check_in = st.date_input(
        "Check-in",
        value=date.today(),
        min_value=date.today(),
        format="DD-MM-YYYY",
    )


# ============================================================
# CHECK-OUT
# ============================================================

with date_col2:

    minimum_checkout = (
        check_in + timedelta(days=1)
    )

    check_out = st.date_input(
        "Check-out",
        value=minimum_checkout,
        min_value=minimum_checkout,
        format="DD-MM-YYYY",
    )


# ============================================================
# CHECK AVAILABILITY BUTTON
# ============================================================

with button_col:

    st.write("")
    st.write("")

    check_availability = st.button(
        "🔍 Check Availability",
        type="primary",
        use_container_width=True,
    )


# ============================================================
# DATE VALIDATION
# ============================================================

if check_out <= check_in:

    st.error(
        "Check-out date must be after the check-in date."
    )

    st.stop()


# ============================================================
# RUN SCRAPER
# ============================================================

if check_availability:

    # --------------------------------------------------------
    # Convert dates to main.py format
    # --------------------------------------------------------

    check_in_str = check_in.strftime(
        "%d-%m-%Y"
    )

    check_out_str = check_out.strftime(
        "%d-%m-%Y"
    )


    # --------------------------------------------------------
    # Create data directory
    # --------------------------------------------------------

    DATA_DIR.mkdir(
        exist_ok=True
    )


    # --------------------------------------------------------
    # Delete old results
    #
    # This prevents an old search from being displayed.
    # --------------------------------------------------------

    for old_file in [
        JSON_FILE,
        TEXT_FILE,
    ]:

        try:

            if old_file.exists():
                old_file.unlink()

        except Exception:
            pass


    # --------------------------------------------------------
    # Build main.py command
    # --------------------------------------------------------

    command = [
        sys.executable,
        str(MAIN_FILE),
        "--check-in",
        check_in_str,
        "--check-out",
        check_out_str,
    ]


    # --------------------------------------------------------
    # Windows UTF-8 configuration
    #
    # Prevents errors from characters such as ✓.
    # --------------------------------------------------------

    environment = os.environ.copy()

    environment["PYTHONIOENCODING"] = "utf-8"

    environment["PYTHONUTF8"] = "1"


    # --------------------------------------------------------
    # Execute main.py
    # --------------------------------------------------------

    with st.spinner(
        "Checking room availability..."
    ):

        try:

            result = subprocess.run(
                command,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
            )

        except Exception as error:

            st.error(
                f"Unable to start the room scraper: {error}"
            )

            st.stop()


    # ========================================================
    # CHECK SCRAPER ERROR
    # ========================================================

    if result.returncode != 0:

        st.error(
            "Unable to fetch room availability."
        )


        if result.stderr:

            with st.expander(
                "Show technical details"
            ):

                st.code(
                    result.stderr,
                    language="text",
                )

        st.stop()


    # ========================================================
    # CHECK JSON FILE
    # ========================================================

    if not JSON_FILE.exists():

        st.warning(
            "No room availability data was returned."
        )

        st.stop()


    # ========================================================
    # READ JSON
    # ========================================================

    try:

        with open(
            JSON_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except Exception as error:

        st.error(
            f"Unable to read room results: {error}"
        )

        st.stop()


    # ========================================================
    # GET ROOMS
    # ========================================================

    rooms = data.get(
        "rooms",
        []
    )


    # ========================================================
    # SAVE SEARCH STATE
    # ========================================================

    st.session_state.searched = True

    st.session_state.rooms_found = len(
        rooms
    )

    st.session_state.search_check_in = (
        check_in
    )

    st.session_state.search_check_out = (
        check_out
    )


    # ========================================================
    # READ TEXT GENERATED BY main.py
    # ========================================================

    availability_text = ""


    if TEXT_FILE.exists():

        try:

            availability_text = (
                TEXT_FILE.read_text(
                    encoding="utf-8"
                ).strip()
            )

        except Exception:

            availability_text = ""


    # ========================================================
    # FALLBACK FORMATTER
    #
    # Used only if main.py did not create
    # room_availability.txt.
    # ========================================================

    if not availability_text:

        room_prices = {}


        # ====================================================
        # IDENTIFY ROOM TYPES
        # ====================================================

        for room in rooms:

            name = room.get(
                "name",
                ""
            )

            price = room.get(
                "price"
            )


            # Skip invalid records

            if not name:
                continue

            if price is None:
                continue


            name_lower = name.lower()


            # ------------------------------------------------
            # Surveyor Suite must come before Surveyor
            # ------------------------------------------------

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


        # ====================================================
        # ROUND DOWN TO NEAREST ₹100
        # ====================================================

        def round_down_100(value):

            return (
                int(value) // 100
            ) * 100


        # ====================================================
        # FORMAT INDIAN PRICE
        # ====================================================

        def money(value):

            return f"{value:,}"


        # ====================================================
        # BUILD AVAILABILITY MESSAGE
        # ====================================================

        lines = []

        lines.append(
            "For , Here is the Room availability "
            "with prices below:"
        )


        # ====================================================
        # CAMPER
        # ====================================================

        if "camper" in room_prices:

            price = round_down_100(
                room_prices["camper"]
            )

            lines.append(
                "The Camper room (2 occupants) "
                "is available for "
                f"Rs. {money(price)} "
                "plus taxes per night."
            )


        # ====================================================
        # GLAMPER
        # ====================================================

        if "glamper" in room_prices:

            price = round_down_100(
                room_prices["glamper"]
            )

            lines.append(
                "The Glamper room (2 occupants) "
                "is available for "
                f"Rs. {money(price)} "
                "plus taxes per night. "
                "(We have 4 Glamper rooms)"
            )


        # ====================================================
        # SURVEYOR
        # ====================================================

        if "surveyor" in room_prices:

            price = round_down_100(
                room_prices["surveyor"]
            )

            lines.append(
                "The Surveyor room (2 occupants) "
                "is available for "
                f"Rs. {money(price)} "
                "plus taxes per night."
            )


        # ====================================================
        # SURVEYOR SUITE
        # ====================================================

        if "surveyor_suite" in room_prices:

            price = round_down_100(
                room_prices["surveyor_suite"]
            )

            lines.append(
                "The Surveyor suite room (2 occupants) "
                "is available for "
                f"Rs. {money(price)} "
                "plus taxes per night."
            )


        # ====================================================
        # ZENITH
        # ====================================================

        if "zenith" in room_prices:

            price = round_down_100(
                room_prices["zenith"]
            )

            lines.append(
                "The Zenith luxury cottage "
                "(2 occupants) is available for "
                f"Rs. {money(price)} "
                "plus taxes per night."
            )


        # ====================================================
        # TWIN LUXURY COTTAGE
        # ====================================================

        if "twin_luxury" in room_prices:

            price = round_down_100(
                room_prices["twin_luxury"]
            )

            lines.append(
                "The twin luxury cottage "
                "(2 occupants / Room) is available "
                f"for Rs. {money(price)} "
                "plus taxes per night. "
                "(2 Rooms next to each other)"
            )


        # ====================================================
        # VILLA
        # ====================================================

        if "villa" in room_prices:

            # Villa contains 2 rooms.

            villa_price = (
                room_prices["villa"] * 2
            )

            # Round final Villa price down
            # to nearest ₹100.

            villa_price = round_down_100(
                villa_price
            )

            lines.append(
                "The Villa (2 occupants/room) "
                "is available for "
                f"Rs. {money(villa_price)} "
                "plus taxes per night. "
                "(2 Rooms villa)"
            )


        # ====================================================
        # FINAL TEXT
        # ====================================================

        availability_text = "\n".join(
            lines
        )


    # ========================================================
    # SAVE RESULT
    # ========================================================

    st.session_state.availability_text = (
        availability_text
    )


# ============================================================
# DISPLAY RESULTS
# ============================================================

if st.session_state.searched:

    st.divider()


    # ========================================================
    # SUCCESS MESSAGE
    # ========================================================

    st.success(
        f"Availability found for "
        f"{st.session_state.rooms_found} "
        f"room type(s)."
    )


    # ========================================================
    # DATE SUMMARY
    # ========================================================

    result_check_in = (
        st.session_state.search_check_in
    )

    result_check_out = (
        st.session_state.search_check_out
    )


    st.info(
        f"Check-in: "
        f"{result_check_in.strftime('%d-%m-%Y')}"
        f"  →  "
        f"Check-out: "
        f"{result_check_out.strftime('%d-%m-%Y')}"
    )


    # ========================================================
    # ROOM AVAILABILITY
    # ========================================================

    st.header(
        "Room Availability"
    )


    # ========================================================
    # COPYABLE RESULT
    #
    # st.code() provides the native Copy button.
    # ========================================================

    st.code(
        st.session_state.availability_text,
        language=None,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Everest Base Camp Room Availability System"
)

st.caption(
    "Prices are shown per room, per night, "
    "plus applicable taxes."
)