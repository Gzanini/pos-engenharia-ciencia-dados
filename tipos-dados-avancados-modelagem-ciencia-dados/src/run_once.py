from etl_core import run_once

if __name__ == "__main__":
    # Runs a single ETL cycle and prints a concise execution summary.
    results = run_once()
    for r in results:
        print(f"{r.file_name} | {r.status} | {r.rows_loaded}")
