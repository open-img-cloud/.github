# Image repository conventions

This document defines the contract every image repository in `open-img-cloud`
must follow to consume the shared build infrastructure hosted in this repo.

## Build runtime

All image builds run on **self-hosted Rocky 10 runners with nested virtualization**
(`/dev/kvm` exposed to the runner user). The reusable workflows expect runner
labels matching `["self-hosted","Linux","kvm"]` by default; consumers can
override via the `runner_labels` input.

Builds execute inside the **stackopshq builder image**
(`ghcr.io/stackopshq/libguestfs-tools:2`), pinned to a major version. Before
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
org level (Settings → Secrets and variables → Actions → New organization secret)
and grant access to the runner-group repos (or "Selected repositories"):

- `S3_GARAGE_ENDPOINT`, `S3_GARAGE_KEY_ID`, `S3_GARAGE_SECRET`
- `R2_ENDPOINT`, `R2_KEY_ID`, `R2_SECRET`
- `CF_ZONE_ID`, `CF_API_TOKEN`

These secrets are declared `required: false` in the reusable workflow
definitions so PR validation / dry-runs (`workflow_dispatch publish=false`)
can dispatch without them. When `publish=true`, the build job runs a
fail-fast validation step that errors out if any are empty.

## Tracked `build/` directory

If your global gitignore excludes `build/` (a common pattern, e.g. for
Go / Cargo / Maven build outputs), add a repo-local override so the
build hooks (`customize.sh`, `detect-upstream.sh`, `config/`) get tracked:

```gitignore
# Override global build/ exclusion: this repo uses build/ for OIC build hooks.
!/build/
```

A leading `!/build/` re-includes the directory at repo root. Note that
files initially have to be force-added (`git add -f build/...`) the
first time, since gitignore takes precedence on staging until the
override is committed.

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

## Customize hook gotchas

Two non-obvious traps consistently hit customize hooks and waste a build
or two before being noticed:

1. **`virt-customize --install` requires libguestfs OS inspection to
   recognize the guest rootfs.** Distros that aren't in the libguestfs
   detection table (or that don't ship `ID_LIKE=<known-distro>` in
   `/etc/os-release`) fail with:
   ```
   virt-customize: error: cannot use '--install' because no package
   manager has been detected for this guest OS.
   ```
   **Fix:** use the distro's package manager directly via
   `--run-command`. For example, on Alpaquita (Alpine fork, not detected):
   `--run-command 'apk add cloud-init python3 ...'`.

2. **Minimal upstream rootfs may not contain expected directories.**
   Notably `/usr/local/sbin/` is absent from many Alpine/Alpaquita
   images. Chain a `--mkdir <dir>` *before* the `--copy-in` that
   targets it:
   ```
   --mkdir /usr/local/sbin --copy-in build/config/serial-config.sh:/usr/local/sbin/
   ```

## Example: `build/customize.sh` for Alpaquita

```bash
#!/usr/bin/env bash
# Receives the qcow2 path as $1. Runs in the libguestfs container.
set -euo pipefail
QCOW2="$1"
CONFIG_DIR="build/config"

# Note: --install fails on Alpaquita (libguestfs doesn't detect the
# package manager); we shell out to apk via --run-command instead.
virt-customize -a "$QCOW2" \
  --run-command 'apk update' \
  --run-command 'apk upgrade' \
  --run-command 'apk add cloud-init python3 py3-yaml py3-requests e2fsprogs-extra util-linux shadow sudo qemu-guest-agent openssh-server dhcpcd' \
  --copy-in "${CONFIG_DIR}/cloud.cfg:/etc/cloud/" \
  --copy-in "${CONFIG_DIR}/grub:/etc/default/" \
  --mkdir /usr/local/sbin \
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
#
# Bell-Sw publishes Alpaquita Stream as a rolling release at a stable URL
# pointing to "latest" — no redirect, no version-bearing metadata in the
# URL or content-disposition header. We synthesise a date-based version
# from the upstream qcow2.xz Last-Modified HTTP header (YYYY.MM.DD).
# Each new upstream rebuild bumps the date.
set -euo pipefail

URL='https://packages.bell-sw.com/alpaquita/glibc/stream/releases/x86_64/alpaquita-stream-latest-glibc-x86_64.qcow2.xz'

last_mod=$(curl -fsSI "$URL" \
  | awk -F': ' 'tolower($1)=="last-modified"{sub(/\r$/,"",$2); print $2; exit}')

if [[ -z "${last_mod:-}" ]]; then
  echo "::error::could not read Last-Modified header from $URL" >&2
  exit 1
fi

# RFC 7231: "Sat, 11 Apr 2026 07:50:31 GMT"
date -u -d "$last_mod" +'%Y.%m.%d'
```

> **Detection strategies vary per upstream.** Pick whichever maps the
> upstream's release model into a stable, monotonically-increasing
> string:
> - **Versioned releases** (e.g. Rocky 10.1, Alpine 3.22.0): scrape the
>   release index page, extract the highest version.
> - **GitHub releases**: `gh api /repos/<owner>/<repo>/releases/latest --jq .tag_name`
> - **Rolling release with stable URL** (Alpaquita Stream above): synthesise
>   from the `Last-Modified` header → `YYYY.MM.DD`.
> - **Rolling release with dated URL**: follow the redirect from a
>   `-latest-` alias and parse the dated filename.

## Versioning rules

- `VERSION` holds the upstream version verbatim, no `v` prefix. Examples:
  - Numbered release: `3.22.0`
  - Date-stamped (e.g. for rolling-release upstreams): `2026.04.11`
  - Custom build of upstream: `2.0.20240711.0`
- Git tag for a release is `v<VERSION>` (e.g., `v3.22.0`, `v2026.04.11`).
- The `version` input passed to the reusable workflow is `<VERSION>` (no `v`).
  When omitted, the workflow strips the leading `v` from `github.ref_name`.

## Path conventions on the public CDN

Versioned objects are immutable and served with `Cache-Control: max-age=31536000, immutable`.
The `latest/` directory is a snapshot copy of the most recent build; it carries
`max-age=300` and is purged from the Cloudflare edge after each release.

Never link to `latest/` from documentation that needs reproducibility — link to
the versioned path instead.
