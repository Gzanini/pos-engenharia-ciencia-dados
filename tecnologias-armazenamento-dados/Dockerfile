FROM apache/airflow:2.10.5-python3.11

COPY --chown=airflow:root pyproject.toml /opt/airflow/project/pyproject.toml
COPY --chown=airflow:root src /opt/airflow/project/src

RUN pip install --no-cache-dir -e "/opt/airflow/project[gcp]"

