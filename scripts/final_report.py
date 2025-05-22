import csv
import json
import matplotlib.pyplot as plt
from collections import Counter
import os

# Directory where this script lives
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
REPORTS_DIR = os.path.join(SCRIPT_DIR, "..", "reports")
CSV_PATH = os.path.join(REPORTS_DIR, "codacy_final.csv")
GRADE_PIE_PATH = os.path.join(REPORTS_DIR, "codacy_grade_piechart.png")
COVERAGE_BAR_PATH = os.path.join(REPORTS_DIR, "codacy_coverage_barchart.png")
BENCHMARK_PIE_PATH = os.path.join(REPORTS_DIR, "codacy_coverage_benchmark_piechart.png")

# Ensure the reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)

# Read benchmark from config
with open(CONFIG_PATH) as f:
    config = json.load(f)
COVERAGE_BENCHMARK = config.get("coverage_benchmark", 80.0)

grades = []
coverages = []
repo_names = []

with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        grades.append(row.get("grade") or "Unknown")
        try:
            coverage = float(row.get("coverage percentage", 0.0))
        except (ValueError, KeyError):
            coverage = 0.0
        coverages.append(coverage)
        repo_names.append(row.get("name", ""))

# Pie chart for repository grades
grade_counts = Counter(grades)
plt.figure(figsize=(6,6))
plt.pie(grade_counts.values(), labels=grade_counts.keys(), autopct='%1.1f%%', startangle=140)
plt.title('Repository Grade Distribution')
plt.axis('equal')
plt.tight_layout()
plt.savefig(GRADE_PIE_PATH)
plt.show()

# Bar chart for repository coverage
plt.figure(figsize=(max(10, len(repo_names)*0.5),6))
plt.bar(repo_names, coverages, color=['green' if c >= COVERAGE_BENCHMARK else 'red' for c in coverages])
plt.axhline(COVERAGE_BENCHMARK, color='orange', linestyle='dashed', linewidth=2, label=f'Benchmark: {COVERAGE_BENCHMARK}%')
plt.xlabel('Repository')
plt.ylabel('Coverage Percentage')
plt.title('Coverage Percentage by Repository')
plt.xticks(rotation=45, ha='right')
plt.legend()
plt.tight_layout()
plt.savefig(COVERAGE_BAR_PATH)
plt.show()

# Analytics: How many are above/below benchmark
above = sum(1 for c in coverages if c >= COVERAGE_BENCHMARK)
below = sum(1 for c in coverages if c < COVERAGE_BENCHMARK)
total = len(coverages)

print(f"Coverage Benchmark: {COVERAGE_BENCHMARK}%")
print(f"Repositories above or equal to benchmark: {above} ({(above/total)*100:.1f}%)")
print(f"Repositories below benchmark: {below} ({(below/total)*100:.1f}%)")

# Pie chart for above/below benchmark
plt.figure(figsize=(5,5))
plt.pie([above, below], labels=['Above/Eq Benchmark', 'Below Benchmark'], autopct='%1.1f%%', colors=['green', 'red'])
plt.title(f'Repositories Coverage vs {COVERAGE_BENCHMARK}% Benchmark')
plt.axis('equal')
plt.tight_layout()
plt.savefig(BENCHMARK_PIE_PATH)
plt.show()
