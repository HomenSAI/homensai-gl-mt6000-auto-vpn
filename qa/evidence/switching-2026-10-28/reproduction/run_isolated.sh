#!/bin/sh
# Execute local reproduction with readonly host files and private /tmp.
# Network namespace is shared solely for the loopback QA bridge/private QEMU serial.
set -eu
: "${QA_OUTPUT:?Set QA_OUTPUT to the evidence directory}"
[ -d "$QA_OUTPUT" ] || mkdir -p "$QA_OUTPUT"
[ "$QA_OUTPUT" != / ] || exit 64
exec bwrap --unshare-user --ro-bind / / --bind "$QA_OUTPUT" "$QA_OUTPUT" --tmpfs /tmp --proc /proc --dev /dev --cap-drop ALL -- "$@"
