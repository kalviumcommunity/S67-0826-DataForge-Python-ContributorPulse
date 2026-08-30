"""ContributorPulse - Complete Streamlit Analytics Dashboard."""

from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_client import (
    APIClientError,
    APIConnectionError,
    APINotFoundError,
    APIRateLimitError,
    APIServerError,
    APITimeoutError,
    APIValidationError,
    BackendAPIClient,
)

# ==============================================================================
# Page Configuration
# ==============================================================================

st.set_page_config(
    page_title="ContributorPulse | Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

client = BackendAPIClient()

# ==============================================================================
# Session State Initialization
# ==============================================================================

if "owner" not in st.session_state:
    st.session_state["owner"] = ""
if "repository" not in st.session_state:
    st.session_state["repository"] = ""
if "analysis_run" not in st.session_state:
    st.session_state["analysis_run"] = None
if "selected_view" not in st.session_state:
    st.session_state["selected_view"] = "🏛️ Overview & Health"
if "time_period" not in st.session_state:
    st.session_state["time_period"] = "All Ingested History"

# ==============================================================================
# Helper Functions & Safe Formatters
# ==============================================================================

def render_health_badge(score: Optional[float]) -> str:
    """Return health classification and badge format."""
    if score is None:
        return "⚪ Unknown Health"
    if score >= 80:
        return f"🟢 Excellent ({score:.1f}/100)"
    elif score >= 60:
        return f"🟡 Good ({score:.1f}/100)"
    elif score >= 40:
        return f"🟠 Moderate ({score:.1f}/100)"
    else:
        return f"🔴 At Risk ({score:.1f}/100)"


def safe_metric(value: Any, unit: str = "", default: str = "N/A") -> str:
    """Format metric value safely without throwing on None or empty."""
    if value is None:
        return default
    if isinstance(value, float):
        return f"{value:.1f}{unit}"
    return f"{value}{unit}"


# ==============================================================================
# Sidebar - Repository Selection, Time-Period Window & View Navigation
# ==============================================================================

st.sidebar.title("📊 ContributorPulse")
st.sidebar.caption("Maintainer Intelligence & Contributor Retention")
st.sidebar.divider()

st.sidebar.subheader("Repository Target")
input_owner = st.sidebar.text_input(
    "Owner / Org",
    value=st.session_state["owner"],
    placeholder="e.g. kalviumcommunity",
    help="GitHub owner or organization login",
)
input_repo = st.sidebar.text_input(
    "Repository Name",
    value=st.session_state["repository"],
    placeholder="e.g. S67-0826-DataForge-Python-ContributorPulse",
    help="GitHub repository name",
)

col_trig, col_ref = st.sidebar.columns([3, 2])
trigger_btn = col_trig.button("🚀 Analyze", type="primary", use_container_width=True)
refresh_btn = col_ref.button("🔄 Refresh", use_container_width=True)

st.sidebar.divider()
st.sidebar.subheader("Time-Period Filter")
time_period_options = [
    "All Ingested History",
    "Last 30 Days",
    "Last 90 Days",
    "Last 180 Days",
    "Last 365 Days",
]
selected_period = st.sidebar.selectbox(
    "Active Cohort Window",
    time_period_options,
    index=time_period_options.index(st.session_state.get("time_period", "All Ingested History")),
    help="Filters retention analytics and time-series trends by cohort window.",
)
st.session_state["time_period"] = selected_period

if trigger_btn or (refresh_btn and input_owner and input_repo):
    if not input_owner.strip() or not input_repo.strip():
        st.sidebar.error("Please provide both repository owner and name.")
    else:
        st.session_state["owner"] = input_owner.strip()
        st.session_state["repository"] = input_repo.strip()
        try:
            with st.spinner("Connecting to backend and analyzing repository..."):
                run = client.trigger_analysis(st.session_state["owner"], st.session_state["repository"])
                st.session_state["analysis_run"] = run
            st.sidebar.success(f"Analysis Status: {run.get('status', 'COMPLETED')}")
        except APINotFoundError as exc:
            st.sidebar.error(f"❌ {exc.message}")
        except APIValidationError as exc:
            st.sidebar.error(f"⚠️ Validation Error: {exc.message}")
        except APITimeoutError as exc:
            st.sidebar.error(f"⏱️ Timeout: {exc.message}")
        except APIConnectionError as exc:
            st.sidebar.error(f"🔌 Connection Error: {exc.message}")
        except APIRateLimitError as exc:
            st.sidebar.error(f"⏳ Rate Limit: {exc.message}")
        except APIServerError as exc:
            st.sidebar.error(f"⚠️ Server Error: {exc.message}")
        except Exception as exc:
            st.sidebar.error(f"Unexpected error: {str(exc)}")

st.sidebar.divider()
st.sidebar.subheader("Dashboard Views")
views = [
    "🏛️ Overview & Health",
    "👥 Contributor Journey & Retention",
    "⏱️ Response & Review Experience",
    "🔀 Pull Request & Merge Analytics",
    "⚠️ Contributor Risk & Segmentation",
    "⚖️ Repository Comparison & Monitoring",
]
selected_view = st.sidebar.radio("Select View", views, index=views.index(st.session_state["selected_view"]))
st.session_state["selected_view"] = selected_view

owner = st.session_state["owner"]
repo = st.session_state["repository"]

# ==============================================================================
# Guard Check: Empty State when no repository is selected
# ==============================================================================

if not owner or not repo:
    st.title("📊 ContributorPulse Intelligence Dashboard")
    st.info("👈 Enter a GitHub repository owner and name in the sidebar, then click **🚀 Analyze** to begin.")
    
    st.divider()
    st.subheader("Platform Capabilities")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🏛️ Health & Retention")
        st.write("Understand 30d and 90d return velocity, PR merge rates, and holistic repository health.")
    with c2:
        st.markdown("### ⏱️ Latency & Velocity")
        st.write("Measure maintainer response speed, review turnaround times, and friction points.")
    with c3:
        st.markdown("### ⚠️ Churn Risk Detection")
        st.write("Identify at-risk first-time contributors with transparent, explainable penalty reasons.")
    st.stop()

# ==============================================================================
# Header & Context Banner
# ==============================================================================

st.title(f"{selected_view}")
st.caption(f"Repository: **{owner}/{repo}** | Time Period: **{selected_period}** | Maintainer Intelligence")
st.divider()

# ==============================================================================
# VIEW 1: Overview & Repository Health
# ==============================================================================

if selected_view == "🏛️ Overview & Health":
    try:
        with st.spinner("Fetching repository summary and KPI engine metrics..."):
            summary = client.get_repository_summary(owner, repo)
            kpis_res = client.get_repository_kpis(owner, repo)
            repo_meta = client.get_repository(owner, repo)

        if not summary or not kpis_res:
            st.warning("⚠️ No analytics summary found for this repository. Please run an analysis first.")
            st.stop()

        kpis = kpis_res.get("kpis", {})
        health_score = summary.get("health_score", 0.0)

        # Health Banner
        st.subheader("Repository Health & Vital Signs")
        col_h1, col_h2 = st.columns([3, 1])
        with col_h1:
            st.markdown(f"### Overall Repository Health: {render_health_badge(health_score)}")
            st.progress(min(max(health_score / 100.0, 0.0), 1.0))
        with col_h2:
            st.metric("Health Score", f"{health_score:.1f} / 100")

        st.divider()

        # KPI Cards Grid
        st.subheader("Core Key Performance Indicators (KPIs)")
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            ret30 = kpis.get("retention_rate_30d", {})
            st.metric("30-Day Retention", safe_metric(ret30.get("value"), "%"), help=ret30.get("description", ""))
            st.caption(f"Sample size: {ret30.get('sample_size', 0)} contributors")
        with k2:
            ret90 = kpis.get("retention_rate_90d", {})
            st.metric("90-Day Retention", safe_metric(ret90.get("value"), "%"), help=ret90.get("description", ""))
            st.caption(f"Sample size: {ret90.get('sample_size', 0)} contributors")
        with k3:
            merge_rate = kpis.get("merge_rate", {})
            st.metric("PR Merge Rate", safe_metric(merge_rate.get("value"), "%"), help=merge_rate.get("description", ""))
            st.caption(f"Sample size: {merge_rate.get('sample_size', 0)} PRs")
        with k4:
            growth = kpis.get("contributor_growth_rate", {})
            st.metric("Contributor Growth", safe_metric(growth.get("value"), "%"), help=growth.get("description", ""))
            st.caption(f"Sample size: {growth.get('sample_size', 0)} contributors")

        k5, k6, k7, k8 = st.columns(4)
        with k5:
            resp_time = kpis.get("average_first_response_hours", {})
            st.metric("Avg First Response", safe_metric(resp_time.get("value"), " hrs"), help=resp_time.get("description", ""))
            st.caption(f"Sample size: {resp_time.get('sample_size', 0)} PRs")
        with k6:
            rev_time = kpis.get("average_review_hours", {})
            st.metric("Avg Review Time", safe_metric(rev_time.get("value"), " hrs"), help=rev_time.get("description", ""))
            st.caption(f"Sample size: {rev_time.get('sample_size', 0)} PRs")
        with k7:
            mrg_time = kpis.get("average_merge_hours", {})
            st.metric("Avg Time to Merge", safe_metric(mrg_time.get("value"), " hrs"), help=mrg_time.get("description", ""))
            st.caption(f"Sample size: {mrg_time.get('sample_size', 0)} PRs")
        with k8:
            high_risk = kpis.get("high_risk_contributors_count", {})
            st.metric("High-Risk Contributors", safe_metric(high_risk.get("value"), ""), help=high_risk.get("description", ""))
            st.caption("Active contributors flagged with churn risk")

        st.divider()

        # Repository Profile Summary
        if repo_meta:
            st.subheader("Repository Profile & Volume")
            p1, p2, p3, p4 = st.columns(4)
            with p1:
                st.metric("⭐ Stars", repo_meta.get("stars_count", 0))
            with p2:
                st.metric("🍴 Forks", repo_meta.get("forks_count", 0))
            with p3:
                st.metric("🐛 Open Issues", repo_meta.get("open_issues_count", 0))
            with p4:
                st.metric("👥 Total Contributors", summary.get("total_contributors", 0))

    except APIClientError as exc:
        st.error(f"⚠️ Error loading overview: {exc.message}")

# ==============================================================================
# VIEW 2: Contributor Journey & Retention
# ==============================================================================

elif selected_view == "👥 Contributor Journey & Retention":
    try:
        with st.spinner("Fetching retention funnel data..."):
            funnel_data = client.get_retention_funnel(owner, repo)

        if not funnel_data or not funnel_data.get("stages"):
            st.info("ℹ️ No retention funnel records available for this repository yet.")
        else:
            st.subheader("Contributor Onboarding & Retention Funnel")
            st.write(
                "Track how first-time contributors progress from their initial contribution "
                "through PR merge and 30-day, 60-day, and 90-day repeat contributions."
            )

            stages = funnel_data.get("stages", [])
            df_funnel = pd.DataFrame(stages)

            fig = go.Figure(
                go.Funnel(
                    y=df_funnel["stage"],
                    x=df_funnel["contributor_count"],
                    textinfo="value+percent initial",
                    marker={"color": ["#3366CC", "#109618", "#FF9900", "#DC3912", "#990099"]},
                )
            )
            fig.update_layout(
                title_text="First-Time Contributor Progression & Drop-off",
                template="plotly_white",
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Funnel Conversion Rates")
            st.dataframe(
                df_funnel.rename(
                    columns={
                        "stage": "Funnel Stage",
                        "contributor_count": "Contributors",
                        "conversion_rate": "Conversion Rate (%)",
                        "drop_off_count": "Drop-off Count",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    except APIClientError as exc:
        st.error(f"⚠️ Error loading funnel: {exc.message}")

# ==============================================================================
# VIEW 3: Response and Review Experience
# ==============================================================================

elif selected_view == "⏱️ Response & Review Experience":
    try:
        with st.spinner("Fetching response distribution and timeline..."):
            dist_data = client.get_response_distribution(owner, repo)
            timeline_data = client.get_review_timeline(owner, repo)

        col_d1, col_d2 = st.columns(2)

        with col_d1:
            st.subheader("Maintainer Response Time Distribution")
            st.write("Time taken for maintainers to provide the first comment or review on PRs.")

            if dist_data and dist_data.get("buckets"):
                df_dist = pd.DataFrame(dist_data["buckets"])
                fig_dist = px.bar(
                    df_dist,
                    x="bracket",
                    y="count",
                    text="percentage",
                    labels={"bracket": "Response Time Bracket", "count": "PR Count", "percentage": "%"},
                    color="bracket",
                    color_discrete_sequence=px.colors.qualitative.Prism,
                )
                fig_dist.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig_dist.update_layout(template="plotly_white", showlegend=False)
                st.plotly_chart(fig_dist, use_container_width=True)
            else:
                st.info("ℹ️ No response distribution data available.")

        with col_d2:
            st.subheader("Monthly Review Speed & Velocity Timeline")
            st.write("Historical trends in average review time and maintainer response velocity.")

            if timeline_data and timeline_data.get("timeline"):
                df_time = pd.DataFrame(timeline_data["timeline"])
                fig_time = px.line(
                    df_time,
                    x="period",
                    y=["average_review_hours", "average_response_hours"],
                    markers=True,
                    labels={"period": "Month", "value": "Hours", "variable": "Metric"},
                )
                fig_time.update_layout(template="plotly_white", legend_title_text="Metric")
                st.plotly_chart(fig_time, use_container_width=True)
            else:
                st.info("ℹ️ No review timeline data available.")

    except APIClientError as exc:
        st.error(f"⚠️ Error loading response metrics: {exc.message}")

# ==============================================================================
# VIEW 4: Pull-Request and Merge Analytics
# ==============================================================================

elif selected_view == "🔀 Pull Request & Merge Analytics":
    try:
        with st.spinner("Fetching pull request merge statistics..."):
            merge_data = client.get_merge_stats(owner, repo)

        if not merge_data or merge_data.get("total_prs", 0) == 0:
            st.info("ℹ️ No pull request activity records found for this repository.")
        else:
            st.subheader("Pull Request Resolution & Merge Outcomes")
            st.write("Distribution of merged, closed unmerged, and open pull requests.")

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total PRs", merge_data.get("total_prs", 0))
            with m2:
                st.metric("Merge Rate", f"{merge_data.get('merge_rate', 0.0):.1f}%")
            with m3:
                st.metric("Merged PRs", merge_data.get("merged_prs", 0))
            with m4:
                st.metric("Closed Unmerged", merge_data.get("closed_unmerged_prs", 0))

            labels = ["Merged", "Closed (Unmerged)", "Open"]
            values = [
                merge_data.get("merged_prs", 0),
                merge_data.get("closed_unmerged_prs", 0),
                merge_data.get("open_prs", 0),
            ]

            fig_pie = go.Figure(
                data=[
                    go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.45,
                        marker=dict(colors=["#2CA02C", "#D62728", "#1F77B4"]),
                    )
                ]
            )
            fig_pie.update_layout(
                title_text="PR Outcomes Distribution",
                template="plotly_white",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    except APIClientError as exc:
        st.error(f"⚠️ Error loading merge stats: {exc.message}")

# ==============================================================================
# VIEW 5: Contributor Risk and Segmentation
# ==============================================================================

elif selected_view == "⚠️ Contributor Risk & Segmentation":
    try:
        with st.spinner("Fetching contributor intelligence and churn risk segmentation..."):
            risk_data = client.get_high_risk_contributors(owner, repo)

        st.subheader("High Churn Risk Contributor Alerts")
        st.write(
            "First-time contributors identified at elevated risk of churn (Risk Score >= 0.60), "
            "with explainable penalty reasons."
        )

        if not risk_data or not risk_data.get("items"):
            st.success("🎉 No high-risk contributors identified. Contributor retention is healthy!")
        else:
            items = risk_data.get("items", [])
            df_risk = pd.DataFrame(items)

            st.metric("High-Risk Contributors Flagged", len(items))

            st.dataframe(
                df_risk[
                    [
                        "login",
                        "churn_risk_score",
                        "churn_risk_level",
                        "experience_level",
                        "risk_reason",
                        "first_response_hours",
                        "first_review_hours",
                    ]
                ].rename(
                    columns={
                        "login": "Contributor",
                        "churn_risk_score": "Risk Score (0-1)",
                        "churn_risk_level": "Risk Tier",
                        "experience_level": "Experience",
                        "risk_reason": "Identified Risk Reasons",
                        "first_response_hours": "First Response (hrs)",
                        "first_review_hours": "First Review (hrs)",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    except APIClientError as exc:
        st.error(f"⚠️ Error loading risk segmentation: {exc.message}")

# ==============================================================================
# VIEW 6: Repository Comparison & Monitoring
# ==============================================================================

elif selected_view == "⚖️ Repository Comparison & Monitoring":
    st.subheader("Side-by-Side Repository Comparison")
    st.write("Compare contributor health, retention, and merge velocity across multiple repositories.")

    default_compare = f"{owner}/{repo}" if (owner and repo) else ""
    compare_input = st.text_input(
        "Repositories to Compare (comma-separated owner/repo pairs)",
        value=default_compare,
        placeholder="e.g. kalviumcommunity/repo1, facebook/react",
    )

    if st.button("⚖️ Compare Repositories", type="primary"):
        repo_list = [r.strip() for r in compare_input.split(",") if r.strip()]
        if not repo_list:
            st.warning("⚠️ Please enter at least one valid repository (owner/name) to compare.")
        else:
            try:
                with st.spinner("Fetching comparison metrics..."):
                    comp_data = client.compare_repositories(repo_list)

                if not comp_data or not comp_data.get("repositories"):
                    st.info("ℹ️ No comparative data found for the selected repositories.")
                else:
                    repos = comp_data.get("repositories", [])
                    # Normalize missing or None fields safely
                    for r in repos:
                        r["health_score"] = r.get("health_score") or 0.0
                        r["retention_rate_30d"] = r.get("retention_rate_30d") or 0.0
                        r["merge_rate"] = r.get("merge_rate") or 0.0
                        r["total_contributors"] = r.get("total_contributors") or 0
                        r["total_prs"] = r.get("total_prs") or 0

                    df_comp = pd.DataFrame(repos)

                    # KPI Comparison Table
                    st.subheader("Comparative Health & Retention Summary")
                    st.dataframe(
                        df_comp[
                            [
                                "full_name",
                                "health_score",
                                "retention_rate_30d",
                                "merge_rate",
                                "total_contributors",
                                "total_prs",
                            ]
                        ].rename(
                            columns={
                                "full_name": "Repository",
                                "health_score": "Health Score",
                                "retention_rate_30d": "30d Retention (%)",
                                "merge_rate": "Merge Rate (%)",
                                "total_contributors": "Contributors",
                                "total_prs": "Total PRs",
                            }
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Comparative Bar Chart (handles 1, 2, or N repositories gracefully)
                    fig_comp = px.bar(
                        df_comp,
                        x="full_name",
                        y=["health_score", "retention_rate_30d", "merge_rate"],
                        barmode="group",
                        labels={"full_name": "Repository", "value": "Score / Percentage", "variable": "Metric"},
                        title="Repository Health and Retention Benchmarks",
                    )
                    fig_comp.update_layout(template="plotly_white")
                    st.plotly_chart(fig_comp, use_container_width=True)

            except APIClientError as exc:
                st.error(f"⚠️ Error comparing repositories: {exc.message}")