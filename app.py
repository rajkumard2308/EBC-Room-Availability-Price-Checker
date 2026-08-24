import streamlit as st
from datetime import date, timedelta
import main


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Everest Base Camp | Room Availability",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* Main page */
    .main {
        padding-top: 1rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f7f9fc;
        border-right: 1px solid #e5e7eb;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 2rem;
    }

    /* Main title */
    .main-title {
        text-align: center;
        font-size: 42px;
        font-weight: 800;
        color: #172554;
        margin-top: -80px;
        margin-bottom: 5px;
    }

    .main-subtitle {
        text-align: center;
        font-size: 20px;
        font-weight: 600;
        color: #334155;
        margin-bottom: 8px;
    }

    .main-description {
        text-align: center;
        color: #64748b;
        font-size: 15px;
        margin-bottom: 25px;
    }

    /* Availability heading */
    .availability-title {
        font-size: 30px;
        font-weight: 750;
        color: #172554;
        margin-top: 10px;
        margin-bottom: 12px;
    }

    /* Result box */
    .result-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-top: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    /* Sidebar heading */
    .sidebar-title {
        font-size: 22px;
        font-weight: 750;
        color: #172554;
        margin-bottom: 5px;
    }

    .sidebar-description {
        font-size: 14px;
        color: #64748b;
        margin-bottom: 20px;
    }

    /* Hide Streamlit menu/footer */
    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🏔️ Everest Base Camp</div>',
    unsafe_allow_html=True,
)

st.divider()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-title">📅 Select Stay Dates</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="sidebar-description">
            Select your check-in and check-out dates
            to check live room availability.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Default dates
    # --------------------------------------------------------

    today = date.today()
    default_check_in = today + timedelta(days=1)
    default_check_out = today + timedelta(days=2)

    check_in_date = st.date_input(
        "Check-in",
        value=default_check_in,
        min_value=today,
        format="DD-MM-YYYY",
        key="check_in_date",
    )

    check_out_date = st.date_input(
        "Check-out",
        value=default_check_out,
        min_value=today,
        format="DD-MM-YYYY",
        key="check_out_date",
    )

    st.write("")

    check_button = st.button(
        "🔎 Check Availability",
        type="primary",
        use_container_width=True,
    )

    st.write("")

    st.caption(
        "Prices are shown per room per night "
        "and rounded according to the configured pricing rule."
    )


# ============================================================
# INITIAL STATE
# ============================================================

if "result" not in st.session_state:
    st.session_state.result = None

if "error" not in st.session_state:
    st.session_state.error = None


# ============================================================
# CHECK AVAILABILITY
# ============================================================

if check_button:

    # --------------------------------------------------------
    # Validate dates
    # --------------------------------------------------------

    if check_out_date <= check_in_date:

        st.session_state.result = None
        st.session_state.error = (
            "Check-out date must be after the check-in date."
        )

    else:

        st.session_state.error = None

        check_in = check_in_date.strftime("%d-%m-%Y")
        check_out = check_out_date.strftime("%d-%m-%Y")

        # ----------------------------------------------------
        # Scraping
        # ----------------------------------------------------

        with st.status(
            "Checking live room availability...",
            expanded=False,
        ) as status:

            try:

                result = main.scrape_availability(
                    check_in,
                    check_out,
                )

                st.session_state.result = result

                status.update(
                    label="Room availability found.",
                    state="complete",
                    expanded=False,
                )

            except Exception as e:

                st.session_state.result = None
                st.session_state.error = str(e)

                status.update(
                    label="Unable to fetch room availability.",
                    state="error",
                    expanded=False,
                )


# ============================================================
# ERROR
# ============================================================

if st.session_state.error:

    st.error(
        st.session_state.error
    )


# ============================================================
# RESULT
# ============================================================

result = st.session_state.result


if result:

    rooms = result.get(
        "rooms",
        []
    )

    availability_text = result.get(
        "availability_text",
        ""
    )

    check_in = result.get(
        "check_in",
        ""
    )

    check_out = result.get(
        "check_out",
        ""
    )

    # --------------------------------------------------------
    # Success message
    # --------------------------------------------------------

    st.success(
        f"Availability found for {len(rooms)} room type(s)."
    )

    # --------------------------------------------------------
    # Selected dates
    # --------------------------------------------------------

    st.info(
        f"Check-in: {check_in}  →  Check-out: {check_out}"
    )

    # --------------------------------------------------------
    # ROOM AVAILABILITY
    # --------------------------------------------------------

    st.markdown(
        '<div class="availability-title">Room Availability</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Result text
    #
    # st.code() provides the COPY button automatically.
    # --------------------------------------------------------

    st.code(
        availability_text,
        language=None,
    )


# ============================================================
# BEFORE SEARCH
# ============================================================

else:

    if not st.session_state.error:
        st.subheader("Check Room Availability")
        st.write(
            "Select your stay dates from the left "
            "and click **Check Availability**."
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        color:#94a3b8;
        font-size:13px;
        padding:10px;
    ">
        Everest Base Camp Room Availability System
        <br>
        Prices shown are per room, per night,
        plus applicable taxes.
    </div>
    """,
    unsafe_allow_html=True,
)