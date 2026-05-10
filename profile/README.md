![Hero image](https://raw.githubusercontent.com/open-img-cloud/.github/refs/heads/main/profile/img/open-images-logo.png)

**Open Image Cloud** publishes ready-to-use, **cosign-signed**, **reproducible** cloud images for **OpenStack** and **Proxmox**.

- 🌐 **Website** — <https://openimages.cloud>
- 📦 **Image registry** — <https://images.openimages.cloud> (CDN-backed mirror of our self-hosted Garage source-of-truth)
- 📜 **Conventions & contribution guide** — [`CONVENTIONS.md`](https://github.com/open-img-cloud/.github/blob/main/CONVENTIONS.md)

---

## What you get

- 🔁 **Reproducible builds** on GitHub Actions with pinned upstream sources and a tagged builder container; commit, run URL, and builder digest are embedded in every image's `MANIFEST.json`.
- 🔒 **Keyless cosign signatures** via GitHub OIDC — verify any image without managing keys on your side.
- ☁️ **Native cloud-init** for OpenStack (ConfigDrive), Proxmox (NoCloud), and any provider that consumes either.
- 📦 **Versioned & immutable** paths on the public registry: `images.openimages.cloud/<os>/<version>/<filename>`. A mutable `latest/` alias is kept fresh after each release.

---

## Available images

### Linux

| OS                | Latest               | Variants     | Status                | Repository |
|-------------------|----------------------|--------------|-----------------------|------------|
| Alpaquita Linux   | `2026.04.14`         | glibc, musl  | ✅ Stable             | [`alpaquita-linux`](https://github.com/open-img-cloud/alpaquita-linux) |
| Alpine Linux      | `3.23.4`             | BIOS, UEFI   | ✅ Stable             | [`alpine-linux`](https://github.com/open-img-cloud/alpine-linux) |
| Amazon Linux 2    | `2.0.20260508.0`     | —            | 📦 Maintenance only<sup>1</sup> | [`amazon-linux-2`](https://github.com/open-img-cloud/amazon-linux-2) |
| Amazon Linux 2023 | `2023.11.20260509.0` | —            | ✅ Stable             | [`amazon-linux-2023`](https://github.com/open-img-cloud/amazon-linux-2023) |
| Gentoo Linux      | `2026.05.03`         | —            | 🚧 Build pipeline WIP | [`gentoo-linux`](https://github.com/open-img-cloud/gentoo-linux) |
| NixOS             | `25.11`              | —            | ✅ Stable             | [`nixos`](https://github.com/open-img-cloud/nixos) |
| Oracle Linux 9    | `9.7-b269`           | —            | ✅ Stable             | [`oracle-linux-9`](https://github.com/open-img-cloud/oracle-linux-9) |
| Oracle Linux 10   | `10.1-b270`          | —            | ✅ Stable             | [`oracle-linux-10`](https://github.com/open-img-cloud/oracle-linux-10) |

<sup>1</sup> Amazon Linux 2 reached upstream EOL on 2025-06-30. Builds are kept available for extended-support customers; new deployments should target Amazon Linux 2023.

### OpenStack components

| Component       | Latest    | Older releases       | Status     | Repository |
|-----------------|-----------|----------------------|------------|------------|
| Octavia Amphora | `2026.1`  | `2025.2`, `2025.1`   | ✅ Stable  | [`octavia-amphora`](https://github.com/open-img-cloud/octavia-amphora) |

> Octavia images are pinned to the matching OpenStack release; older paths stay immutable on the registry so you can keep targeting the OpenStack release of your existing deployment.

### Windows

| OS                  | Status       | Repository |
|---------------------|--------------|------------|
| Windows Server 2022 | 🚧 Planned   | [`windows-server-2022`](https://github.com/open-img-cloud/windows-server-2022) |

### Special-purpose

| Image          | Purpose                                | Status      | Repository |
|----------------|----------------------------------------|-------------|------------|
| Cloud Rescue   | Bootable rescue / diagnostic image     | 🚧 Planned  | [`cloud-rescue`](https://github.com/open-img-cloud/cloud-rescue) |

> Need an OS that's not on this list? [Open an issue](https://github.com/open-img-cloud/.github/issues) — adoption is driven by demand.

---

## Verify a downloaded image

All images are signed via cosign keyless (GitHub OIDC). Verify before booting:

```bash
# 1. Download the image and its cosign bundle
curl -fLO https://images.openimages.cloud/alpine-linux/3.23.4/alpine-3.23.4-uefi-x86_64.qcow2
curl -fLO https://images.openimages.cloud/alpine-linux/3.23.4/alpine-3.23.4-uefi-x86_64.qcow2.bundle

# 2. Verify the signature
cosign verify-blob alpine-3.23.4-uefi-x86_64.qcow2 \
  --bundle alpine-3.23.4-uefi-x86_64.qcow2.bundle --new-bundle-format \
  --certificate-identity-regexp 'https://github.com/open-img-cloud/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

`Verified OK` means the image was built by a GitHub Actions workflow under the `open-img-cloud` org. Inspect provenance via `MANIFEST.json` next to the image.

---

## How it works

The build pipeline lives in [`open-img-cloud/.github`](https://github.com/open-img-cloud/.github) as a set of **reusable GitHub workflows** plus **composite actions**. Each image repo stays thin: `VERSION`, a `customize.sh` (libguestfs) or `dib-build.sh` (diskimage-builder) hook, a `detect-upstream.sh` watcher, plus two thin caller workflows. See [`CONVENTIONS.md`](https://github.com/open-img-cloud/.github/blob/main/CONVENTIONS.md) for the full contract.

Storage topology: [Garage](https://garagehq.deuxfleurs.fr) (self-hosted S3, source-of-truth) → mirrored to [Cloudflare R2](https://www.cloudflare.com/developer-platform/products/r2/) → served behind the Cloudflare CDN at <https://images.openimages.cloud>. Routing is handled by [`images-router`](https://github.com/open-img-cloud/images-router), a tiny Cloudflare Worker that maps `/<os>/*` to per-distribution buckets.

---

## Licensing

The infrastructure, workflows, and tooling published in this org are released under permissive open-source licenses (Apache-2.0 / MIT depending on the repo — see each repository's `LICENSE` file).

⚠️ **The OS images themselves inherit the licensing terms of their upstream distributions** (Alpine, Amazon Linux, NixOS, Oracle Linux, etc.). Review the original licenses before using any image in production.

---

## Contribute

PRs and issues are welcome — whether to add a new distribution, propose an architecture (arm64, riscv64), report a security issue, or improve the build pipeline. Start with [`CONVENTIONS.md`](https://github.com/open-img-cloud/.github/blob/main/CONVENTIONS.md) if you want to add a new image repo.

---

**Build once. Verify everywhere. Deploy anywhere.**
