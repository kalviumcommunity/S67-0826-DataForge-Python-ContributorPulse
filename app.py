import streamlit as st


st.set_page_config(
    page_title="Analyse Retain",
    page_icon="🔍",
    layout="wide"
)


st.title("Analyse Retain")

st.subheader("Maintainer Intelligence Platform")

st.write(
    "Understand why first-time contributors return or drop off."
)

st.divider()

st.header("Welcome 👋")

st.write(
    "Analyse a GitHub repository to understand contributor "
    "activity, retention, and onboarding experiences."
)

st.info(
    "Use the Repository page from the sidebar to begin your analysis."
)