import streamlit as st
from api_client import (
    APIConnectionError,
    APINotFoundError,
    APIRateLimitError,
    APIServerError,
    APITimeoutError,
    APIValidationError,
    BackendAPIClient,
)

# =========================================
# PAGE CONFIGURATION
# =========================================

st.set_page_config(
    page_title="Analyze Repository",
    page_icon="🔍",
    layout="wide"
)

client = BackendAPIClient()

# =========================================
# SESSION STATE
# =========================================

if "owner" not in st.session_state:
    st.session_state["owner"] = ""

if "repository" not in st.session_state:
    st.session_state["repository"] = ""

if "analysis_started" not in st.session_state:
    st.session_state["analysis_started"] = False

if "analysis_run" not in st.session_state:
    st.session_state["analysis_run"] = None

if "repository_data" not in st.session_state:
    st.session_state["repository_data"] = None

if "repository_summary" not in st.session_state:
    st.session_state["repository_summary"] = None

if "repository_kpis" not in st.session_state:
    st.session_state["repository_kpis"] = None

# =========================================
# PAGE TITLE
# =========================================

st.title("🔍 Analyze Repository")

st.write(
    "Enter a GitHub repository to analyze contributor activity, "
    "onboarding velocity, and first-time contributor retention."
)

st.divider()

# =========================================
# REPOSITORY DETAILS FORM
# =========================================

st.subheader("Repository Details")

col_a, col_b = st.columns(2)
with col_a:
    owner = st.text_input(
        "Repository Owner",
        value=st.session_state["owner"],
        placeholder="e.g. kalviumcommunity",
    )
with col_b:
    repository = st.text_input(
        "Repository Name",
        value=st.session_state["repository"],
        placeholder="e.g. S67-0826-DataForge-Python-ContributorPulse",
    )

# =========================================
# ANALYZE BUTTON & EXECUTION
# =========================================

if st.button("🚀 Analyze Repository", type="primary"):
    owner = owner.strip()
    repository = repository.strip()

    if not owner or not repository:
        st.error("Please enter both the repository owner and repository name.")
    else:
        st.session_state["owner"] = owner
        st.session_state["repository"] = repository

        try:
            with st.spinner("Connecting to FastAPI backend and ingesting repository data..."):
                analysis_run = client.trigger_analysis(owner, repository)
                st.session_state["analysis_run"] = analysis_run
                st.session_state["analysis_started"] = True

            st.success(f"✓ Analysis triggered successfully (Status: {analysis_run.get('status', 'COMPLETED')})")

            with st.spinner("Fetching verified repository summary and health metrics..."):
                repo_data = client.get_repository(owner, repository)
                repo_summary = client.get_repository_summary(owner, repository)
                repo_kpis = client.get_repository_kpis(owner, repository)

                st.session_state["repository_data"] = repo_data
                st.session_state["repository_summary"] = repo_summary
                st.session_state["repository_kpis"] = repo_kpis

            st.success("✓ Repository data and KPIs retrieved from backend")

        except APINotFoundError as exc:
            st.session_state["analysis_started"] = False
            st.error(f"❌ {exc.message}")
        except APIValidationError as exc:
            st.error(f"⚠️ Validation Error: {exc.message}")
        except APITimeoutError as exc:
            st.error(f"⏱️ Timeout: {exc.message}")
        except APIConnectionError as exc:
            st.error(f"🔌 Connection Error: {exc.message}")
        except APIRateLimitError as exc:
            st.error(f"⏳ Rate Limit: {exc.message}")
        except APIServerError as exc:
            st.error(f"⚠️ Server Error: {exc.message}")
        except Exception as exc:
            st.error(f"An unexpected error occurred: {str(exc)}")

# =========================================
# RENDER VERIFIED REPOSITORY DATA
# =========================================

repo_data = st.session_state.get("repository_data")
summary_data = st.session_state.get("repository_summary")
kpis_data = st.session_state.get("repository_kpis")
analysis_run = st.session_state.get("analysis_run")

if repo_data and summary_data:
    st.divider()
    st.subheader("Repository Information & Health")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("⭐ Stars", repo_data.get("stars_count", 0))
    with c2:
        st.metric("🍴 Forks", repo_data.get("forks_count", 0))
    with c3:
        st.metric("🐛 Open Issues", repo_data.get("open_issues_count", 0))
    with c4:
        health_score = summary_data.get("health_score", 0.0)
        st.metric("🛡️ Health Score", f"{health_score}/100")

    st.subheader("Description")
    st.write(repo_data.get("description") or "No description provided.")

    st.divider()
    st.subheader("Ingestion & Analysis Status")
    if analysis_run:
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.metric("Pull Requests", analysis_run.get("total_prs_ingested", 0))
        with r2:
            st.metric("Commits", analysis_run.get("total_commits_ingested", 0))
        with r3:
            st.metric("Issues", analysis_run.get("total_issues_ingested", 0))
        with r4:
            st.metric("Contributors", analysis_run.get("total_contributors_ingested", 0))
elif not st.session_state.get("analysis_started"):
    st.info("💡 Enter repository owner and name above to start analysis.")