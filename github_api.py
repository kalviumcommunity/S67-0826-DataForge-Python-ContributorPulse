import os
import requests
from dotenv import load_dotenv


# -----------------------------------------
# LOAD ENVIRONMENT VARIABLES
# -----------------------------------------

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# -----------------------------------------
# COMMON HEADERS
# -----------------------------------------

HEADERS = {
    "Accept": "application/vnd.github+json"
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


# -----------------------------------------
# GET REPOSITORY
# -----------------------------------------

def get_repository(owner, repository):
    """
    Get information about a GitHub repository.
    """

    url = f"https://api.github.com/repos/{owner}/{repository}"

    response = requests.get(
        url,
        headers=HEADERS
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
    Get contributors of a GitHub repository.
    """

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repository}/contributors"
    )

    response = requests.get(
        url,
        headers=HEADERS,
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


# -----------------------------------------
# GET COMMIT ACTIVITY
# -----------------------------------------

def get_commit_activity(owner, repository):
    """
    Get weekly commit activity for a repository.
    """

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repository}/stats/commit_activity"
    )

    response = requests.get(
        url,
        headers=HEADERS
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
# GET PULL REQUESTS
# -----------------------------------------

def get_pull_requests(owner, repository):
    """
    Get pull requests for a GitHub repository.
    """

    url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repository}/pulls"
    )

    response = requests.get(
        url,
        headers=HEADERS,
        params={
            "state": "all",
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