import csv
import json
import matplotlib.pyplot as plt
from collections import Counter
import pandas as pd
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage

# ----- CONFIGURATION -----
CONFIG_FILE = "config.json"
CSV_FILE = "codacy_final.csv"
EXCEL_FILE = "codacy_report.xlsx"
PNG_GRADE_PIE = "codacy_grade_piechart.png"
PNG_COVERAGE_BAR = "codacy_coverage_barchart.png"
PNG_BENCHMARK_PIE = "codacy_coverage_benchmark_piechart.png"

# ----- READ CONFIG -----
with open(CONFIG_FILE) as f:
    config = json.load(f)
COVERAGE_BENCHMARK = config.get("coverage_benchmark", 80.0)

# ----- PROCESS CSV AND GENERATE CHARTS -----
grades = []
coverages = []
repo_names = []

with open(CSV_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        grades.append(row["grade"] or "Unknown")
        try:
            coverage = float(row["coverage percentage"])
        except (ValueError, KeyError):
            coverage = 0.0
        coverages.append(coverage)
        repo_names.append(row["name"])

# Pie chart for repository grades
grade_counts = Counter(grades)
plt.figure(figsize=(6,6))
plt.pie(grade_counts.values(), labels=grade_counts.keys(), autopct='%1.1f%%', startangle=140)
plt.title('Repository Grade Distribution')
plt.axis('equal')
plt.tight_layout()
plt.savefig(PNG_GRADE_PIE)
plt.close()

# Bar chart for repository coverage
plt.figure(figsize=(10,6))
plt.bar(repo_names, coverages, color=['green' if c >= COVERAGE_BENCHMARK else 'red' for c in coverages])
plt.axhline(COVERAGE_BENCHMARK, color='orange', linestyle='dashed', linewidth=2, label=f'Benchmark: {COVERAGE_BENCHMARK}%')
plt.xlabel('Repository')
plt.ylabel('Coverage Percentage')
plt.title('Coverage Percentage by Repository')
plt.xticks(rotation=45, ha='right')
plt.legend()
plt.tight_layout()
plt.savefig(PNG_COVERAGE_BAR)
plt.close()

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
plt.savefig(PNG_BENCHMARK_PIE)
plt.close()

# ----- EXPORT TO EXCEL AND EMBED IMAGES -----
df = pd.read_csv(CSV_FILE)
df.to_excel(EXCEL_FILE, index=False)

wb = load_workbook(EXCEL_FILE)
ws = wb.active

img_start_row = len(df) + 3  # Leave a couple of empty rows after table

ws.add_image(XLImage(PNG_GRADE_PIE), f"B{img_start_row}")
ws.add_image(XLImage(PNG_COVERAGE_BAR), f"B{img_start_row + 20}")
ws.add_image(XLImage(PNG_BENCHMARK_PIE), f"B{img_start_row + 40}")

wb.save(EXCEL_FILE)
print(f"Excel report generated: {EXCEL_FILE} with charts embedded.")
