import os
import csv
import json
import matplotlib.pyplot as plt
from collections import Counter
import pandas as pd
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage

# ------------------------ CONFIGURATION ------------------------

# Set up report directory outside current folder (one level up, named 'codacy_reports')
REPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'codacy_reports'))
os.makedirs(REPORT_DIR, exist_ok=True)

# Update paths for config and CSV as requested:
# - config.json in the scripts folder (same as this script)
# - codacy_final.csv in the reports folder at the repo root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
CSV_FILE = os.path.join(REPO_ROOT, "reports", "codacy_final.csv")

EXCEL_FILE = os.path.join(REPORT_DIR, "codacy_report.xlsx")
PNG_GRADE_PIE = os.path.join(REPORT_DIR, "codacy_grade_piechart.png")
PNG_COVERAGE_BAR = os.path.join(REPORT_DIR, "codacy_coverage_barchart.png")
PNG_BENCHMARK_PIE = os.path.join(REPORT_DIR, "codacy_coverage_benchmark_piechart.png")
PNG_ISSUE_BAR = os.path.join(REPORT_DIR, "codacy_issue_barchart.png")
PNG_ISSUE_PIE = os.path.join(REPORT_DIR, "codacy_issue_benchmark_piechart.png")

# ------------------------ DATA LOADING FUNCTIONS ------------------------

def load_config(config_path):
    """Load coverage and issue percentage benchmarks from config file."""
    with open(config_path) as f:
        config = json.load(f)
    coverage_benchmark = config.get("coverage_benchmark", 80.0)
    issue_benchmark = config.get("issue_benchmark", 90.0)
    return coverage_benchmark, issue_benchmark

def load_csv_data(csv_path):
    """
    Load repository names, grades, coverage %, and issue % from CSV.
    Returns: (repo_names, grades, coverages, issue_percentages)
    """
    repo_names = []
    grades = []
    coverages = []
    issue_percentages = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            repo_names.append(row.get("name", ""))
            grades.append(row.get("grade") or "Unknown")
            try:
                coverage = float(row.get("coverage percentage", 0.0))
            except (ValueError, KeyError):
                coverage = 0.0
            coverages.append(coverage)
            try:
                issue_pct = float(row.get("issue percentage", 0.0))
            except (ValueError, KeyError):
                issue_pct = 0.0
            issue_percentages.append(issue_pct)
    return repo_names, grades, coverages, issue_percentages

# ------------------------ CHART GENERATION FUNCTIONS ------------------------

def plot_grade_pie_chart(grades, save_path):
    """Plot and save a pie chart of grade distribution."""
    grade_counts = Counter(grades)
    plt.figure(figsize=(6,6))
    plt.pie(grade_counts.values(), labels=grade_counts.keys(), autopct='%1.1f%%', startangle=140)
    plt.title('Repository Grade Distribution')
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def plot_metric_bar_chart(repo_names, metric_values, benchmark, ylabel, title, save_path):
    """
    Plot and save a bar chart for a given metric.
    Green bars: >= benchmark, Red bars: < benchmark.
    """
    plt.figure(figsize=(max(10, len(repo_names)*0.5), 6))
    colors = ['green' if v >= benchmark else 'red' for v in metric_values]
    plt.bar(repo_names, metric_values, color=colors)
    plt.axhline(benchmark, color='orange', linestyle='dashed', linewidth=2, label=f'Benchmark: {benchmark}%')
    plt.xlabel('Repository')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

def plot_benchmark_pie_chart(metric_values, benchmark, above_label, below_label, title, save_path):
    """
    Plot and save a pie chart for above/equal vs. below benchmark.
    Also prints analytics summary to console.
    """
    above = sum(1 for v in metric_values if v >= benchmark)
    below = sum(1 for v in metric_values if v < benchmark)
    total = len(metric_values)
    percent_above = (above / total) * 100 if total else 0
    percent_below = (below / total) * 100 if total else 0

    print(f"{title} Benchmark: {benchmark}%")
    print(f"Repositories above or equal to benchmark: {above} ({percent_above:.1f}%)")
    print(f"Repositories below benchmark: {below} ({percent_below:.1f}%)\n")

    plt.figure(figsize=(5,5))
    plt.pie([above, below], labels=[above_label, below_label], autopct='%1.1f%%', colors=['green', 'red'])
    plt.title(title)
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()

# ------------------------ EXCEL EXPORT FUNCTION ------------------------

def export_to_excel_with_images(csv_file, excel_file, image_paths):
    """
    Export CSV data to Excel and embed images below the table.
    image_paths: List of (image_path, row_offset) tuples.
    """
    df = pd.read_csv(csv_file)
    df.to_excel(excel_file, index=False)

    wb = load_workbook(excel_file)
    ws = wb.active

    img_start_row = len(df) + 3  # Leave a couple of empty rows after table

    for idx, (img_path, row_offset) in enumerate(image_paths):
        cell_ref = f"B{img_start_row + row_offset}"
        img = XLImage(img_path)
        ws.add_image(img, cell_ref)

    wb.save(excel_file)
    print(f"Excel report generated: {excel_file} with charts embedded.")

# ------------------------ MAIN FUNCTION ------------------------

def main():
    # Load config benchmarks
    coverage_benchmark, issue_benchmark = load_config(CONFIG_FILE)

    # Load CSV data
    repo_names, grades, coverages, issue_percentages = load_csv_data(CSV_FILE)

    # Generate and save charts
    plot_grade_pie_chart(grades, PNG_GRADE_PIE)

    plot_metric_bar_chart(
        repo_names, coverages, coverage_benchmark,
        ylabel="Coverage Percentage",
        title="Coverage Percentage by Repository",
        save_path=PNG_COVERAGE_BAR
    )
    plot_benchmark_pie_chart(
        coverages, coverage_benchmark,
        above_label="Above/Eq Benchmark",
        below_label="Below Benchmark",
        title=f"Repositories Coverage vs {coverage_benchmark}% Benchmark",
        save_path=PNG_BENCHMARK_PIE
    )

    plot_metric_bar_chart(
        repo_names, issue_percentages, issue_benchmark,
        ylabel="Issue Percentage",
        title="Issue Percentage by Repository",
        save_path=PNG_ISSUE_BAR
    )
    plot_benchmark_pie_chart(
        issue_percentages, issue_benchmark,
        above_label="Above/Eq Issue Benchmark",
        below_label="Below Issue Benchmark",
        title=f"Repositories Issue % vs {issue_benchmark}% Benchmark",
        save_path=PNG_ISSUE_PIE
    )

    # Export to Excel and embed images, spaced out to avoid congestion
    image_paths = [
        (PNG_GRADE_PIE, 0),
        (PNG_COVERAGE_BAR, 30),
        (PNG_BENCHMARK_PIE, 65),
        (PNG_ISSUE_BAR, 100),
        (PNG_ISSUE_PIE, 135),
    ]
    export_to_excel_with_images(CSV_FILE, EXCEL_FILE, image_paths)

# ------------------------ ENTRY POINT ------------------------

if __name__ == "__main__":
    main()
