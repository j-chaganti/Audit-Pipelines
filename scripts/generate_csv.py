import os
import requests
import csv
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration Section 

# Retrieve the GitHub token from environment variable
GITHUB_TOKEN = os.getenv("TOKEN_GITHUB")
if not GITHUB_TOKEN:
    raise Exception("🚨 Missing required environment variable: TOKEN_GITHUB")

# Retrieve the GitHub organization from environment variable
GITHUB_ORG = os.getenv("ORG_GITHUB")
if not GITHUB_ORG:
    raise Exception("🚨 Missing required environment variable: ORG_GITHUB")

# Set up the HTTP headers for GitHub API requests
GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Helper Functions 

def get_github_repos(org):
    """
    Fetch all repositories in the specified GitHub organization.
    Handles pagination to retrieve all repositories.
    """
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}"
        resp = requests.get(url, headers=GITHUB_HEADERS)
        if resp.status_code != 200:
            print(f"❌ Failed to fetch repos (status {resp.status_code}): {resp.text}")
            break
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos

def get_custom_properties(owner, repo):
    """
    Fetch custom properties from the GitHub API for a specific repository.
    Returns the raw JSON response or None if the request fails.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/properties/values"
    resp = requests.get(url, headers=GITHUB_HEADERS)
    if resp.status_code != 200:
        return None
    return resp.json()

def is_soc_compliant(custom_properties):
    """
    Checks if the repository has the custom property 'Compliance' set to 'soc'.
    Returns True if compliant, otherwise False.
    """
    if not custom_properties:
        return False

    # Handle both list and dict API responses for custom properties
    if isinstance(custom_properties, list):
        for item in custom_properties:
            key = item.get("property_name") or item.get("name")
            if key and key.strip().lower() == "compliance":
                if str(item.get("value", "")).strip().lower() == "soc":
                    return True
    else:
        props = custom_properties.get("properties", {})
        for key, value in props.items():
            if key.strip().lower() == "compliance" and str(value).strip().lower() == "soc":
                return True
    return False

def check_codacy_badge(owner, repo):
    """
    Checks if the README contains a Codacy badge or codacy.com reference.
    Returns "yes" if found, "no" otherwise.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    resp = requests.get(url, headers=GITHUB_HEADERS)
    if resp.status_code != 200:
        return "no"
    content = resp.json().get("content", "")
    if not content:
        return "no"
    try:
        readme_text = base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        return "no"
    if "codacy.com" in readme_text.lower() or "shields.io/codacy" in readme_text.lower():
        return "yes"
    return "no"

def export_to_csv(rows):
    """
    Export the provided rows to a CSV file with standard headers,
    saving into the reports/ directory at the repo root.
    """
    # Save CSV to reports/ directory at repo root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(script_dir, '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)  # Ensure reports directory exists
    filename = os.path.join(reports_dir, "soc_compliant_repos2.csv")
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "S no.", "name", "repo url", "default branch",
            "codacy integration", "custom properties"
        ])
        for idx, row in enumerate(rows, 1):
            writer.writerow([idx] + row)
    print(f"✅ CSV saved: {filename}")

# --------------------- Main Logic ----------------------------------

def main():
    """
    The main function orchestrates fetching, filtering, and exporting
    SOC-compliant repositories in a GitHub organization.
    """

    org = GITHUB_ORG

    # Fetch all repositories in the organization
    github_repos = get_github_repos(org)
    print(f"🔎 Total GitHub repos found: {len(github_repos)}")

    def build_row(repo):
        """
        Build a CSV row for a repository if it is SOC-compliant.
        Returns the row as a list or None if not compliant.
        """
        name = repo.get("name", "")
        owner = repo.get("owner", {}).get("login", org)
        repo_url = repo.get("html_url", "")
        default_branch = repo.get("default_branch", "")

        # Fetch custom properties and check SOC compliance
        custom_props = get_custom_properties(owner, name)
        if is_soc_compliant(custom_props):
            codacy_integration = check_codacy_badge(owner, name)
            return [
                name,
                repo_url,
                default_branch,
                codacy_integration,
                "SOC"
            ]
        return None  # Exclude non-SOC-compliant repos

    # Process repositories in parallel to speed up the workflow
    soc_rows = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(build_row, repo) for repo in github_repos]
        for future in as_completed(futures):
            row = future.result()
            if row:
                soc_rows.append(row)

    # Sort the output alphabetically by repo name for professional presentation
    soc_rows.sort(key=lambda x: x[0].lower())

    if not soc_rows:
        print("⚠️ No SOC-compliant repositories found.")
    else:
        export_to_csv(soc_rows)

# Entry Point 

if __name__ == "__main__":
    main()
