import streamlit as st
import pandas as pd 

from github_api import get_repository, get_contributors


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

if st.button("🚀 Analyze Repository", type="primary"):

    # Check input
    if not owner or not repository:

        st.error(
            "Please enter both the repository owner "
            "and repository name."
        )

    else:

        # Store repository details
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

            st.divider()

            # -----------------------------------------
            # REPOSITORY INFORMATION
            # -----------------------------------------

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

            # -----------------------------------------
            # DESCRIPTION
            # -----------------------------------------

            st.subheader("Description")

            description = repository_data.get(
                "description"
            )

            if description:

                st.write(description)

            else:

                st.write(
                    "No description available."
                )

            # -----------------------------------------
            # REPOSITORY DETAILS
            # -----------------------------------------

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

            # -----------------------------------------
            # CONTRIBUTOR SUMMARY
            # -----------------------------------------

if contributors_data:

    st.divider()

    st.subheader("👥 Contributors")

    st.write(
        "Contributors who have participated in this repository."
    )

    # Create contributor table
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

    # Sort by contributions
    contributor_df = contributor_df.sort_values(
        by="Contributions",
        ascending=False
    )

    # Display table
    st.dataframe(
        contributor_df,
        use_container_width=True,
        hide_index=True
    )

    st.metric(
        "Total Contributors",
        len(contributor_df)
    )

else:

    st.warning(
        "No contributor data available."
    )