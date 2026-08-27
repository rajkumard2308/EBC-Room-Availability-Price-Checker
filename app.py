import streamlit as st
from datetime import date, timedelta
import main

st.set_page_config(
    page_title="Everest Base Camp | Room Availability",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .main { padding-top: 0 !important; }
    .block-container {
        max-width: 1100px;
        padding-top: 1.25rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    /* Main title - responsive for desktop and mobile */
    .main-title {
        width: 100%;
        text-align: center;
        font-size: clamp(28px, 5vw, 42px);
        font-weight: 800;
        line-height: 1.2;
        color: #172554;
        margin: 18px 0 6px 0;
        padding: 0 10px;
        box-sizing: border-box;
        overflow: visible;
        word-break: normal;
    }
    .main-description {
        width: 100%;
        text-align: center;
        color: #64748b;
        font-size: 15px;
        line-height: 1.5;
        margin: 0 0 18px 0;
    }

    .date-title {
        text-align: center;
        font-size: 27px;
        font-weight: 750;
        color: #172554;
        line-height: 1.3;
        margin: 4px 0 3px 0;
    }

    .date-description {
        text-align: center;
        font-size: 14px;
        color: #64748b;
        line-height: 1.5;
        margin: 0 0 14px 0;
    }

    div[data-testid="stDateInput"] label {
        color: #334155 !important;
        font-weight: 600 !important;
    }

    div[data-testid="stDateInput"] input { border-radius: 10px !important; }

    div.stButton > button {
        min-height: 46px;
        border-radius: 10px;
        font-size: 15px;
        font-weight: 650;
    }

    .pricing-note {
        text-align: center;
        color: #64748b;
        font-size: 13px;
        line-height: 1.5;
        margin: 8px 0 20px 0;
    }

    .availability-title {
        font-size: 30px;
        font-weight: 750;
        color: #172554;
        line-height: 1.3;
        margin: 20px 0 10px 0;
    }

    pre {
        white-space: pre-wrap !important;
        overflow-wrap: anywhere !important;
        word-break: break-word !important;
    }

    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 13px;
        line-height: 1.6;
        padding: 12px 8px;
        margin-top: 18px;
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    @media (max-width: 768px) {
        .block-container {
            max-width: 100%;
            padding-top: 0.75rem !important;
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
            padding-bottom: 1.5rem !important;
        }

        .main-title {
            font-size: 30px;
            line-height: 1.25;
            margin-top: 28px;
            margin-bottom: 6px;
            padding-top: 0;
        }

        .main-description { font-size: 13px; margin-bottom: 12px; }
        .date-title { font-size: 23px; margin-top: 2px; margin-bottom: 3px; }
        .date-description { font-size: 13px; margin-bottom: 10px; }
        .availability-title { font-size: 25px; margin-top: 18px; }
        .pricing-note { font-size: 12px; margin-top: 7px; margin-bottom: 15px; }

        div.stButton > button {
            min-height: 46px;
            font-size: 14px;
        }

        pre {
            font-size: 12px !important;
            line-height: 1.55 !important;
        }

        .footer { font-size: 12px; }
    }

    @media (max-width: 420px) {
        .main-title {
            font-size: 24px;
            line-height: 1.25;
        }
        .date-title { font-size: 21px; }
        .block-container {
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SESSION STATE
# ============================================================

today = date.today()

if "check_in_date" not in st.session_state:
    st.session_state.check_in_date = today + timedelta(days=1)

if "check_out_date" not in st.session_state:
    st.session_state.check_out_date = st.session_state.check_in_date + timedelta(days=1)

if "result" not in st.session_state:
    st.session_state.result = None

if "error" not in st.session_state:
    st.session_state.error = None


def update_checkout_date():
    """Set checkout to one day after the newly selected check-in date."""
    st.session_state.check_out_date = (
        st.session_state.check_in_date + timedelta(days=1)
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🏔️ Everest Base Camp</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-description">Room Availability &amp; Price Checker</div>',
    unsafe_allow_html=True,
)

st.divider()


# ============================================================
# DATE SELECTION
# ============================================================

st.markdown(
    '<div class="date-title">📅 Select Stay Dates</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="date-description">'
    'Select your check-in and check-out dates to check live room availability.'
    '</div>',
    unsafe_allow_html=True,
)


date_col1, date_col2 = st.columns(2, gap="medium")

with date_col1:
    check_in_date = st.date_input(
        "Check-in",
        min_value=today,
        format="DD-MM-YYYY",
        key="check_in_date",
        on_change=update_checkout_date,
    )

check_out_min = check_in_date + timedelta(days=1)

if st.session_state.check_out_date <= check_in_date:
    st.session_state.check_out_date = check_out_min

with date_col2:
    check_out_date = st.date_input(
        "Check-out",
        min_value=check_out_min,
        format="DD-MM-YYYY",
        key="check_out_date",
    )

st.write("")

button_col1, button_col2, button_col3 = st.columns([1, 2, 1])

with button_col2:
    check_button = st.button(
        "🔎 Check Availability",
        type="primary",
        use_container_width=True,
    )

st.markdown(
    '<div class="pricing-note">'
    'Prices are shown per room per night and rounded according to the '
    'configured pricing rule.'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# CHECK AVAILABILITY
# ============================================================

if check_button:
    if check_out_date <= check_in_date:
        st.session_state.result = None
        st.session_state.error = "Check-out date must be after the check-in date."
    else:
        st.session_state.error = None
        check_in = check_in_date.strftime("%d-%m-%Y")
        check_out = check_out_date.strftime("%d-%m-%Y")

        with st.status("Checking live room availability...", expanded=False) as status:
            try:
                result = main.scrape_availability(check_in, check_out)
                st.session_state.result = result
                status.update(
                    label="Room availability found.",
                    state="complete",
                    expanded=False,
                )
            except Exception as e:
                st.session_state.result = None
                st.session_state.error = f"Unable to fetch room availability: {e}"
                status.update(
                    label="Unable to fetch room availability.",
                    state="error",
                    expanded=False,
                )


# ============================================================
# ERROR
# ============================================================

if st.session_state.error:
    st.error(st.session_state.error)


# ============================================================
# RESULT
# ============================================================

result = st.session_state.result

if result:
    rooms = result.get("rooms", [])
    availability_text = result.get("availability_text", "")
    check_in = result.get("check_in", "")
    check_out = result.get("check_out", "")

    st.success(f"Availability found for {len(rooms)} room type(s).")

    st.info(f"Check-in: {check_in} → Check-out: {check_out}")

    st.markdown(
        '<div class="availability-title">Room Availability</div>',
        unsafe_allow_html=True,
    )

    # Native Streamlit code block keeps the text plain and provides Copy.
    st.code(availability_text, language=None)


# ============================================================
# BEFORE SEARCH
# ============================================================

else:
    if not st.session_state.error:
        st.markdown(
            """
            <div style="
                text-align:center;
                padding:30px 15px 35px 15px;
                color:#64748b;
            ">
                <div style="font-size:42px; line-height:1.2; margin-bottom:8px;">🏕️</div>
                <div style="font-size:22px; font-weight:700; color:#334155; line-height:1.3;">
                    Check Room Availability
                </div>
                <div style="font-size:14px; margin-top:7px; line-height:1.5;">
                    Select your stay dates above and click <b>Check Availability</b>.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div class="footer">
        Everest Base Camp Room Availability System
        <br>
        Prices shown are per room, per night, plus applicable taxes.
    </div>
    """,
    unsafe_allow_html=True,
)
