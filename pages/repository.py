import streamlit as st
import time


# =========================================
# PAGE CONFIGURATION
# =========================================

st.set_page_config(
    page_title="Analyze Repository",
    page_icon="🔍",
    layout="wide"
)


# =========================================
# SESSION STATE
# =========================================

if "repo_owner" not in st.session_state:
    st.session_state.repo_owner = ""

if "repo_name" not in st.session_state:
    st.session_state.repo_name = ""

if "analysis_started" not in st.session_state:
    st.session_state.analysis_started = False


# =========================================
# PAGE HEADER
# =========================================

st.title("🔍 Analyze Repository")

st.write(
    "Enter a GitHub repository to analyze contributor activity "
    "and understand contributor retention."
)

st.divider()


# =========================================
# REPOSITORY DETAILS
# =========================================

st.subheader("Repository Details")


owner = st.text_input(
    "Repository Owner",
    value=st.session_state.repo_owner,
    placeholder="e.g. flutter"
)


repo = st.text_input(
    "Repository Name",
    value=st.session_state.repo_name,
    placeholder="e.g. flutter"
)


# =========================================
# ANALYZE BUTTON
# =========================================

if st.button(
    "🚀 Analyze Repository",
    type="primary"
):

    # Remove unnecessary spaces
    owner = owner.strip()
    repo = repo.strip()

    # -----------------------------------------
    # VALIDATION
    # -----------------------------------------

    if not owner or not repo:

        st.error(
            "Please enter both the repository owner "
            "and repository name."
        )

    else:

        # -----------------------------------------
        # SAVE REPOSITORY
        # -----------------------------------------

        st.session_state.repo_owner = owner
        st.session_state.repo_name = repo

        st.session_state.analysis_started = True


        # -----------------------------------------
        # SIMULATED ANALYSIS
        # -----------------------------------------

        with st.spinner("Analyzing repository..."):

            time.sleep(1)
            st.success("✓ Repository verified")

            time.sleep(1)
            st.success("✓ Contributors collected")

            time.sleep(1)
            st.success("✓ Pull requests collected")

            time.sleep(1)
            st.success("✓ Reviews collected")

            time.sleep(1)
            st.success("✓ Analysis complete")


        # -----------------------------------------
        # ANALYSIS COMPLETE
        # -----------------------------------------

        st.divider()

        st.subheader("✅ Analysis Ready")

        st.write(
            f"Repository **{owner}/{repo}** "
            "has been analyzed successfully."
        )

        st.info(
            "Your contributor retention dashboard is ready."
        )


# =========================================
# DASHBOARD NAVIGATION
# =========================================

if st.session_state.analysis_started:

    st.divider()

    st.subheader("📊 View Results")

    st.write(
        "Open the dashboard to view contributor "
        "retention and activity metrics."
    )

    st.page_link(
        "pages/dashboard.py",
        label="📊 View Contributor Dashboard",
        
    )