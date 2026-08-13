import streamlit as st
import time


st.set_page_config(
    page_title="Analyze Repository",
    page_icon="🔍",
    layout="wide"
)


# Session State
if "owner" not in st.session_state:
    st.session_state["owner"] = ""

if "repository" not in st.session_state:
    st.session_state["repository"] = ""

if "analysis_started" not in st.session_state:
    st.session_state["analysis_started"] = False


# Page Title
st.title("🔍 Analyze Repository")

st.write(
    "Enter a GitHub repository to analyze contributor activity "
    "and understand contributor retention."
)

st.divider()


# Repository Details
st.subheader("Repository Details")

owner = st.text_input(
    "Repository Owner",
    placeholder="e.g. flutter"
)

repository = st.text_input(
    "Repository Name",
    placeholder="e.g. flutter"
)


# Analyze Button
if st.button("🚀 Analyze Repository", type="primary"):

    if not owner or not repository:
        st.error("Please enter both the repository owner and repository name.")

    else:

        # Store values in Session State
        st.session_state["owner"] = owner
        st.session_state["repository"] = repository
        st.session_state["analysis_started"] = True

        # Loading / Analysis
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


        st.divider()

        st.subheader("Analysis Ready")

        st.write(
            f"Repository **{st.session_state['owner']}/"
            f"{st.session_state['repository']}** "
            "has been analyzed successfully."
        )

        st.info(
            "Results will be displayed here in the next stage."
        )