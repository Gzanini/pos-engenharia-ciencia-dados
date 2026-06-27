from etl_core import executar_em_loop

if __name__ == "__main__":
    # Executa ETL em modo continuo para processar novos arquivos periodicamente.
    executar_em_loop(sleep_seconds=30)
