from etl_core import executar_uma_vez

if __name__ == "__main__":
    # Executa um ciclo unico de ETL e imprime um resumo da execucao.
    results = executar_uma_vez()
    for r in results:
        print(f"{r.file_name} | {r.status} | {r.rows_loaded}")
