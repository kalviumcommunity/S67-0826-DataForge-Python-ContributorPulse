"""ContributorPulse - Maintainer Intelligence & Contributor Retention Platform."""

import streamlit as st

st.set_page_config(
    page_title="ContributorPulse | Maintainer Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 ContributorPulse")
st.subheader("Maintainer Intelligence & Contributor Retention Platform")

st.write(
    "ContributorPulse empowers open-source maintainers to understand first-time contributor "
    "onboarding journeys, response velocity, code review turnaround times, and predictive churn risk."
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🔍 1. Ingest & Analyze")
    st.write(
        "Enter any GitHub repository to trigger an automated ingestion and cleaning pipeline. "
        "Normalizes commit, PR, review, and comment activity into durable PostgreSQL storage."
    )
    st.page_link("pages/repository.py", label="Go to Repository Ingestion", icon="🔍")

with col2:
    st.markdown("### 📊 2. Health & Velocity Dashboard")
    st.write(
        "Explore 6 dedicated intelligence views: Overview & Health, Contributor Retention Funnels, "
        "Response Distribution, Merge Analytics, Churn Risk Alerts, and Repository Benchmarking."
    )
    st.page_link("pages/dashboard.py", label="Go to Analytics Dashboard", icon="📊")

with col3:
    st.markdown("### 👥 3. Contributor Journeys")
    st.write(
        "Drill down into individual contributor paths with multi-parameter filtering, "
        "risk scores, and transparent penalty reasons."
    )
    st.page_link("pages/contributors.py", label="Go to Contributor Journeys", icon="👥")

st.divider()

st.info(
    "💡 **Quick Start**: Use the sidebar to enter a repository (e.g. `kalviumcommunity/S67-0826-DataForge-Python-ContributorPulse`) "
    "and start exploring the retention analytics."
)
