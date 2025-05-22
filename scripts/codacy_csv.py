'''import os
import requests
import csv

API_KEY = "TdQ0e56GavNJdj0mpwXX"
PROVIDER = "gh"
ORG_NAME = "octanner"
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
OUTPUT_CSV = os.path.join(REPORTS_DIR, "codacy_final.csv")
LIMIT = 1000  # Use up to 1000 if your endpoint supports it

# Ensure the reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "api-token": API_KEY
}

url = f"https://app.codacy.com/api/v3/search/analysis/organizations/{PROVIDER}/{ORG_NAME}/repositories"

all_repos = []
cursor = None

while True:
    payload = {"limit": LIMIT}
    if cursor:
        payload["cursor"] = cursor
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    repos = data.get("data", [])
    all_repos.extend(repos)
    pagination = data.get("pagination", {})
    cursor = pagination.get("cursor")
    print(f"Fetched {len(repos)} repos, total so far: {len(all_repos)}")
    if not cursor:
        break  # No more pages

header = ["S no.", "name", "repo link", "compliance", "codacy integrated", "grade", "coverage percentage"]
csv_rows = []

for idx, item in enumerate(all_repos, start=1):
    repo_info = item.get("repository", {})
    name = repo_info.get("name", "")
    owner = repo_info.get("owner", "")
    provider = repo_info.get("provider", "")
    repo_link = f"https://github.com/{owner}/{name}" if provider == "gh" and owner and name else ""
    codacy_integrated = "Yes" if repo_info.get("addedState", "") == "Following" else "No"
    compliance = repo_info.get("codingStandardName", "")
    grade = item.get("gradeLetter", "") or item.get("grade", "")
    coverage = ""
    if "coverage" in item:
        cov = item["coverage"]
        if "coveragePercentage" in cov and cov["coveragePercentage"] is not None:
            coverage = f"{cov['coveragePercentage']:.2f}"
        elif "numberTotalFiles" in cov and cov["numberTotalFiles"]:
            total_files = cov["numberTotalFiles"]
            files_uncovered = cov.get("filesUncovered", 0)
            coverage = f"{(1 - files_uncovered / total_files) * 100:.2f}"
    csv_rows.append([idx, name, repo_link, compliance, codacy_integrated, grade, coverage])

with open(OUTPUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(csv_rows)

print(f"Saved {len(csv_rows)} repositories to {OUTPUT_CSV}")'''
import os
import requests
import csv
import sys

API_TOKEN = os.getenv("CODACY_API_TOKEN", "TdQ0e56GavNJdj0mpwXX")
PROVIDER = "gh"
ORG_NAME = os.getenv("CODACY_ORG_NAME", "octanner")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
OUTPUT_CSV = os.path.join(REPORTS_DIR, "codacy_final.csv")
LIMIT = 100  # Set to small number for easier debugging

os.makedirs(REPORTS_DIR, exist_ok=True)

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

    # Authentication check
    if response.status_code == 401 or response.status_code == 403:
        print("AUTHENTICATION ERROR: Please check your API token. Exiting.")
        print("Response:", response.text)
        sys.exit(1)

    try:
        data = response.json()
    except Exception as e:
        print(f"JSON decoding error: {e}")
        print("Raw response:", response.text)
        sys.exit(1)

    # Print the full response for inspection (may be large!)
    print("Top-level keys in response:", list(data.keys()))
    if "data" not in data:
        print("ERROR: 'data' field missing from response. Response was:")
        print(data)
        sys.exit(1)
    repos = data.get("data", [])
    all_repos.extend(repos)
    print(f"Fetched {len(repos)} repos, total so far: {len(all_repos)}")

    # Pagination check
    pagination = data.get("pagination")
    if pagination is None:
        print("WARNING: No 'pagination' field found in response. Pagination may not be supported or your query returned all results on the first page.")
        print("Full response:", data)
        break

    print("Pagination block:", pagination)
    cursor = pagination.get("cursor")
    if not cursor:
        print("INFO: No further cursor found, ending pagination.")
        break  # No more pages

    print(f"Next cursor: {cursor}")
    iteration += 1

# Save to CSV (if any results)
if all_repos:
    header = ["S no.", "name", "repo link", "compliance", "codacy integrated", "grade", "coverage percentage"]
    csv_rows = []
    for idx, item in enumerate(all_repos, start=1):
        repo_info = item.get("repository", {})
        name = repo_info.get("name", "")
        owner = repo_info.get("owner", "")
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

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(csv_rows)
    print(f"Saved {len(csv_rows)} repositories to {OUTPUT_CSV}")
else:
    print("No repositories found or saved. Please check the debug output above.")

