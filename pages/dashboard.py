import streamlit as st
import pandas as pd


# =========================================
# PAGE CONFIGURATION
# =========================================

st.set_page_config(
    page_title="Dashboard | Analyse Retain",
    page_icon="📊",
    layout="wide"
)


# =========================================
# GET REPOSITORY FROM SESSION STATE
# =========================================

repo_owner = st.session_state.get(
    "repo_owner",
    ""
)

repo_name = st.session_state.get(
    "repo_name",
    ""
)

analysis_started = st.session_state.get(
    "analysis_started",
    False
)


# =========================================
# PAGE HEADER
# =========================================

st.title("📊 Contributor Retention Dashboard")

st.write(
    "Understand contributor activity and retention "
    "in your GitHub repository."
)

st.divider()


# =========================================
# REPOSITORY OVERVIEW
# =========================================

st.subheader("Repository Overview")


col1, col2, col3 = st.columns(3)


# -----------------------------------------
# Repository
# -----------------------------------------

with col1:

    if repo_owner and repo_name:

        repository_name = (
            f"{repo_owner}/{repo_name}"
        )

    else:

        repository_name = "No repository selected"

    st.metric(
        "Repository",
        repository_name
    )


# -----------------------------------------
# Analysis Period
# -----------------------------------------

with col2:

    st.metric(
        "Analysis Period",
        "Last 30 Days"
    )


# -----------------------------------------
# Analysis Status
# -----------------------------------------

with col3:

    if analysis_started:

        status = "Complete"

    else:

        status = "Not Started"

    st.metric(
        "Analysis Status",
        status
    )


st.divider()


# =========================================
# CHECK IF REPOSITORY EXISTS
# =========================================

if not repo_owner or not repo_name:

    st.warning(
        "⚠️ No repository has been analyzed yet."
    )

    st.write(
        "Please select **Repository** from the sidebar "
        "and analyze a repository first."
    )

    st.page_link(
        "pages/repository.py",
        label="🔍 Go to Repository Analysis",
        icon="🔍"
    )

    st.stop()


# =========================================
# KPI METRICS
# =========================================

st.subheader("Contributor Metrics")


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Active Contributors",
        "42"
    )


with col2:

    st.metric(
        "First-time Contributors",
        "18"
    )


with col3:

    st.metric(
        "Returned Contributors",
        "9"
    )


with col4:

    st.metric(
        "Retention Rate",
        "50%"
    )


st.divider()


# =========================================
# CONTRIBUTOR RETENTION
# =========================================

st.subheader("Contributor Retention")

st.write(
    "This shows how many first-time contributors "
    "continued contributing after their initial contribution."
)


retention_data = pd.DataFrame(
    {
        "Category": [
            "First-time Contributors",
            "Returned Contributors",
            "Dropped-off Contributors"
        ],

        "Count": [
            18,
            9,
            9
        ]
    }
)


st.bar_chart(
    retention_data.set_index("Category")
)


st.divider()


# =========================================
# CONTRIBUTOR ACTIVITY
# =========================================

st.subheader("Contributor Activity")

st.write(
    "This shows the overall contribution activity "
    "in the analyzed repository."
)


activity_data = pd.DataFrame(
    {
        "Activity": [
            "Commits",
            "Issues",
            "Pull Requests",
            "Reviews"
        ],

        "Count": [
            67,
            15,
            24,
            31
        ]
    }
)


st.bar_chart(
    activity_data.set_index("Activity")
)


st.divider()


# =========================================
# CURRENT REPOSITORY
# =========================================

st.subheader("Analyzed Repository")

st.info(
    f"📁 **{repo_owner}/{repo_name}**"
)