import streamlit as st
import pandas as pd


# =========================================
# PAGE CONFIGURATION
# =========================================

st.set_page_config(
    page_title="Contributors",
    page_icon="👥",
    layout="wide"
)


# =========================================
# CHECK ANALYSIS STATUS
# =========================================

if not st.session_state.get("analysis_started", False):

    st.warning(
        "⚠️ Please analyze a repository first."
    )

    st.page_link(
        "pages/repository.py",
        label="🔍 Go to Repository Analysis"
    )

    st.stop()


# =========================================
# GET DATA FROM SESSION STATE
# =========================================

owner = st.session_state.get(
    "owner",
    ""
)

repository = st.session_state.get(
    "repository",
    ""
)

contributors_data = st.session_state.get(
    "contributors_data"
)

pull_requests = st.session_state.get(
    "pull_requests"
)


# =========================================
# PAGE TITLE
# =========================================

st.title("👥 Contributor Analysis")

st.write(
    f"Contributor activity analysis for "
    f"**{owner}/{repository}**."
)

st.divider()


# =========================================
# CHECK CONTRIBUTOR DATA
# =========================================

if not contributors_data:

    st.error(
        "❌ No contributor data is available."
    )

    st.page_link(
        "pages/repository.py",
        label="🔍 Analyze Repository Again"
    )

    st.stop()


# =========================================
# CREATE CONTRIBUTOR DATAFRAME
# =========================================

contributor_rows = []

for contributor in contributors_data:

    contributor_rows.append(
        {
            "Username": contributor.get(
                "login",
                "Unknown"
            ),
            "Contributions": contributor.get(
                "contributions",
                0
            )
        }
    )


contributor_df = pd.DataFrame(
    contributor_rows
)


# Sort contributors by contributions

contributor_df = contributor_df.sort_values(
    by="Contributions",
    ascending=False
).reset_index(drop=True)


# =========================================
# CONTRIBUTOR OVERVIEW
# =========================================

st.subheader("📊 Contributor Overview")


total_contributors = len(
    contributor_df
)

total_contributions = int(
    contributor_df["Contributions"].sum()
)

average_contributions = round(
    contributor_df["Contributions"].mean(),
    2
)

top_contributor = contributor_df.iloc[0]


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Total Contributors",
        total_contributors
    )


with col2:

    st.metric(
        "Total Contributions",
        total_contributions
    )


with col3:

    st.metric(
        "Average Contributions",
        average_contributions
    )


with col4:

    st.metric(
        "Top Contributor",
        top_contributor["Username"]
    )


# =========================================
# TOP CONTRIBUTORS
# =========================================

st.divider()

st.subheader("🏆 Top Contributors")

st.write(
    "Contributors ranked by the number of "
    "recorded contributions."
)


# Show top 10 contributors

top_contributors = contributor_df.head(10)


st.dataframe(
    top_contributors,
    width="stretch",
    hide_index=True
)


# =========================================
# CONTRIBUTION CHART
# =========================================

st.subheader("📈 Contribution Distribution")

chart_data = top_contributors.set_index(
    "Username"
)["Contributions"]

st.bar_chart(
    chart_data
)


# =========================================
# RETURNING CONTRIBUTOR ANALYSIS
# =========================================

st.divider()

st.subheader("🔄 Contributor Return Analysis")

st.write(
    "This section looks at pull-request participation "
    "to identify contributors who appear to have "
    "returned to contribute more than once."
)


# =========================================
# CHECK PULL REQUEST DATA
# =========================================

if pull_requests:

    # -----------------------------------------
    # COUNT PRs PER CONTRIBUTOR
    # -----------------------------------------

    pr_counts = {}

    for pr in pull_requests:

        user_data = pr.get("user") or {}

        username = user_data.get(
            "login"
        )

        if username:

            pr_counts[username] = (
                pr_counts.get(username, 0) + 1
            )


    # -----------------------------------------
    # CREATE RETURN ANALYSIS
    # -----------------------------------------

    return_rows = []

    for username, count in pr_counts.items():

        if count == 1:

            status = "One-time contributor"

        else:

            status = "Returning contributor"

        return_rows.append(
            {
                "Username": username,
                "Pull Requests": count,
                "Participation": status
            }
        )


    return_df = pd.DataFrame(
        return_rows
    )


    if not return_df.empty:

        return_df = return_df.sort_values(
            by="Pull Requests",
            ascending=False
        ).reset_index(drop=True)


        # -----------------------------------------
        # RETURN METRICS
        # -----------------------------------------

        returning_count = len(
            return_df[
                return_df["Participation"]
                == "Returning contributor"
            ]
        )

        one_time_count = len(
            return_df[
                return_df["Participation"]
                == "One-time contributor"
            ]
        )


        col1, col2 = st.columns(2)


        with col1:

            st.metric(
                "🔄 Returning Contributors",
                returning_count
            )


        with col2:

            st.metric(
                "🆕 One-time Contributors",
                one_time_count
            )


        # -----------------------------------------
        # RETURN RATE
        # -----------------------------------------

        total_pr_contributors = (
            returning_count +
            one_time_count
        )


        if total_pr_contributors > 0:

            return_rate = (
                returning_count /
                total_pr_contributors
            ) * 100

            return_rate = round(
                return_rate,
                2
            )

            st.write(
                f"### Return Rate: {return_rate}%"
            )

            st.progress(
                return_rate / 100
            )


        # -----------------------------------------
        # INTERPRETATION
        # -----------------------------------------

        if returning_count > one_time_count:

            st.success(
                "Most PR contributors appear to have "
                "participated more than once."
            )

        elif one_time_count > returning_count:

            st.warning(
                "More contributors appear to have made "
                "only one PR. This may indicate an "
                "onboarding or retention opportunity."
            )

        else:

            st.info(
                "One-time and returning contributors "
                "are currently balanced."
            )


        # -----------------------------------------
        # CONTRIBUTOR RETURN TABLE
        # -----------------------------------------

        st.subheader(
            "Contributor Participation"
        )

        st.dataframe(
            return_df,
            width="stretch",
            hide_index=True
        )


    else:

        st.info(
            "No contributor pull-request activity "
            "was available for return analysis."
        )


else:

    st.warning(
        "⚠️ Pull request data is not available, "
        "so contributor return analysis cannot "
        "be calculated."
    )


# =========================================
# PROJECT INSIGHT
# =========================================

st.divider()

st.subheader("💡 Contributor Retention Insight")

if pull_requests and not return_df.empty:

    if returning_count > one_time_count:

        st.write(
            "The available pull-request data suggests "
            "that a larger proportion of contributors "
            "returned to participate again. This is a "
            "positive signal for contributor retention."
        )

    else:

        st.write(
            "The available pull-request data shows a "
            "large proportion of one-time contributors. "
            "This is worth investigating because it may "
            "indicate that some first-time contributors "
            "do not return."
        )

else:

    st.write(
        "More contributor activity data is needed "
        "to determine meaningful retention patterns."
    )


# =========================================
# NAVIGATION
# =========================================

st.divider()

st.subheader("🔗 Continue")

col1, col2 = st.columns(2)


with col1:

    st.page_link(
        "pages/repository.py",
        label="🔍 Repository Analysis"
    )


with col2:

    st.page_link(
        "pages/dashboard.py",
        label="📊 Contributor Dashboard"
    )