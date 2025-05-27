import os
import requests
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration Section

GITHUB_TOKEN = os.getenv("TOKEN_GITHUB")
if not GITHUB_TOKEN:
    raise Exception("🚨 Missing required environment variable: TOKEN_GITHUB")

GITHUB_ORG = os.getenv("ORG_GITHUB")
if not GITHUB_ORG:
    raise Exception("🚨 Missing required environment variable: ORG_GITHUB")

CODACY_TOKEN = os.getenv("CODACY_API_TOKEN")
if not CODACY_TOKEN:
    raise Exception("🚨 Missing required environment variable: CODACY_API_TOKEN")

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

CODACY_HEADERS = {
    "api-token": CODACY_TOKEN,
    "Accept": "application/json"
}

# Helper Functions

def get_github_repos(org):
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
    url = f"https://api.github.com/repos/{owner}/{repo}/properties/values"
    resp = requests.get(url, headers=GITHUB_HEADERS)
    if resp.status_code != 200:
        return None
    return resp.json()

def is_soc_compliant(custom_properties):
    if not custom_properties:
        return False
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

def get_codacy_projects(org):
    projects = set()
    page = 1
    while True:
        url = f"https://api.codacy.com/2.0/organizations/{org}/projects?page={page}&per_page=100"
        resp = requests.get(url, headers=CODACY_HEADERS)
        if resp.status_code == 404:
            print(f"❌ Codacy organization {org} not found or no access.")
            break
        if resp.status_code != 200:
            print(f"❌ Failed to fetch Codacy projects (status {resp.status_code}): {resp.text}")
            break
        data = resp.json()
        projects_on_page = data.get("projects", [])
        if not projects_on_page:
            break
        for proj in projects_on_page:
            repo_full_name = proj.get("repositoryFullName") or proj.get("name")
            if repo_full_name and "/" in repo_full_name:
                projects.add(repo_full_name.lower())
        page += 1
    return projects

def export_to_csv(rows):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(script_dir, '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    # Add timestamp to filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(reports_dir, f"soc_compliant_repository_{timestamp}.csv")

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
    org = GITHUB_ORG

    codacy_projects = get_codacy_projects(org)
    print(f"🔎 Codacy projects found: {len(codacy_projects)}")

    github_repos = get_github_repos(org)
    print(f"🔎 Total GitHub repos found: {len(github_repos)}")

    def build_row(repo):
        name = repo.get("name", "")
        owner = repo.get("owner", {}).get("login", org)
        repo_url = repo.get("html_url", "")
        default_branch = repo.get("default_branch", "")
        repo_full_name = f"{owner}/{name}".lower()

        custom_props = get_custom_properties(owner, name)
        if is_soc_compliant(custom_props):
            codacy_integration = "yes" if repo_full_name in codacy_projects else "no"
            return [
                name,
                repo_url,
                default_branch,
                codacy_integration,
                "SOC"
            ]
        return None

    soc_rows = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(build_row, repo) for repo in github_repos]
        for future in as_completed(futures):
            row = future.result()
            if row:
                soc_rows.append(row)

    soc_rows.sort(key=lambda x: x[0].lower())

    if not soc_rows:
        print("⚠️ No SOC-compliant repositories found.")
    else:
        export_to_csv(soc_rows)

if __name__ == "__main__":
    main()
