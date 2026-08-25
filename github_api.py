import os
import requests

from dotenv import load_dotenv


# -----------------------------------------
# LOAD ENVIRONMENT VARIABLES
# -----------------------------------------

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# -----------------------------------------
# GITHUB API CONFIGURATION
# -----------------------------------------

BASE_URL = "https://api.github.com"


def get_headers():
    """
    Return headers used for GitHub API requests.
    """

    headers = {
        "Accept": "application/vnd.github+json"
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return headers


# -----------------------------------------
# GET REPOSITORY
# -----------------------------------------

def get_repository(owner, repository):
    """
    Fetch repository information from GitHub.
    """

    url = f"{BASE_URL}/repos/{owner}/{repository}"

    response = requests.get(
        url,
        headers=get_headers()
    )

    if response.status_code == 200:
        return response.json()

    print(
        "GitHub API Error:",
        response.status_code,
        response.text
    )

    return None


# -----------------------------------------
# GET CONTRIBUTORS
# -----------------------------------------

def get_contributors(owner, repository):
    """
    Fetch contributors from a GitHub repository.
    """

    url = (
        f"{BASE_URL}/repos/"
        f"{owner}/{repository}/contributors"
    )

    response = requests.get(
        url,
        headers=get_headers(),
        params={
            "per_page": 100
        }
    )

    if response.status_code == 200:
        return response.json()

    print(
        "GitHub API Error:",
        response.status_code,
        response.text
    )

    return None