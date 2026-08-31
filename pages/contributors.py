import pandas as pd
import streamlit as st

from api_client import (
    APIClientError,
    BackendAPIClient,
)

# ==============================================================================
# Page Configuration
# ==============================================================================

st.set_page_config(
    page_title="ContributorPulse | Contributor Journeys",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

client = BackendAPIClient()

owner = st.session_state.get("owner", "")
repo = st.session_state.get("repository", "")

# ==============================================================================
# Page Header & Context
# ==============================================================================

st.title("👥 Contributor Journeys & Segmentation")
st.write(
    "Explore individual contributor onboarding paths, review responsiveness, "
    "retention status, and explainable churn risk assessments."
)
st.divider()

if not owner or not repo:
    st.info(
        "👈 Please enter a repository owner and name in the **Dashboard** or **Analyze Repository** page first."
    )
    try:
        st.page_link("pages/dashboard.py", label="📊 Go to Dashboard", icon="📊")
    except Exception:
        pass
    st.stop()

# ==============================================================================
# Filters & Search Toolbar
# ==============================================================================

st.subheader("Filter & Search Contributors")

c1, c2, c3, c4 = st.columns(4)

with c1:
    search_query = st.text_input("🔍 Search Login / Name", placeholder="e.g. alice")
with c2:
    exp_filter = st.selectbox(
        "Experience Level",
        ["All", "first_time", "repeat", "core"],
        index=0,
    )
with c3:
    ret_filter = st.selectbox(
        "Retention Status",
        ["All", "onboarding", "retained", "churned"],
        index=0,
    )
with c4:
    risk_filter = st.selectbox(
        "Churn Risk Level",
        ["All", "low", "medium", "high"],
        index=0,
    )

col_page_size, col_page_num = st.columns([1, 1])
with col_page_size:
    per_page = st.select_slider("Items Per Page", options=[10, 20, 50, 100], value=20)
with col_page_num:
    page_num = st.number_input("Page Number", min_value=1, value=1, step=1)

# ==============================================================================
# Fetch & Render Contributor Data
# ==============================================================================

period_filter = st.session_state.get("time_period", "All Ingested History")

try:
    with st.spinner("Fetching contributor journeys from backend..."):
        res = client.get_contributors(
            owner=owner,
            repo=repo,
            page=page_num,
            per_page=per_page,
            experience_level=None if exp_filter == "All" else exp_filter,
            retention_status=None if ret_filter == "All" else ret_filter,
            churn_risk_level=None if risk_filter == "All" else risk_filter,
            search=search_query.strip() if search_query.strip() else None,
            period=period_filter,
        )

    if not res or not res.get("items"):
        st.warning("⚠️ No contributors match the selected filters.")
    else:
        items = res.get("items", [])
        pagination = res.get("pagination", {})
        total_records = pagination.get("total_records", len(items))
        total_pages = pagination.get("total_pages", 1)

        st.caption(
            f"Showing **{len(items)}** of **{total_records}** contributors (Page {page_num} of {total_pages}) | Cohort Window: **{period_filter}**"
        )

        df = pd.DataFrame(items)

        display_cols = [
            "login",
            "experience_level",
            "retention_status",
            "churn_risk_level",
            "churn_risk_score",
            "total_prs",
            "merged_prs",
            "first_response_hours",
            "first_review_hours",
            "risk_reason",
        ]
        available_cols = [c for c in display_cols if c in df.columns]

        st.dataframe(
            df[available_cols].rename(
                columns={
                    "login": "Contributor",
                    "experience_level": "Experience",
                    "retention_status": "Retention",
                    "churn_risk_level": "Risk Tier",
                    "churn_risk_score": "Risk Score (0-1)",
                    "total_prs": "Total PRs",
                    "merged_prs": "Merged PRs",
                    "first_response_hours": "First Response (hrs)",
                    "first_review_hours": "First Review (hrs)",
                    "risk_reason": "Identified Risk Reasons",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

except APIClientError as exc:
    st.error(f"⚠️ Error fetching contributors: {exc.message}")
except Exception:
    st.error("⚠️ Unexpected error: An unexpected error occurred while fetching contributors.")
