# Preparation may download Debian packages; actual SDK compile runs --network none.
FROM local-dev-tools:installed@sha256:0b4418ddd722b07b92fe44d180df10fe252e105cd85ff830040e77b0fb34e3a7
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential flex bison gawk gettext libncurses-dev libssl-dev \
    zlib1g-dev rsync patch file xz-utils wget bzip2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 10001 --create-home sdkbuilder
USER 10001:10001
WORKDIR /home/sdkbuilder
