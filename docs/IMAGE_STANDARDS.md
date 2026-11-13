# openimages.cloud: Image catalog standards

This document defines the requirements an image must satisfy to live in
the openimages.cloud catalog. Reference for new onboardings, audits,
and the auto-validation CI step (see [`actions/validate-image`][1]).

Every catalog repo MUST satisfy A–F. SHOULD satisfy G–J. Deviations are
acceptable when documented in the repo's README at the top, with a
date and rationale.

[1]: ../actions/validate-image/

---

## A. Provenance & signing (MUST)

- **Cosign keyless** signature using sigstore-bundle format
  (`--new-bundle-format`). Bundle filename: `<artifact>.bundle`,
  alongside the artifact in the same bucket path.
- **Certificate identity regex** points to the reusable workflow that
  produced the signature, not the caller repo. Currently:
  `^https://github.com/open-img-cloud/\.github/\.github/workflows/build-(libguestfs|dib|nix-flake|freebsd)-image\.yml@`.
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

## B. Distribution (MUST)

- **Per-distro public bucket** on Infomaniak Object Storage (Ceph S3,
  Public Cloud project `Images_Storage`, region `dc4-a`) named
  `<repo slug>`, e.g. `alpine-linux`. Single source of truth, with
  versioning enabled (non-current versions kept 30 days).
- **Worker `images-router` route** active: the bucket name MUST be in
  `ALLOWED_BUCKETS` in `wrangler.toml`.
- **URL pattern**:
  - Versioned: `https://images.openimages.cloud/<slug>/<version>/<filename>`,
    with `Cache-Control: public, max-age=31536000, immutable`.
  - Latest alias: `https://images.openimages.cloud/<slug>/latest/<filename>`,
    with `Cache-Control: public, max-age=300`.
- **Index HTML** auto-generated in each version directory and in
  `latest/` (`index.html`), showing all files, sizes, and verification
  snippet. The bucket root (`/<slug>/`) has no index: the router
  redirects it to `/<slug>/latest/`; `versions.json` lists the versions.

## C. Image content for cloud-init-based distros (MUST)

- `cloud-init` ≥ 24.x installed and enabled at boot.
- The reusable libguestfs workflow auto-injects the org-wide drop-in
  `/etc/cloud/cloud.cfg.d/99_oic-policy.cfg` containing:
  ```yaml
  datasource_list: ['ConfigDrive', 'OpenStack', 'NoCloud', 'None']
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

## D. Image content for non-cloud-init distros (MUST when applicable)

- Every catalog image ships cloud-init today, NixOS (nixpkgs
  `services.cloud-init`) and FreeBSD (`net/cloud-init`) included, with the
  catalog datasource order (ConfigDrive first). This section applies to a
  future image that cannot run cloud-init: it MUST provide an equivalent
  metadata fetcher that:
  1. Reads OpenStack metadata from `169.254.169.254` (HTTP) AND/OR a
     ConfigDrive (`vfat label config-2`).
  2. Sets the hostname.
  3. Adds the SSH public key to the default user's `authorized_keys`.
- Default user, SSH server, serial console, and root-login policy
  same as section C.

## E. Format & sidecars (MUST)

- **`qcow2`** sparse + compressed. Output of `virt-sparsify --compress`
  for libguestfs path; `qcow2-compressed` format for nix-flake or DIB
  path.
- **`x86_64`** at minimum. ARM64 is a roadmap target: see
  [Onboarding roadmap](../README.md).
- **Sidecars per artifact** in the same path:
  - `<artifact>.md5`
  - `<artifact>.sha1`
  - `<artifact>.sha256`
  - `<artifact>.bundle` (cosign sigstore-bundle)
- **`MANIFEST.json`** at the version-prefix root, applies to all
  artifacts in the same version directory (`MANIFEST-<variant>.json`
  per variant). Besides the build provenance, `publish-image` adds the
  machine fields used by importers (Glance, Proxmox, `index.json`):
  `sha512`, `size`, `virtual_size` (from the qcow2 header), `firmware`
  (`uefi` when the filename says so, else `bios`) and `arch`.
- **`versions.json`** at the bucket root (schema `oic-versions/v1`):
  every published version with its artifacts, rebuilt by
  `publish-image` from the bucket contents on each release, served with
  the mutable 5 min TTL. Clients use it to list, pin and roll back.
- **`SHA256SUMS`** (multi-file) when a version directory ships >1
  artifact (variants / firmware / arch).

## F. Repository structure (MUST)

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

The release.yml MUST call one of the four approved reusables:
`build-libguestfs-image.yml`, `build-dib-image.yml`,
`build-nix-flake-image.yml`, `build-freebsd-image.yml` (FreeBSD-hosted
builds in an ephemeral FreeBSD VM: FreeBSD, later OPNsense). Adding a new reusable requires updating
this document AND the cert-identity regex in section A.

## G. Operations (SHOULD)

- **`watch.yml` cron** at a unique HH:MM minute per repo to spread
  load on the runner pool. Current allocations: rocky8 06:02, rocky9 06:05,
  rocky10 06:08, OL8 06:11, alma9 06:14, alpaquita 06:17, alma8 06:20,
  alpine 06:23, alma10 06:26, AL2023 06:29, debian12 06:32, AL2 06:35,
  debian13 06:38, OL9 06:41, ubuntu22.04 06:44, OL10 06:47, ubuntu24.04 06:50,
  gentoo 06:53, ubuntu26.04 06:56, nixos 06:59. Pick a free `:NN` for new repos.
- **`detect-upstream.sh`** prints the latest upstream version on
  stdout (single line, no extra output) and exits 0. Failures (no
  reachable upstream, parse error) exit non-zero with `::error::`.
- The watch flow opens / updates a single PR named
  `auto/upstream-bump` with the new VERSION value.
- **Tag push** (`v<VERSION>`) triggers the publish path
  (`publish: true`). `workflow_dispatch` defaults to
  `publish: false` (dry-run).

## H. Image size (SHOULD)

- Target: ≤ 1.5× the upstream image OR ≤ 1 GB, whichever is lower.
- Justify exceptions in the README at the top, with the levers we
  considered (e.g. NixOS docs/locales/copyChannel before publish).
- Catalog reference sizes (2026-05):
  - alpine: 95 MB / alpaquita: 175 MB / AL2: 540 MB / AL2023: 542 MB
  - octavia: 365 MB / OL9: 754 MB / OL10: 1024 MB / nixos: 600-800 MB

## I. Lifecycle (SHOULD)

- **Active**: distro is supported by upstream. README + repo
  description plain.
- **Archive**: 📦 prefix in repo description, EOL banner at top of
  README, repository topic `archive`. Continued builds for
  extended-support customers are OK; new deployments redirected to
  the live successor.
- **Known issue**: ⚠️ banner at the top of the README with a date
  and a link to the tracking issue. Build workflow MAY remain on
  but produce no green release until the issue is addressed.

## J. Validation (SHOULD)

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
- **Weekly catalog audit** (`.github/workflows/catalog-audit.yml`,
  dispatched every Monday by the images-router cron) re-validates the
  `latest/` artefact of every catalog entry and variant with the same
  checks, and opens a single "Catalog audit" issue on failure.

## K. Runtime smoke on a live OpenStack (MUST)

Static artefact validation (section J) confirms an image is well-formed
and signed; it does not prove that it actually boots or behaves like a
cloud image. The post-publish runtime smoke closes that loop.

- The reusable workflow's `runtime_smoke` step (composite action
  [`actions/smoke-openstack/`][2]) imports the just-published qcow2 into
  Infomaniak Public Cloud (one of `dc3-a`, `dc4-a` at random; `regions`
  input), boots a throwaway instance on `ext-net1` (public IPv4 and
  IPv6, floating IP only when needed), SSHes in as the distro's default
  user with an injected key, and checks the **image contract**. Every
  check is required (inputs `strict` and `require_ipv6` default to
  true):
  - SSH with the injected key as the documented default user;
  - cloud-init finished without error (status, warnings and tracebacks
    printed on failure);
  - DNS resolution inside the guest;
  - sshd does not offer password authentication (keyboard-interactive
    is reported);
  - hostname taken from the metadata;
  - root partition and filesystem (or ZFS pool) grown to the flavor
    disk (at least 80%);
  - passwordless root for the default user (sudo or doas);
  - qemu-guest-agent running (the image is registered with
    `hw_qemu_guest_agent=yes`; the catalog advertises quiesced snapshots);
  - the global IPv6 address Neutron assigned to the port is configured,
    and the guest reaches the IPv6 Internet.
- Timeouts absorb slow DHCP (over 2 minutes measured in `dc4-a`): SSH 7
  minutes, IPv6 address 4 minutes, DNS and IPv6 egress 2 minutes.
- Images with a non-POSIX login shell must set a POSIX shell for the
  default user (FreeBSD: `/bin/sh`); contract commands get `/sbin` and
  `/usr/sbin` in `PATH`.
- `user_data` (diagnostic boots) passes a cloud-config to the instance
  and prints its console at the end.
- Required org-wide secrets: `OS_AUTH_URL`, `OS_REGION_NAME`,
  `OS_APPLICATION_CREDENTIAL_ID`, `OS_APPLICATION_CREDENTIAL_SECRET`.
- Each caller workflow MUST set `runtime_smoke_login_user`. Images that
  are not general-purpose VMs (Octavia amphora, Manila service image)
  leave it empty and document a dedicated test.
- **Test images** (CirrOS) republish the upstream file unchanged
  (`passthrough: true`: no customization, no sysprep, no sparsify, the
  published SHA-256 must equal the upstream one) and are checked against
  `contract: minimal`: SSH with the key injected by the image's own
  metadata client as `runtime_smoke_login_user`, DNS, hostname, root
  growth, passwordless sudo and IPv6 stay required; the cloud-init and
  qemu-guest-agent checks are skipped, and an sshd offering passwords is
  only reported (well-known password by design). Such images are not
  general-purpose: sections C and D do not apply, their README says so at
  the top, and `oic-sync` skips them unless they are named.
- Failure blocks the release run; cleanup always runs.

[2]: ../actions/smoke-openstack/
