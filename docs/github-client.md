# ContributorPulse GitHub API Client

The ContributorPulse backend includes a typed GitHub REST API client designed for repository ingestion, contributor profiling, and activity tracking with rate-limit and backoff handling.

---

## Capabilities & Architecture

- **Authentication:** Reads `GITHUB_TOKEN` from application configuration; sends `Authorization: Bearer <token>` when configured.
- **Secret Safety:** The token is never exposed in logs, exceptions, or string representations (`__repr__`).
- **Pagination:** Handles pagination across multiple pages (`per_page=100`) up to optional `max_pages`.
- **Transient Failure Retries:** Retries 500, 502, 503, 504, and network timeouts with exponential backoff (`backoff_factor * 2^attempt`).
- **Rate Limit Handling:** Parses `x-ratelimit-remaining`, `x-ratelimit-reset`, and `retry-after` headers, raising typed `GitHubRateLimitError`.
- **Dependency Injection:** Accepts custom HTTP transports / clients for test isolation.

---

## Domain Methods

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `get_repository(owner, repo)` | `GET /repos/{owner}/{repo}` | Fetches repository metadata, stars, forks, language, and default branch. |
| `get_contributors(owner, repo, max_pages)` | `GET /repos/{owner}/{repo}/contributors` | Fetches repository contributors with pagination. |
| `get_pull_requests(owner, repo, state, max_pages)` | `GET /repos/{owner}/{repo}/pulls` | Fetches pull requests with state filtering (`all`, `open`, `closed`). |
| `get_issues(owner, repo, state, max_pages)` | `GET /repos/{owner}/{repo}/issues` | Fetches repository issues and discussion items. |
| `get_reviews(owner, repo, pull_number, max_pages)` | `GET /repos/{owner}/{repo}/pulls/{number}/reviews` | Fetches review submissions and approval states for a PR. |
| `get_comments(owner, repo, issue_number, max_pages)` | `GET /repos/{owner}/{repo}/issues/[{number}/]comments` | Fetches discussion comments on PRs and issues. |
| `get_commits(owner, repo, max_pages)` | `GET /repos/{owner}/{repo}/commits` | Fetches commit history with timestamps and diff volumes. |
| `get_contributor_commits(owner, repo, author, max_pages)` | `GET /repos/{owner}/{repo}/commits?author={author}` | Fetches commits authored by a specific contributor. |
| `get_commit_activity(owner, repo)` | `GET /repos/{owner}/{repo}/stats/commit_activity` | Fetches weekly commit frequency stats. |

---

## Typed Exception Hierarchy

```
GitHubAPIError
├── GitHubAuthenticationError (HTTP 401)
├── GitHubForbiddenError (HTTP 403)
├── GitHubRateLimitError (HTTP 403 Rate Limit / HTTP 429)
├── GitHubNotFoundError (HTTP 404)
├── GitHubValidationError (HTTP 422)
├── GitHubTimeoutError (Network/Timeout)
└── GitHubServerError (HTTP 5xx)
```

---

## Requirements Coverage
- **FR-02:** GitHub repository metadata retrieval.
- **FR-03:** Contributor list and profile extraction.
- **FR-04:** Pull request, review, and comment ingestion.
- **FR-05:** Issue interaction metrics.
- **FR-06:** Commit history and weekly activity tracking.
- **NFR-04:** Safe configuration and secret masking.
- **NFR-05:** Bounded retries, pagination, and deterministic mock testing.
