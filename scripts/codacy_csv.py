import os
import requests
import csv
import sys
import glob
from datetime import datetime

API_TOKEN = os.getenv("CODACY_API_TOKEN", "TdQ0e56GavNJdj0mpwXX")
PROVIDER = "gh"
ORG_NAME = os.getenv("CODACY_ORG_NAME", "octanner")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_CSV = os.path.join(REPORTS_DIR, f"codacy_soc_compliant_report_{timestamp}.csv")
LIMIT = 1000

os.makedirs(REPORTS_DIR, exist_ok=True)

# --- Find latest SOC-compliant file ---
def find_latest_soc_file():
    pattern = os.path.join(REPORTS_DIR, "soc_compliant_repos2_*.csv")
    files = glob.glob(pattern)
    if not files:
        print("\u274c No SOC-compliant report found. Expected format: soc_compliant_repos2_*.csv")
        sys.exit(1)
    latest_file = max(files, key=os.path.getmtime)
    print(f"\ud83d\udcc4 Using latest SOC-compliant file: {os.path.basename(latest_file)}")
    return latest_file

SOC_CSV = find_latest_soc_file()

# Read SOC-compliant repo names
soc_repos = set()
with open(SOC_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        repo_url = row.get("repo url", "")
        if repo_url:
            repo_name = repo_url.replace("https://github.com/", "").strip().lower()
            soc_repos.add(repo_name)

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "api-token": API_TOKEN
}

url = f"https://app.codacy.com/api/v3/search/analysis/organizations/{PROVIDER}/{ORG_NAME}/repositories"

all_repos = []
cursor = None
iteration = 1

while True:
    print(f"\n---- API CALL #{iteration} ----")
    payload = {"limit": LIMIT}
    if cursor:
        payload["cursor"] = cursor
    print(f"Payload being sent: {payload}")

    try:
        response = requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"Network/request error: {e}")
        sys.exit(1)

    print(f"Status code: {response.status_code}")
    if response.status_code in [401, 403]:
        print("AUTHENTICATION ERROR: Please check your API token. Exiting.")
        print("Response:", response.text)
        sys.exit(1)

    try:
        data = response.json()
    except Exception as e:
        print(f"JSON decoding error: {e}")
        print("Raw response:", response.text)
        sys.exit(1)

    print("Top-level keys in response:", list(data.keys()))
    if "data" not in data:
        print("ERROR: 'data' field missing from response. Response was:")
        print(data)
        sys.exit(1)

    repos = data.get("data", [])
    all_repos.extend(repos)
    print(f"Fetched {len(repos)} repos, total so far: {len(all_repos)}")

    pagination = data.get("pagination")
    if not pagination:
        print("INFO: No pagination block, ending.")
        break

    cursor = pagination.get("cursor")
    if not cursor:
        print("INFO: No further cursor found, ending pagination.")
        break

    print(f"Next cursor: {cursor}")
    iteration += 1

# Save to CSV
if all_repos:
    header = ["S no.", "name", "repo link", "compliance", "codacy integrated", "grade", "coverage percentage"]
    csv_rows = []
    idx = 1
    for item in all_repos:
        repo_info = item.get("repository", {})
        name = repo_info.get("name", "")
        owner = repo_info.get("owner", "")
        full_name = f"{owner}/{name}".lower()
        if full_name not in soc_repos:
            continue  # Skip non-SOC compliant repos

        provider = repo_info.get("provider", "")
        repo_link = f"https://github.com/{owner}/{name}" if provider == "gh" and owner and name else ""
        codacy_integrated = "Yes" if repo_info.get("addedState", "") == "Following" else "No"
        compliance = repo_info.get("codingStandardName", "")
        grade = item.get("gradeLetter", "") or item.get("grade", "")

        coverage = ""
        cov = item.get("coverage", {})
        if cov:
            if cov.get("coveragePercentage") is not None:
                coverage = f"{cov['coveragePercentage']:.2f}"
            elif cov.get("numberTotalFiles"):
                total_files = cov["numberTotalFiles"]
                files_uncovered = cov.get("filesUncovered", 0)
                coverage = f"{(1 - files_uncovered / total_files) * 100:.2f}" if total_files else ""

        csv_rows.append([idx, name, repo_link, compliance, codacy_integrated, grade, coverage])
        idx += 1

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(csv_rows)

    print(f"\u2705 Saved {len(csv_rows)} SOC-compliant Codacy repositories to {OUTPUT_CSV}")
else:
    print("\u26a0\ufe0f No repositories found or saved. Please check the debug output above.")
