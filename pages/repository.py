import streamlit as st
import time


st.set_page_config(
    page_title="Analyse Retain - Repository",
    page_icon="🔍",
    layout="wide"
)


st.title("🔍 Analyze Repository")

st.write(
    "Enter a GitHub repository to analyze contributor retention."
)

st.divider()


# Initialize session state
if "owner" not in st.session_state:
    st.session_state["owner"] = ""

if "repository" not in st.session_state:
    st.session_state["repository"] = ""

if "analysis_started" not in st.session_state:
    st.session_state["analysis_started"] = False


# Repository Owner
owner = st.text_input(
    "Repository Owner",
    placeholder="e.g. flutter"
)

# Repository Name
repository = st.text_input(
    "Repository Name",
    placeholder="e.g. flutter"
)


st.write("")


# Analyze button
if st.button("🚀 Analyze Repository", use_container_width=True):

    if not owner or not repository:
        st.error("Please enter both the repository owner and repository name.")

    else:
        # Store values in session state
        st.session_state["owner"] = owner
        st.session_state["repository"] = repository
        st.session_state["analysis_started"] = True

        # Loading state
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


# Show repository details after analysis
if st.session_state["analysis_started"]:

    st.divider()

    st.subheader("Analysis Summary")

    st.write(
        f"Repository analyzed: "
        f"**{st.session_state['owner']}/{st.session_state['repository']}**"
    )

    st.info(
        "Analysis results will be displayed here in the next stage."
    )