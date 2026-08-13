FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

RUN apt-get update && \
    apt-get install -y python3 python3-pip git build-essential cmake ninja-build && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app/Speaking

COPY requirements.txt .

ENV CMAKE_ARGS="-DGGML_CUDA=on"
ENV FORCE_CMAKE=1

RUN pip3 install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu124
 
COPY . /app/Speaking/

EXPOSE 9001

CMD ["python3", "server.py"]