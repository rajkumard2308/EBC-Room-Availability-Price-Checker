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
       SUMMARY HEADER
       ===================================================== */

    .summary-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        margin: 0 0 14px 0;
        padding: 0;
    }

    .section-title {
        font-size: 30px;
        font-weight: 750;
        letter-spacing: -0.5px;
        margin: 0;
        padding: 0;
        line-height: 1.2;
    }


    /* =====================================================
       COPY ICON
       ===================================================== */

    .copy-icon {
        width: 38px;
        height: 38px;
        border: 1px solid rgba(128, 128, 128, 0.45);
        border-radius: 7px;
        background: transparent;
        font-size: 18px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
    }

    .copy-icon:hover {
        background: rgba(128, 128, 128, 0.15);
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
        margin: 0;
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

        .copy-icon {
            width: 36px;
            height: 36px;
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


            # =================================================
            # COPY TEXT
            # =================================================

            copy_text = "\n".join(lines)

            copy_text_json = json.dumps(
                copy_text
            )


            # =================================================
            # SUMMARY HEADER
            # =================================================

            header_col, copy_col = st.columns(
                [0.86, 0.14],
                gap="small"
            )


            # -------------------------------------------------
            # Title
            # -------------------------------------------------

            with header_col:

                st.markdown(
                    """
                    <div class="section-title">
                        Room Availability Summary
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


            # -------------------------------------------------
            # Copy button
            # -------------------------------------------------

            with copy_col:

                copy_html = f"""
                <style>
                    html, body {{
                        margin: 0 !important;
                        padding: 0 !important;
                        overflow: visible !important;
                    }}

                    .copy-wrapper {{
                        width: 100%;
                        box-sizing: border-box;
                        height: 42px;
                        display: flex;
                        align-items: center;
                        justify-content: flex-end;
                    }}

                    .copy-icon {{
                        min-width: 42px;
                        height: 38px;
                        padding: 0 10px;
                        border: 1px solid rgba(128, 128, 128, 0.45);
                        border-radius: 7px;
                        background: transparent;
                        font-size: 17px;
                        font-weight: 600;
                        color: inherit;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 5px;
                        white-space: nowrap;
                        transition: all 0.2s ease;
                    }}

                    .copy-icon:hover {{
                        background: rgba(128, 128, 128, 0.15);
                    }}

                    .copy-icon.copied {{
                        width: 88px;
                        min-width: 88px;
                        box-sizing: border-box;
                        overflow: hidden;
                    }}

                    .copy-icon.failed {{
                        width: 88px;
                        min-width: 88px;
                        box-sizing: border-box;
                        overflow: hidden;
                    }}
                </style>

                <div class="copy-wrapper">
                    <button
                        id="copyButton"
                        onclick="copySummary()"
                        title="Copy Summary"
                        class="copy-icon"
                    >📋</button>
                </div>

                <script>
                const summaryText = {copy_text_json};

                function copySummary() {{

                    if (
                        navigator.clipboard &&
                        window.isSecureContext
                    ) {{

                        navigator.clipboard
                            .writeText(summaryText)
                            .then(function() {{
                                showCopied();
                            }})
                            .catch(function() {{
                                fallbackCopy(summaryText);
                            }});

                    }} else {{

                        fallbackCopy(summaryText);

                    }}
                }}


                function fallbackCopy(text) {{

                    const textarea =
                        document.createElement("textarea");

                    textarea.value = text;

                    textarea.style.position = "fixed";
                    textarea.style.left = "-999999px";
                    textarea.style.top = "0";
                    textarea.style.opacity = "0";

                    document.body.appendChild(textarea);

                    textarea.focus();
                    textarea.select();

                    let copied = false;

                    try {{
                        copied =
                            document.execCommand("copy");
                    }} catch (error) {{
                        copied = false;
                    }}

                    textarea.remove();

                    if (copied) {{
                        showCopied();
                    }} else {{
                        showCopyFailed();
                    }}
                }}


                function showCopied() {{

                    const button =
                        document.getElementById("copyButton");

                    button.innerHTML = "✓ Copied";
                    button.title = "Copied";
                    button.classList.remove("failed");
                    button.classList.add("copied");

                    setTimeout(function() {{

                        button.innerHTML = "📋";
                        button.title = "Copy Summary";
                        button.classList.remove("copied");

                    }}, 1500);
                }}


                function showCopyFailed() {{

                    const button =
                        document.getElementById("copyButton");

                    button.innerHTML = "✕ Failed";
                    button.title = "Copy failed";
                    button.classList.add("failed");

                    setTimeout(function() {{

                        button.innerHTML = "📋";
                        button.title = "Copy Summary";
                        button.classList.remove("failed");

                    }}, 1800);
                }}
                </script>
                """

                components.html(
                    copy_html,
                    height=42,
                )


            # =================================================
            # INTRO
            # =================================================

            st.markdown(
                f"""
                <div class="summary-intro">
                    {intro}
                </div>
                """,
                unsafe_allow_html=True,
            )


            # =================================================
            # ROOM LINES
            # =================================================

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


            # =================================================
            # DISPLAY SUMMARY
            # =================================================

            st.markdown(
                f"""
                <div class="summary-box">
                    {room_html}
                </div>
                """,
                unsafe_allow_html=True,
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