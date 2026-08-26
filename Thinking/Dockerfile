FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

RUN apt-get update && \
    apt-get install -y python3 python3-pip git build-essential cmake ninja-build && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app/Thinking

COPY requirements.txt .

ENV CMAKE_ARGS="-DGGML_CUDA=on"
ENV FORCE_CMAKE=1

RUN pip3 install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cu124
 
RUN pip3 install --no-cache-dir scikit-learn==1.4.2

COPY . /app/Thinking

EXPOSE 7000

CMD ["python3", "server.py"]