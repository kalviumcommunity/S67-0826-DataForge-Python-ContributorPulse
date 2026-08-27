import streamlit as st

from github_api import (
    get_repository,
    get_contributors,
    get_commit_activity,
    get_pull_requests
)


# -----------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------

st.set_page_config(
    page_title="Analyze Repository",
    page_icon="🔍",
    layout="wide"
)


# -----------------------------------------
# SESSION STATE
# -----------------------------------------

if "owner" not in st.session_state:
    st.session_state["owner"] = ""

if "repository" not in st.session_state:
    st.session_state["repository"] = ""

if "analysis_started" not in st.session_state:
    st.session_state["analysis_started"] = False

if "repository_data" not in st.session_state:
    st.session_state["repository_data"] = None

if "contributors_data" not in st.session_state:
    st.session_state["contributors_data"] = None

if "commit_activity" not in st.session_state:
    st.session_state["commit_activity"] = None

if "pull_requests" not in st.session_state:
    st.session_state["pull_requests"] = None


# -----------------------------------------
# PAGE TITLE
# -----------------------------------------

st.title("🔍 Analyze Repository")

st.write(
    "Enter a GitHub repository to analyze contributor activity "
    "and understand contributor retention."
)

st.divider()


# -----------------------------------------
# REPOSITORY DETAILS
# -----------------------------------------

st.subheader("Repository Details")

owner = st.text_input(
    "Repository Owner",
    value=st.session_state["owner"],
    placeholder="e.g. flutter"
)

repository = st.text_input(
    "Repository Name",
    value=st.session_state["repository"],
    placeholder="e.g. flutter"
)


# -----------------------------------------
# ANALYZE BUTTON
# -----------------------------------------

if st.button(
    "🚀 Analyze Repository",
    type="primary"
):

    owner = owner.strip()
    repository = repository.strip()

    # -----------------------------------------
    # VALIDATION
    # -----------------------------------------

    if not owner or not repository:

        st.error(
            "Please enter both the repository owner "
            "and repository name."
        )

    else:

        # -----------------------------------------
        # SAVE REPOSITORY DETAILS
        # -----------------------------------------

        st.session_state["owner"] = owner
        st.session_state["repository"] = repository

        # -----------------------------------------
        # GET REPOSITORY INFORMATION
        # -----------------------------------------

        with st.spinner("Checking GitHub repository..."):

            repository_data = get_repository(
                owner,
                repository
            )

        # -----------------------------------------
        # REPOSITORY NOT FOUND
        # -----------------------------------------

        if repository_data is None:

            st.session_state["analysis_started"] = False
            st.session_state["repository_data"] = None
            st.session_state["contributors_data"] = None
            st.session_state["commit_activity"] = None
            st.session_state["pull_requests"] = None

            st.error(
                "❌ Repository not found. "
                "Please check the owner and repository name."
            )

        # -----------------------------------------
        # REPOSITORY FOUND
        # -----------------------------------------

        else:

            st.session_state["analysis_started"] = True
            st.session_state["repository_data"] = repository_data

            st.success("✓ Repository verified")

            # -----------------------------------------
            # GET CONTRIBUTORS
            # -----------------------------------------

            with st.spinner("Collecting contributors..."):

                contributors_data = get_contributors(
                    owner,
                    repository
                )

            st.session_state["contributors_data"] = contributors_data

            if contributors_data is not None:

                st.success("✓ Contributors collected")

            else:

                st.warning(
                    "⚠️ Repository found, but contributors "
                    "could not be collected."
                )

            # -----------------------------------------
            # GET COMMIT ACTIVITY
            # -----------------------------------------

            with st.spinner("Collecting commit activity..."):

                commit_activity = get_commit_activity(
                    owner,
                    repository
                )

            st.session_state["commit_activity"] = commit_activity

            if commit_activity is not None:

                st.success("✓ Commit activity collected")

            else:

                st.warning(
                    "⚠️ Commit activity could not be collected."
                )

            # -----------------------------------------
            # GET PULL REQUESTS
            # -----------------------------------------

            with st.spinner("Collecting pull requests..."):

                pull_requests = get_pull_requests(
                    owner,
                    repository
                )

            st.session_state["pull_requests"] = pull_requests

            if pull_requests is not None:

                st.success("✓ Pull requests collected")

            else:

                st.warning(
                    "⚠️ Pull request data could not be collected."
                )


            # =========================================
            # REPOSITORY INFORMATION
            # =========================================

            st.divider()

            st.subheader("Repository Information")

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "⭐ Stars",
                    repository_data.get(
                        "stargazers_count",
                        0
                    )
                )

            with col2:

                st.metric(
                    "🍴 Forks",
                    repository_data.get(
                        "forks_count",
                        0
                    )
                )

            with col3:

                st.metric(
                    "🐛 Open Issues",
                    repository_data.get(
                        "open_issues_count",
                        0
                    )
                )


            # =========================================
            # DESCRIPTION
            # =========================================

            st.subheader("Description")

            description = repository_data.get("description")

            if description:

                st.write(description)

            else:

                st.write(
                    "No description available."
                )


            # =========================================
            # REPOSITORY DETAILS
            # =========================================

            st.subheader("Repository Details")

            col1, col2 = st.columns(2)

            with col1:

                st.write(
                    "**Repository:** "
                    f"{repository_data.get('full_name', 'N/A')}"
                )

                st.write(
                    "**Language:** "
                    f"{repository_data.get('language', 'N/A')}"
                )

            with col2:

                st.write(
                    "**Default Branch:** "
                    f"{repository_data.get('default_branch', 'N/A')}"
                )

                visibility = (
                    "Private"
                    if repository_data.get("private")
                    else "Public"
                )

                st.write(
                    f"**Visibility:** {visibility}"
                )


            # =========================================
            # CONTRIBUTOR SUMMARY
            # =========================================

            st.divider()

            st.subheader("👥 Contributors")

            if contributors_data:

                st.write(
                    f"Contributor data collected successfully."
                )

                st.metric(
                    "Total Contributors",
                    len(contributors_data)
                )

                st.info(
                    "Open the Contributors page to view "
                    "detailed contributor activity and retention analysis."
                )

            else:

                st.warning(
                    "No contributor data available."
                )


            # =========================================
            # COMMIT ACTIVITY
            # =========================================

            if commit_activity:

                st.divider()

                st.subheader("📈 Commit Activity")

                st.write(
                    "Recent commit activity collected "
                    "from the repository."
                )

                st.write(
                    commit_activity[:5]
                )

            else:

                st.warning(
                    "No commit activity data available."
                )


            # =========================================
            # PULL REQUEST ACTIVITY
            # =========================================

            if pull_requests:

                st.divider()

                st.subheader("🔀 Pull Request Activity")

                st.write(
                    "Pull requests collected from the repository."
                )

                # -----------------------------------------
                # PR SUMMARY
                # -----------------------------------------

                total_prs = len(pull_requests)

                open_prs = sum(
                    1
                    for pr in pull_requests
                    if pr.get("state") == "open"
                )

                closed_prs = sum(
                    1
                    for pr in pull_requests
                    if pr.get("state") == "closed"
                )

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "Total Pull Requests",
                        total_prs
                    )

                with col2:

                    st.metric(
                        "Open PRs",
                        open_prs
                    )

                with col3:

                    st.metric(
                        "Closed PRs",
                        closed_prs
                    )


                # -----------------------------------------
                # PR TABLE
                # -----------------------------------------

                pr_rows = []

                for pr in pull_requests:

                    user_data = pr.get("user") or {}

                    pr_rows.append(
                        {
                            "Title": pr.get(
                                "title",
                                "Unknown"
                            ),
                            "Author": user_data.get(
                                "login",
                                "Unknown"
                            ),
                            "State": pr.get(
                                "state",
                                "Unknown"
                            ),
                            "Created": pr.get(
                                "created_at",
                                "Unknown"
                            ),
                            "Merged": (
                                "Yes"
                                if pr.get("merged_at")
                                else "No"
                            )
                        }
                    )

                st.dataframe(
                    pr_rows,
                    width="stretch",
                    hide_index=True
                )

            else:

                st.warning(
                    "No pull request data available."
                )


            # =========================================
            # ANALYSIS COMPLETE
            # =========================================

            st.divider()

            st.subheader("✅ Analysis Ready")

            st.write(
                f"Repository **{owner}/{repository}** "
                "has been analyzed successfully."
            )

            st.info(
                "Your contributor retention dashboard is ready."
            )


# =========================================
# NAVIGATION
# =========================================

if st.session_state["analysis_started"]:

    st.divider()

    st.subheader("📊 Continue Analysis")

    st.write(
        "Choose what you want to analyze next."
    )

    col1, col2 = st.columns(2)

    with col1:

        st.page_link(
            "pages/contributors.py",
            label="👥 Analyze Contributors"
        )

    with col2:

        st.page_link(
            "pages/dashboard.py",
            label="📊 View Contributor Dashboard"
        )