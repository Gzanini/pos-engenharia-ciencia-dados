from __future__ import annotations

from pathlib import Path

from src import build_pipeline, resolve_project_root, save_outputs, summarize_sales


def main() -> None:
    project_root = resolve_project_root(Path(__file__).resolve().parent)
    raw_dir = project_root / "dados" / "raw"
    processed_dir = project_root / "dados" / "processed"

    df_base, df_model = build_pipeline(raw_dir)
    save_outputs(df_base, df_model, processed_dir)

    summary = summarize_sales(df_base)
    print("Base tratada:", df_base.shape)
    print("Base modelagem:", df_model.shape)
    print("Top products:")
    print(summary["top_products"].to_string(index=False))


if __name__ == "__main__":
    main()
