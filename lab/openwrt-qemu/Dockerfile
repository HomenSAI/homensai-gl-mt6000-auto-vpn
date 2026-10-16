FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends qemu-system-x86 python3 curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /lab
COPY run.py /usr/local/bin/homensai-qemu
CMD ["python3", "/usr/local/bin/homensai-qemu"]
