from etl_core import run_loop

if __name__ == "__main__":
    # Runs ETL in continuous mode to process new files periodically.
    run_loop(sleep_seconds=30)
