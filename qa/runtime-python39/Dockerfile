# Official Python 3.9.15, pinned to the verified registry manifest.
FROM python:3.9.15-slim-bullseye@sha256:ffc6cb648d6993e7c90abb95c2481eb688a6842dfac29bf19e3755454632daa2
RUN apt-get update && apt-get install -y --no-install-recommends lua5.1 lua-cjson \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
