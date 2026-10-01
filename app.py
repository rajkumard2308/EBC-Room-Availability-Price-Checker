import json
from datetime import date, timedelta

import streamlit as st
import streamlit.components.v1 as components

import main


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="EBC Room Availability",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* =====================================================
       MAIN CONTAINER
       ===================================================== */

    .block-container {
        max-width: 1200px;
        padding-top: 3rem;
        padding-bottom: 2rem;
    }

    /* =====================================================
       HEADER
       ===================================================== */

    .app-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin: 0 0 4px 0;
    }

    .app-icon {
        font-size: 42px;
        line-height: 1;
    }

    .app-title {
        font-size: 42px;
        font-weight: 750;
        letter-spacing: -1px;
        line-height: 1.15;
    }

    .app-subtitle {
        font-size: 22px;
        font-weight: 600;
        margin-top: 8px;
        margin-bottom: 28px;
    }

    /* =====================================================
       DATE INPUT
       ===================================================== */

    div[data-testid="stDateInput"] label {
        font-weight: 600 !important;
        font-size: 15px !important;
    }

    div[data-testid="stDateInput"] input {
        border-radius: 9px !important;
        min-height: 45px !important;
    }

    /* =====================================================
       BUTTON
       ===================================================== */

    div.stButton > button {
        width: 100%;
        min-height: 48px;
        border-radius: 9px;
        font-size: 16px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    div.stButton > button:hover {
        transform: translateY(-1px);
    }

    /* =====================================================
       SUCCESS MESSAGE
       ===================================================== */

    div[data-testid="stAlert"] {
        border-radius: 9px !important;
        margin-top: 10px;
        margin-bottom: 26px;
    }

    /* =====================================================
       SECTION TITLE
       ===================================================== */

    .section-title {
        font-size: 30px;
        font-weight: 750;
        letter-spacing: -0.5px;
        margin: 0 0 14px 0;
        padding: 0;
    }

    /* =====================================================
       SUMMARY INTRO
       ===================================================== */

    .summary-intro {
        font-size: 16px;
        font-weight: 600;
        line-height: 1.5;
        margin: 0 0 10px 0;
        padding: 0;
    }

    /* =====================================================
       SUMMARY CONTAINER
       ===================================================== */

    .summary-box {
        border: none;
        padding: 0;
        margin: 0 0 12px 0;
        background: transparent;
    }

    /* =====================================================
       ROOM LINES
       ===================================================== */

    .room-line {
        font-size: 16px;
        line-height: 1.5;
        padding: 0;
        margin: 0;
        border: none;
    }

    .room-line + .room-line {
        margin-top: 0;
    }

    /* =====================================================
       COPY BUTTON AREA
       ===================================================== */

    .copy-wrapper {
        margin-top: 14px;
        margin-bottom: 10px;
    }

    /* =====================================================
       MOBILE
       ===================================================== */

    @media (max-width: 768px) {

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1.5rem;
        }

        .app-title {
            font-size: 30px;
        }

        .app-icon {
            font-size: 32px;
        }

        .app-subtitle {
            font-size: 19px;
        }

        .section-title {
            font-size: 25px;
        }

        .summary-intro {
            font-size: 15px;
        }

        .room-line {
            font-size: 15px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="app-header">
        <div class="app-icon">🏨</div>
        <div class="app-title">Everest Base Camp</div>
    </div>

    <div class="app-subtitle">
        Room Availability & Price Checker
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATE INPUTS
# ============================================================

col1, col2 = st.columns(
    2,
    gap="large"
)


with col1:

    check_in = st.date_input(
        "Check-in Date",
        value=date.today(),
        min_value=date.today(),
        key="check_in_date",
    )


with col2:

    default_check_out = (
        check_in + timedelta(days=1)
    )

    check_out = st.date_input(
        "Check-out Date",
        value=default_check_out,
        min_value=(
            check_in + timedelta(days=1)
        ),
        key="check_out_date",
    )


# ============================================================
# CHECK AVAILABILITY BUTTON
# ============================================================

st.write("")

search_clicked = st.button(
    "🔍  Check Availability",
    type="primary",
    use_container_width=True,
)


# ============================================================
# FETCH AVAILABILITY
# ============================================================

if search_clicked:

    # --------------------------------------------------------
    # Validate dates
    # --------------------------------------------------------

    if check_out <= check_in:

        st.error(
            "Check-out date must be after "
            "check-in date."
        )

        st.stop()

    # --------------------------------------------------------
    # API call
    # --------------------------------------------------------

    try:

        with st.spinner(
            "Fetching live room availability..."
        ):

            result = main.scrape_availability(
                check_in=check_in,
                check_out=check_out,
                adults=2,
                children=0,
                rooms=1,
            )

        # Save result
        st.session_state[
            "availability_result"
        ] = result

    except Exception as exc:

        st.error(
            "Unable to fetch room availability."
        )

        with st.expander(
            "Show technical error"
        ):

            st.exception(exc)

        st.stop()


# ============================================================
# GET RESULT
# ============================================================

result = st.session_state.get(
    "availability_result"
)


# ============================================================
# DISPLAY RESULT
# ============================================================

if result:

    # ========================================================
    # SUCCESS
    # ========================================================

    st.success(
        "Availability fetched successfully!"
    )

    # ========================================================
    # TITLE
    # ========================================================

    st.markdown(
        '<div class="section-title">'
        'Room Availability Summary'
        '</div>',
        unsafe_allow_html=True,
    )

    # ========================================================
    # GET SUMMARY
    # ========================================================

    summary = result.get(
        "human_summary",
        ""
    )

    if summary:

        # ----------------------------------------------------
        # Split lines
        # ----------------------------------------------------

        lines = [
            line.strip()
            for line in summary.splitlines()
            if line.strip()
        ]

        if lines:

            # ------------------------------------------------
            # First line = intro
            # ------------------------------------------------

            intro = lines[0]

            room_lines = lines[1:]

            # ------------------------------------------------
            # Intro
            # ------------------------------------------------

            st.markdown(
                f'<div class="summary-intro">'
                f'{intro}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ------------------------------------------------
            # ROOM LINES
            # ------------------------------------------------

            room_html = ""

            for line in room_lines:

                if not line:
                    continue

                # Escape HTML
                safe_line = (
                    line
                    .replace(
                        "&",
                        "&amp;"
                    )
                    .replace(
                        "<",
                        "&lt;"
                    )
                    .replace(
                        ">",
                        "&gt;"
                    )
                )

                room_html += (
                    '<div class="room-line">'
                    f'{safe_line}'
                    '</div>'
                )

            # ------------------------------------------------
            # Display summary
            # ------------------------------------------------

            st.markdown(
                f"""
                <div class="summary-box">
                    {room_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # =================================================
            # COPY BUTTON
            # =================================================

            # Copy exactly the customer-ready text.
            #
            # There is intentionally NO blank line between
            # the room entries.

            copy_text = "\n".join(
                lines
            )

            copy_text_json = json.dumps(
                copy_text
            )

            copy_html = f"""
            <div class="copy-wrapper">

                <button
                    id="copyBtn"
                    onclick="copySummary()"
                    style="
                        background:#262730;
                        color:white;
                        border:1px solid
                            rgba(255,255,255,0.25);
                        border-radius:8px;
                        padding:10px 18px;
                        font-size:14px;
                        font-weight:600;
                        cursor:pointer;
                        transition:all 0.2s ease;
                    "
                    onmouseover="
                        this.style.background='#33343d';
                    "
                    onmouseout="
                        this.style.background='#262730';
                    "
                >
                    📋 Copy Summary
                </button>

                <span
                    id="copyStatus"
                    style="
                        margin-left:10px;
                        color:#00c853;
                        font-size:14px;
                        font-weight:600;
                    "
                ></span>

            </div>

            <script>

            function copySummary() {{

                const text = {copy_text_json};

                // Modern browser clipboard API
                if (
                    navigator.clipboard &&
                    window.isSecureContext
                ) {{

                    navigator.clipboard
                        .writeText(text)
                        .then(function() {{

                            showCopied();

                        }})
                        .catch(function() {{

                            fallbackCopy(text);

                        }});

                }} else {{

                    fallbackCopy(text);

                }}

            }}


            function fallbackCopy(text) {{

                const textarea =
                    document.createElement(
                        "textarea"
                    );

                textarea.value = text;

                textarea.style.position =
                    "fixed";

                textarea.style.left =
                    "-999999px";

                document.body.appendChild(
                    textarea
                );

                textarea.focus();

                textarea.select();

                try {{

                    document.execCommand(
                        "copy"
                    );

                    showCopied();

                }} catch (error) {{

                    document.getElementById(
                        "copyStatus"
                    ).innerText =
                        "Copy failed";

                }}

                textarea.remove();

            }}


            function showCopied() {{

                const status =
                    document.getElementById(
                        "copyStatus"
                    );

                status.innerText =
                    "✓ Copied";

                setTimeout(function() {{

                    status.innerText = "";

                }}, 2000);

            }}

            </script>
            """

            components.html(
                copy_html,
                height=55,
            )

        else:

            st.warning(
                "No rooms are available for "
                "the selected dates."
            )

    else:

        st.warning(
            "No rooms are available for "
            "the selected dates."
        )