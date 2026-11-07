# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
# TLC image for the optional CI cross-check (tools/formal/tla/tlc_check.py). Build with scripts/build-tlc-image.ps1,
# which puts tla2tools.jar next to this file in a temporary build context. The jar is never stored in git and is
# never downloaded at CI time; its sha256 is verified here at build time.
FROM eclipse-temurin:21-jre
ARG JAR_SHA256=936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88
COPY tla2tools.jar /opt/tlc/tla2tools.jar
RUN echo "${JAR_SHA256}  /opt/tlc/tla2tools.jar" | sha256sum -c - && chmod 0444 /opt/tlc/tla2tools.jar
LABEL org.homensai.tla2tools.sha256="${JAR_SHA256}" \
      org.homensai.purpose="TLC 1.7.4 for tools/formal/tla (offline CI cross-check)"
ENTRYPOINT []
CMD ["java", "-cp", "/opt/tlc/tla2tools.jar", "tlc2.TLC", "-h"]
