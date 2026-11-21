FROM tensorflow/tensorflow:2.20.0-gpu-jupyter

WORKDIR /workspace

COPY requirements.txt /tmp/eurosat-requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /tmp/eurosat-requirements.txt

ENV TF_FORCE_GPU_ALLOW_GROWTH=true \
    TF_CPP_MIN_LOG_LEVEL=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.token=eurosat", "--ServerApp.password="]
