# LeetCode to GitHub Auto Sync

A secure, cloud-based Python automation engine that automatically synchronizes your accepted LeetCode solutions to your GitHub repository using GitHub Actions.

## Features

- **Cloud-Only Execution**: Runs completely on GitHub Actions. No continuous local processes, browser extensions, Tampermonkey, Selenium, or Playwright required. Your laptop can be turned off.
- **Multiple Approaches Support**: Solved a problem multiple ways? Preserves every unique logic approach (`approach-01.py`, `approach-02.py`, `approach-03.py`) without overwriting previous solutions.
- **Normalized Duplicate Detection**: Normalizes line endings, whitespace, and formatting to calculate a SHA-256 code hash. Re-submitting the exact same code skips duplicate file creation.
- **Security-First Architecture**: Strictly uses environment variables. Credentials (`LEETCODE_SESSION`, `LEETCODE_CSRF_TOKEN`) and tokens are never printed, logged, or committed to Git. Uses GitHub's built-in `${{ github.token }}`.
- **State Persistence**: Uses `leetcode-data.json` to maintain synchronization state across workflow runs.
- **Padded Problem Directories**: Organized by difficulty (`solutions/easy/`, `solutions/medium/`, `solutions/hard/`) with formatted problem IDs (e.g., `0001-two-sum/`).

---

## Project Structure

```
leetcode-auto-sync/
├── .github/
│   └── workflows/
│       └── leetcode-sync.yml    # GitHub Actions workflow (scheduled + manual trigger)
├── solutions/                   # Generated solution files folder
│   ├── easy/
│   ├── medium/
│   └── hard/
├── src/
│   ├── __init__.py
│   ├── leetcode_client.py       # LeetCode GraphQL API communication
│   ├── submission_parser.py     # Dataclass parsing and problem ID normalization
│   ├── solution_manager.py     # Code hashing, approach numbering, and file generation
│   ├── state_manager.py        # Synchronization state loading & atomic saving
│   └── git_manager.py           # Git staging, committing, and pushing helper
├── tests/                       # Complete unit test suite
│   ├── __init__.py
│   ├── test_submission_parser.py
│   ├── test_solution_manager.py
│   └── test_state_manager.py
├── sync.py                      # Main entrypoint script
├── config.json                  # Non-sensitive configuration file
├── leetcode-data.json           # Synchronization state file (tracked in Git)
├── requirements.txt             # Project dependencies
├── .env.example                 # Environment variables template
├── .gitignore                   # Git exclusion rules
└── README.md
```

---

## How It Works

1. **Trigger**: GitHub Actions runs automatically via schedule (`*/5 * * * *`) or manual dispatch (`workflow_dispatch`).
2. **Fetch**: Connects to `https://leetcode.com/graphql` using your authenticated session cookie and CSRF token to retrieve recent submissions.
3. **Filter**: Filters only `ACCEPTED` submissions; ignores rejected, wrong answer, TLE, or runtime error submissions.
4. **Duplicate & Approach Check**:
   - Calculates a normalized SHA-256 hash of the code.
   - If an identical code hash already exists for that problem, it logs `Skipped identical solution` and updates state without creating a new file.
   - If the solution has new code logic, it increments the approach number (e.g. `approach-02.py`).
5. **Save & Commit**: Creates the solution file with metadata comments, updates `leetcode-data.json`, commits the changes, and pushes to your GitHub repository.

```
solutions/
└── easy/
    └── 0001-two-sum/
        ├── approach-01.py
        ├── approach-02.py
        └── approach-03.py
```

---

## Security Requirements & Credentials

The system requires two LeetCode authentication tokens passed as environment variables:
- `LEETCODE_SESSION`
- `LEETCODE_CSRF_TOKEN`

### How to Get Your LeetCode Tokens:
1. Log in to [LeetCode](https://leetcode.com) in your web browser.
2. Open Developer Tools (`F12` or `Right-Click -> Inspect`).
3. Go to the **Application** tab -> **Cookies** -> `https://leetcode.com`.
4. Copy the value of:
   - `LEETCODE_SESSION`
   - `csrftoken` (use this as `LEETCODE_CSRF_TOKEN`)

> [!CAUTION]
> Never share or commit these credentials publicly. They provide access to your LeetCode account.

---

## Setup & Deployment Guide

### 1. GitHub Secrets Setup
1. Go to your GitHub repository: `https://github.com/Anbuchezhian24/leetcode-auto-sync`.
2. Navigate to **Settings** -> **Secrets and variables** -> **Actions**.
3. Click **New repository secret** and create:
   - Name: `LEETCODE_SESSION` | Value: *(Your session cookie value)*
   - Name: `LEETCODE_CSRF_TOKEN` | Value: *(Your csrf token value)*

> [!NOTE]
> You do **NOT** need to create a `GITHUB_TOKEN` secret. GitHub Actions automatically supplies `${{ github.token }}`.

### 2. Enable GitHub Actions Permissions
1. In your GitHub repository, navigate to **Settings** -> **Actions** -> **General**.
2. Scroll down to **Workflow permissions**.
3. Select **Read and write permissions**.
4. Click **Save**.

### 3. Triggering Manual Sync
You can trigger the synchronization at any time:
1. Go to the **Actions** tab in your repository.
2. Select **LeetCode to GitHub Sync** from the left sidebar.
3. Click **Run workflow**.

---

## Local Development & Testing

### Installation
Python 3.12+ is recommended.

```bash
# Clone the repository
git clone https://github.com/Anbuchezhian24/leetcode-auto-sync.git
cd leetcode-auto-sync

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Local Environment Setup
Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```env
LEETCODE_SESSION=your_leetcode_session_cookie_here
LEETCODE_CSRF_TOKEN=your_leetcode_csrf_token_here
```

### Execution Modes

1. **Dry-Run Mode (`python sync.py --dry-run`)**:
   Fetches submissions and simulates approach allocation and duplicate detection, but does **not** create solution files, does **not** save state to disk, and does **not** perform Git operations.

2. **No-Push Mode (`python sync.py --no-push`)**:
   Fetches real accepted submissions, creates solution files on disk (`solutions/`), updates and saves `leetcode-data.json`, but **skips** Git staging, commit, and push.

3. **Production Mode (`python sync.py`)**:
   Full sync workflow. Fetches accepted submissions, saves solution files on disk, updates state file, stages changes, creates a Git commit, and pushes to GitHub.

```bash
# Simulation mode (No files created, no state saved, no Git changes)
python sync.py --dry-run

# Local sync mode (Solution files created & state saved, but NO Git commit or push)
python sync.py --no-push

# Full production mode (Files created, state saved, Git committed & pushed)
python sync.py
```

### Running Unit Tests
Run the offline unit test suite:

```bash
python -m unittest discover tests
```

---

## Execution Schedule & Limitations

> [!IMPORTANT]
> **Scheduled Execution Delay**: GitHub Actions scheduled workflows (`cron: "*/5 * * * *"`) are executed by GitHub's background scheduler. Depending on GitHub Actions server load, scheduled workflows may occasionally be delayed by a few minutes. Synchronization is not instant, but runs automatically in the background without needing your computer powered on.

---

## License

MIT License.
