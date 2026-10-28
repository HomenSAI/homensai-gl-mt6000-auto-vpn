# Offline Python 3.11 CI image

The Dockerfile pins the two existing local CI images by their verified digest.
It adds the same Lua 5.1/CJSON binaries used by the Python 3.9 matrix to the
Python 3.11/Node tools image. It uses the Bookworm base's readline/tinfo/glibc;
the build executes a Lua/CJSON smoke check. This records the offline image
composition; rebuilding either input image itself requires its original inputs.

With both pinned images already present locally, build without network access:

```powershell
$env:DOCKER_BUILDKIT='0'
docker build --pull=false --network=none -t homensai-vpn-python311:candidate qa/runtime-python311
```

The candidate passed the complete dual-runtime matrix on source
`0566c457f293a76e86b52829f6e31a2c3586f964`: both runtimes produced package SHA256
`e87946336bcf39981cda27132c14f44a3dfb848eeccc4901fd62fbfee5786e8b`.
After this proof, the image was tagged `homensai-vpn-python311:local`; the local
test and offline CI scripts use that tag by default. Existing input images stay
unchanged. On another offline host, validate the candidate before assigning the
local tag: `docker tag homensai-vpn-python311:candidate homensai-vpn-python311:local`.
Validate a committed snapshot with `./scripts/offline-ci.ps1 -SourceCommit <full-sha>`.
For the 3.9 image, its Dockerfile is `../runtime-python39/Dockerfile`; its apt
packages must already be available in a local build cache for an offline build.

The CI receipt includes `tools_tests`, `lab_tests`, `lab_node_suites`,
`lab_skipped_scripts`, and `lua_tests` (actual completed Lua-backed cases).
Lab unit-test entry points are explicitly allowlisted in `qa/run_offline_ci.py`.
VM/router/network scripts are listed as excluded without importing them; a new
`test_*` entry must be reviewed for offline safety before CI will accept it.
