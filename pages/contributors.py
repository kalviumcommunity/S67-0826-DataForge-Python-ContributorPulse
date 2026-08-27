import streamlit as st
import pandas as pd

from github_api import get_contributor_commits


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

commits_data = st.session_state.get(
    "commits_data"
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


contributor_df = contributor_df.sort_values(
    by="Contributions",
    ascending=False
).reset_index(drop=True)


# =========================================
# CONTRIBUTOR FILTERS
# =========================================

st.subheader("🔎 Filter Contributors")

col1, col2 = st.columns(2)

with col1:

    search_username = st.text_input(
        "Search by username",
        placeholder="Enter contributor username..."
    )

with col2:

    min_contributions = st.number_input(
        "Minimum contributions",
        min_value=0,
        value=0,
        step=1
    )


filtered_df = contributor_df.copy()


if search_username:

    filtered_df = filtered_df[
        filtered_df["Username"].str.contains(
            search_username,
            case=False,
            na=False
        )
    ]


filtered_df = filtered_df[
    filtered_df["Contributions"]
    >= min_contributions
]


st.write(
    f"Showing **{len(filtered_df)}** contributors."
)

st.dataframe(
    filtered_df,
    width="stretch",
    hide_index=True
)


# =========================================
# CONTRIBUTOR OVERVIEW
# =========================================

st.divider()

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

top_contributor = contributor_df.iloc[0]["Username"]


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
        top_contributor
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
# PULL REQUEST ANALYSIS
# =========================================

st.divider()

st.subheader("🔀 Pull Request Participation")


pr_counts = {}


if pull_requests:

    for pr in pull_requests:

        user_data = pr.get("user") or {}

        username = user_data.get(
            "login"
        )

        if username:

            pr_counts[username] = (
                pr_counts.get(username, 0) + 1
            )


# =========================================
# COMMIT ANALYSIS
# =========================================

commit_counts = {}


if commits_data:

    for commit in commits_data:

        author_data = commit.get(
            "author"
        ) or {}

        username = author_data.get(
            "login"
        )

        if username:

            commit_counts[username] = (
                commit_counts.get(username, 0) + 1
            )


# =========================================
# CONTRIBUTOR ACTIVITY TABLE
# =========================================

activity_rows = []


all_usernames = set(
    pr_counts.keys()
).union(
    commit_counts.keys()
)


for username in all_usernames:

    pr_count = pr_counts.get(
        username,
        0
    )

    commit_count = commit_counts.get(
        username,
        0
    )

    total_activity = (
        pr_count +
        commit_count
    )

    if total_activity == 1:

        participation = "One-time contributor"

    else:

        participation = "Returning contributor"


    activity_rows.append(
        {
            "Username": username,
            "Pull Requests": pr_count,
            "Commits": commit_count,
            "Total Activity": total_activity,
            "Participation": participation
        }
    )


activity_df = pd.DataFrame(
    activity_rows
)


# =========================================
# RETENTION ANALYSIS
# =========================================

if not activity_df.empty:

    activity_df = activity_df.sort_values(
        by="Total Activity",
        ascending=False
    ).reset_index(drop=True)


    returning_count = len(
        activity_df[
            activity_df["Participation"]
            == "Returning contributor"
        ]
    )

    one_time_count = len(
        activity_df[
            activity_df["Participation"]
            == "One-time contributor"
        ]
    )

    total_active_contributors = len(
        activity_df
    )


    col1, col2, col3 = st.columns(3)


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


    with col3:

        st.metric(
            "👥 Active Contributors",
            total_active_contributors
        )


    if total_active_contributors > 0:

        return_rate = (
            returning_count /
            total_active_contributors
        ) * 100

        return_rate = round(
            return_rate,
            2
        )

    else:

        return_rate = 0


    st.write(
        f"### 🔄 Contributor Return Rate: "
        f"{return_rate}%"
    )

    st.progress(
        return_rate / 100
    )


    if return_rate >= 70:

        st.success(
            "A large proportion of active contributors "
            "show repeated participation. This is a "
            "positive signal for contributor retention."
        )

    elif return_rate >= 40:

        st.info(
            "Contributor retention appears moderate. "
            "Some contributors return while others "
            "participate only once."
        )

    else:

        st.warning(
            "A large proportion of contributors appear "
            "to participate only once. This may indicate "
            "an onboarding or contributor-retention "
            "opportunity."
        )


    st.subheader(
        "📋 Contributor Activity"
    )

    st.dataframe(
        activity_df,
        width="stretch",
        hide_index=True
    )


else:

    st.warning(
        "⚠️ No pull-request or commit activity "
        "was available for contributor analysis."
    )


# =========================================
# CONTRIBUTOR TIMELINE
# =========================================

st.divider()

st.subheader(
    "🕒 Contributor Timeline"
)

st.write(
    "This section shows when contributors first "
    "and most recently participated in the repository."
)


timeline_rows = []


# -----------------------------------------
# USE AVAILABLE COMMIT DATA
# -----------------------------------------

if commits_data:

    contributor_dates = {}


    for commit in commits_data:

        commit_data = commit.get(
            "commit"
        ) or {}

        author_data = commit_data.get(
            "author"
        ) or {}

        date = author_data.get(
            "date"
        )


        github_author = commit.get(
            "author"
        ) or {}

        username = github_author.get(
            "login"
        )


        if username and date:

            if username not in contributor_dates:

                contributor_dates[username] = []


            contributor_dates[username].append(
                date
            )


    # -----------------------------------------
    # CREATE TIMELINE
    # -----------------------------------------

    for username, dates in contributor_dates.items():

        dates = sorted(dates)

        first_contribution = dates[0]

        last_contribution = dates[-1]

        timeline_rows.append(
            {
                "Username": username,
                "First Contribution": first_contribution,
                "Last Contribution": last_contribution,
                "Total Commits": len(dates)
            }
        )


# =========================================
# TIMELINE DATAFRAME
# =========================================

timeline_df = pd.DataFrame(
    timeline_rows
)


if not timeline_df.empty:

    timeline_df[
        "First Contribution"
    ] = pd.to_datetime(
        timeline_df["First Contribution"]
    )

    timeline_df[
        "Last Contribution"
    ] = pd.to_datetime(
        timeline_df["Last Contribution"]
    )


    timeline_df["Days Active"] = (
        timeline_df["Last Contribution"]
        - timeline_df["First Contribution"]
    ).dt.days


    timeline_df = timeline_df.sort_values(
        by="Days Active",
        ascending=False
    ).reset_index(drop=True)


    st.dataframe(
        timeline_df,
        width="stretch",
        hide_index=True
    )


else:

    st.info(
        "No contributor timeline data is available "
        "from the collected commits."
    )


# =========================================
# PROJECT INSIGHT
# =========================================

st.divider()

st.subheader(
    "💡 Contributor Retention Insight"
)


if not activity_df.empty:

    st.write(
        f"The repository currently shows "
        f"**{returning_count} returning contributors** "
        f"and **{one_time_count} one-time contributors** "
        f"among contributors identified through "
        f"pull-request and commit activity."
    )


    if one_time_count > returning_count:

        st.warning(
            "There are more one-time contributors than "
            "returning contributors. This is an important "
            "area to investigate because first-time "
            "contributors may not be receiving an "
            "onboarding experience that encourages them "
            "to return."
        )

    else:

        st.success(
            "Returning contributors currently outnumber "
            "one-time contributors, which is a positive "
            "retention signal."
        )

else:

    st.info(
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