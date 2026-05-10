# openimages.cloud — Image catalog standards

This document defines the requirements an image must satisfy to live in
the openimages.cloud catalog. Reference for new onboardings, audits,
and the auto-validation CI step (see [`actions/validate-image`][1]).

Every catalog repo MUST satisfy A–F. SHOULD satisfy G–J. Deviations are
acceptable when documented in the repo's README at the top, with a
date and rationale.

[1]: ../actions/validate-image/

---

## A — Provenance & signing (MUST)

- **Cosign keyless** signature using sigstore-bundle format
  (`--new-bundle-format`). Bundle filename: `<artifact>.bundle`,
  alongside the artifact in the same R2/Garage path.
- **Certificate identity regex** points to the reusable workflow that
  produced the signature, not the caller repo. Currently:
  `^https://github.com/open-img-cloud/\.github/\.github/workflows/build-(libguestfs|dib|nix-flake)-image\.yml@`.
  When a new build engine is added, update this regex AND
  every consumer README.
- **`MANIFEST.json`** alongside the artifact, with at minimum:

  ```jsonc
  {
    "name":         "<repo slug>",
    "version":      "<resolved version>",
    "variant":      "<bios|uefi|glibc|musl|null>",
    "format":       "qcow2",
    "filename":     "<artifact filename>",
    "sha256":       "<hex>",
    "upstream_url": "<url of the upstream we built from, when applicable>",
    "built_at":     "<ISO 8601 UTC>",
    "commit":       "<caller repo SHA>",
    "build_url":    "<https://github.com/.../actions/runs/N>",
    "builder_tool": "<libguestfs|diskimage-builder|nix-flake>",
    "builder":      { "image": "<oci ref>", "digest": "<sha256:…>" },
    "signed":       true,
    "bundle":       "<bundle filename>"
  }
  ```

- The reusable workflow MUST be cosign-signed too (verified by the
  `verify-builder` job before any caller code runs), unless the
  caller explicitly sets `verify_builder: false` and documents why
  in its `release.yml`.

## B — Distribution (MUST)

- **Per-distro Garage bucket** (source of truth) named `<repo slug>`,
  e.g. `alpine-linux`. Hosted on the openimages.cloud Garage cluster.
- **Per-distro R2 bucket** (Cloudflare-fronted CDN) with the same name
  as the Garage bucket. Garage→R2 sync runs in the publish step of
  the reusable workflow.
- **Worker `images-router` binding** active. The bucket name MUST be
  in `ALLOWED_BUCKETS` AND a matching `[[r2_buckets]]` block MUST
  exist in `wrangler.toml`. Binding name = `uppercase(<slug>) with -
  → _` (e.g. `alpine-linux` → `ALPINE_LINUX`).
- **URL pattern**:
  - Versioned: `https://images.openimages.cloud/<slug>/<version>/<filename>`
    — `Cache-Control: public, max-age=31536000, immutable`.
  - Latest alias: `https://images.openimages.cloud/<slug>/latest/<filename>`
    — `Cache-Control: public, max-age=300`.
- **Index HTML** auto-generated at the bucket prefix (`/index.html`)
  showing all files, sizes, and verification snippet.

## C — Image content for cloud-init-based distros (MUST)

- `cloud-init` ≥ 24.x installed and enabled at boot.
- The reusable libguestfs workflow auto-injects the org-wide drop-in
  `/etc/cloud/cloud.cfg.d/99_oic-policy.cfg` containing:
  ```yaml
  datasource_list: ['OpenStack', 'ConfigDrive', 'NoCloud', 'None']
  disable_root: true
  ssh_pwauth: false
  preserve_hostname: false
  mount_default_fields: [~, ~, 'auto', 'defaults,nofail', '0', '2']
  ```
  Callers MUST NOT ship a full-replacement `/etc/cloud/cloud.cfg`
  that overrides those keys. Distro-specific overrides go in a
  caller-shipped `99_oic-distro.cfg` (system_info / default_user
  only).
- **Default user** with passwordless sudo via the `wheel` group, key
  authentication only, `lock_passwd: false` (with `plain_text_passwd`
  workaround on Alpine/Alpaquita per
  [`smoke_phase_a_tcp_not_banner.md`](memory)).
- **SSH server** (`openssh-server`) installed, `sshd` enabled in the
  default boot runlevel, `PermitEmptyPasswords no`,
  `PasswordAuthentication no`, `PermitRootLogin no` (or
  `prohibit-password` minimum).
- **Serial console** wired to `ttyS0,115200n8` in the kernel cmdline +
  bootloader config.
- **`qemu-guest-agent`** installed and enabled at boot, when available
  for the distro's package manager (drop with documented reason
  otherwise; AL2023 / OL9 / OL10 currently skipped pending package
  resolution).
- **Hostname** controllable via cloud metadata (no hardcoded value).

## D — Image content for non-cloud-init distros (MUST when applicable)

- NixOS / FreeBSD don't ship cloud-init. They MUST provide an
  equivalent metadata fetcher that:
  1. Reads OpenStack metadata from `169.254.169.254` (HTTP) AND/OR a
     ConfigDrive (`vfat label config-2`).
  2. Sets the hostname.
  3. Adds the SSH public key to the default user's `authorized_keys`.
- Default user, SSH server, serial console, and root-login policy
  same as section C.

## E — Format & sidecars (MUST)

- **`qcow2`** sparse + compressed. Output of `virt-sparsify --compress`
  for libguestfs path; `qcow2-compressed` format for nix-flake or DIB
  path.
- **`x86_64`** at minimum. ARM64 is a roadmap target — see
  [Onboarding roadmap](../README.md).
- **Sidecars per artifact** in the same path:
  - `<artifact>.md5`
  - `<artifact>.sha1`
  - `<artifact>.sha256`
  - `<artifact>.bundle` (cosign sigstore-bundle)
- **`MANIFEST.json`** at the version-prefix root, applies to all
  artifacts in the same version directory.
- **`SHA256SUMS`** (multi-file) when a version directory ships >1
  artifact (variants / firmware / arch).

## F — Repository structure (MUST)

```
<repo>/
├── VERSION              # single line, parseable by release.yml
├── README.md            # see template in oic-github/templates/README.md
├── LICENSE              # GPL-2.0
├── .gitignore           # at minimum: !/build/
├── .github/workflows/
│   ├── release.yml      # tag-push trigger, calls a reusable workflow
│   └── watch.yml        # daily cron, calls upstream-watch.yml
└── build/
    ├── customize.sh     # libguestfs path
    │   OR dib-build.sh  # DIB path
    │   OR nix-build.sh  # Nix flake path
    ├── detect-upstream.sh
    └── config/          # optional, for distro-specific drop-ins
```

The release.yml MUST call one of the three approved reusables:
`build-libguestfs-image.yml`, `build-dib-image.yml`,
`build-nix-flake-image.yml`. Adding a new reusable requires updating
this document AND the cert-identity regex in section A.

## G — Operations (SHOULD)

- **`watch.yml` cron** at a unique HH:MM minute per repo to spread
  load on the runner pool. Current allocations: alpaquita 06:17,
  alpine 06:23, AL2023 06:29, AL2 06:35, OL9 06:41, OL10 06:47,
  gentoo 06:53, nixos 06:59. Pick a free `:NN` for new repos.
- **`detect-upstream.sh`** prints the latest upstream version on
  stdout (single line, no extra output) and exits 0. Failures (no
  reachable upstream, parse error) exit non-zero with `::error::`.
- The watch flow opens / updates a single PR named
  `auto/upstream-bump` with the new VERSION value.
- **Tag push** (`v<VERSION>`) triggers the publish path
  (`publish: true`). `workflow_dispatch` defaults to
  `publish: false` (dry-run).

## H — Image size (SHOULD)

- Target: ≤ 1.5× the upstream image OR ≤ 1 GB, whichever is lower.
- Justify exceptions in the README at the top, with the levers we
  considered (e.g. NixOS docs/locales/copyChannel before publish).
- Catalog reference sizes (2026-05):
  - alpine: 95 MB / alpaquita: 175 MB / AL2: 540 MB / AL2023: 542 MB
  - octavia: 365 MB / OL9: 754 MB / OL10: 1024 MB / nixos: 600-800 MB

## I — Lifecycle (SHOULD)

- **Active**: distro is supported by upstream. README + repo
  description plain.
- **Archive**: 📦 prefix in repo description, EOL banner at top of
  README, repository topic `archive`. Continued builds for
  extended-support customers are OK; new deployments redirected to
  the live successor.
- **Known issue**: ⚠️ banner at the top of the README with a date
  and a link to the tracking issue. Build workflow MAY remain on
  but produce no green release until the issue is addressed.

## J — Validation (SHOULD)

- The reusable workflow's smoke step is **mandatory for libguestfs**
  (boot the qcow2 in qemu, ConfigDrive seed with cloud-init user-data,
  SSH+marker check). Failure blocks publish.
- DIB and Nix paths don't have an in-workflow smoke (control plane
  components / custom init mechanisms). Operators verify post-deploy.
- **Post-publish CI auto-validation** (see
  [`actions/validate-image/`][1]) runs on every tag-push release and
  re-checks: MANIFEST keys, cosign verify-blob, sidecar files
  present, qcow2 size threshold, CDN cache headers. Failure marks
  the release as broken in the repo's status badge.
- **Periodic catalog audit** (a scheduled cross-org workflow) runs
  weekly and re-validates every active repo's `latest/` artifact
  against the same checklist.
