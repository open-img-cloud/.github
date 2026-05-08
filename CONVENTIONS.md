# Image repository conventions

This document defines the contract every image repository in `open-img-cloud`
must follow to consume the shared build infrastructure hosted in this repo.

## Build runtime

All image builds run on **self-hosted Rocky 10 runners with nested virtualization**
(`/dev/kvm` exposed to the runner user). The reusable workflows expect runner
labels matching `["self-hosted","Linux","kvm"]` by default; consumers can
override via the `runner_labels` input.

Builds execute inside the **stackopshq builder image**
(`ghcr.io/stackopshq/libguestfs-tools:v2`), pinned to a major version. Before
the build job starts, a `verify-builder` job runs `cosign verify` against the
image's keyless signature; the build is aborted if verification fails. See
[`docs/runners.md`](docs/runners.md) for runner provisioning details.

## Required files in the caller repo

| Path                          | Purpose                                                              |
|-------------------------------|----------------------------------------------------------------------|
| `VERSION`                     | Single line. The currently pinned upstream version.                  |
| `build/customize.sh`          | Build hook (libguestfs repos). Receives qcow2 path as `$1`.          |
| `build/dib-build.sh`          | Build hook (DIB repos). Receives output dir as `$1`, version as `$2`.|
| `build/detect-upstream.sh`    | Prints the latest upstream version on stdout (one line).             |
| `build/config/`               | Config files referenced by `customize.sh` (cloud.cfg, scripts, etc). |
| `.github/workflows/release.yml` | Calls `build-libguestfs-image.yml` (or DIB equivalent) on tag push.|
| `.github/workflows/watch.yml`   | Schedules `upstream-watch.yml` on cron.                            |

## Required org-level secrets

Inherited by reusable workflows via `secrets: inherit`. Configure once at the
org level (Settings → Secrets and variables → Actions → New organization secret):

- `S3_GARAGE_ENDPOINT`, `S3_GARAGE_KEY_ID`, `S3_GARAGE_SECRET`
- `R2_ENDPOINT`, `R2_KEY_ID`, `R2_SECRET`
- `CF_ZONE_ID`, `CF_API_TOKEN`

## Release flow

1. The watch workflow runs daily, calling `detect-upstream.sh`.
2. If a new version is detected, it opens a PR bumping `VERSION`.
3. Merging the PR is a manual step.
4. After merge, push a git tag matching the version (e.g., `v3.22.0`).
5. The release workflow triggers on tag push, builds the image, signs it,
   uploads to Garage + R2, and purges Cloudflare cache for `latest/`.

Public download URL pattern:

```
https://images.openimages.cloud/<os_name>/<version>/<filename>
https://images.openimages.cloud/<os_name>/latest/<filename>
```

## Verifying a published image

Each release publishes alongside the qcow2:

- `<filename>.sha256`, `.sha1`, `.md5` per-file checksums
- `SHA256SUMS` aggregated checksum file
- `<filename>.sig`, `<filename>.cert` cosign keyless signature & certificate
- `MANIFEST.json` build metadata, including a `builder` block recording the
  exact builder image reference and content digest used to produce the qcow2
  (full chain of custody from base rootfs → published artifact).
- `index.html` static directory listing

End users verify with:

```sh
sha256sum -c SHA256SUMS
cosign verify-blob --certificate <filename>.cert \
                   --signature   <filename>.sig  \
                   --certificate-identity-regexp "https://github.com/open-img-cloud/" \
                   --certificate-oidc-issuer     "https://token.actions.githubusercontent.com" \
                   <filename>
```

## Example: `release.yml` for a libguestfs-based repo

```yaml
name: Build & publish image

on:
  push:
    tags: ['v*']
  workflow_dispatch:
    inputs:
      version:
        description: 'Override version (otherwise derived from tag)'
        required: false

jobs:
  build:
    uses: open-img-cloud/.github/.github/workflows/build-libguestfs-image.yml@main
    with:
      os_name: alpaquita-linux
      version: ${{ inputs.version }}
      output_filename: 'alpaquita-{version}-glibc-x86_64.qcow2'
      upstream_url: 'https://packages.bell-sw.com/alpaquita/glibc/stream/releases/x86_64/alpaquita-stream-{version}-glibc-x86_64.qcow2.xz'
      decompress: xz
    secrets: inherit
```

## Example: `watch.yml` for upstream auto-bump

```yaml
name: Watch upstream

on:
  schedule:
    - cron: '17 6 * * *'   # daily 06:17 UTC
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  watch:
    uses: open-img-cloud/.github/.github/workflows/upstream-watch.yml@main
    with:
      os_name: alpaquita-linux
```

## Example: `build/customize.sh` for Alpaquita

```bash
#!/usr/bin/env bash
# Receives the qcow2 path as $1. Runs in the libguestfs container.
set -euo pipefail
QCOW2="$1"
CONFIG_DIR="build/config"

virt-customize -a "$QCOW2" \
  --update \
  --install cloud-init,python3,py3-yaml,py3-requests,e2fsprogs-extra,util-linux,shadow,sudo,qemu-guest-agent,openssh-server,dhcpcd \
  --copy-in "${CONFIG_DIR}/cloud.cfg:/etc/cloud/" \
  --copy-in "${CONFIG_DIR}/grub:/etc/default/" \
  --copy-in "${CONFIG_DIR}/serial-config.sh:/usr/local/sbin/" \
  --run-command 'chmod +x /usr/local/sbin/serial-config.sh && /usr/local/sbin/serial-config.sh' \
  --run-command 'grub-mkconfig -o /boot/grub/grub.cfg' \
  --run-command 'setup-cloud-init' \
  --run-command 'rc-update add qemu-guest-agent default' \
  --run-command 'rc-update add sshd default' \
  --run-command 'rc-update add dhcpcd default'
```

## Example: `build/detect-upstream.sh` for Alpaquita

```bash
#!/usr/bin/env bash
# Prints the latest Alpaquita stream version (single line).
set -euo pipefail

# Strategy: follow the redirect of the -latest- URL to discover the dated filename.
url='https://packages.bell-sw.com/alpaquita/glibc/stream/releases/x86_64/alpaquita-stream-latest-glibc-x86_64.qcow2.xz'
resolved=$(curl -fsSI -o /dev/null -w '%{url_effective}' -L "$url")

# Expected: alpaquita-stream-<version>-glibc-x86_64.qcow2.xz
echo "$resolved" | grep -oE 'alpaquita-stream-[^-]+-glibc' | sed -E 's/^alpaquita-stream-(.+)-glibc$/\1/'
```

## Versioning rules

- `VERSION` holds the upstream version verbatim, no `v` prefix (e.g., `3.22.0`, `2.0.20240711.0`).
- Git tag for a release is `v<VERSION>` (e.g., `v3.22.0`).
- The `version` input passed to the reusable workflow is `<VERSION>` (no `v`).
  When omitted, the workflow strips the leading `v` from `github.ref_name`.

## Path conventions on the public CDN

Versioned objects are immutable and served with `Cache-Control: max-age=31536000, immutable`.
The `latest/` directory is a snapshot copy of the most recent build; it carries
`max-age=300` and is purged from the Cloudflare edge after each release.

Never link to `latest/` from documentation that needs reproducibility — link to
the versioned path instead.
