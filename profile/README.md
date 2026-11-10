![Open Image Cloud](https://raw.githubusercontent.com/open-img-cloud/.github/refs/heads/main/profile/img/open-images-logo.png)

**Open Image Cloud** publishes ready-to-use, **signed**, **reproducible** cloud images for **OpenStack** and **Proxmox**, built in the open from official upstream releases.

- 🌐 **Website and catalog**: <https://openimages.cloud>
- 📦 **Image registry**: <https://images.openimages.cloud> (Swiss-hosted Infomaniak Object Storage behind the Cloudflare CDN)
- 🔐 **Verification guide**: <https://openimages.cloud/verify/>
- 📜 **Conventions and image standards**: [`CONVENTIONS.md`](https://github.com/open-img-cloud/.github/blob/main/CONVENTIONS.md), [`IMAGE_STANDARDS.md`](https://github.com/open-img-cloud/.github/blob/main/docs/IMAGE_STANDARDS.md)

---

## What you get

- 🔁 **Reproducible builds** in public GitHub Actions workflows, from pinned upstream artefacts and a signed builder container. Commit, CI run and builder digest are recorded in every image's `MANIFEST.json`.
- 🧪 **Boot-tested twice** before and after publishing: in QEMU with a ConfigDrive, then on a live OpenStack (cloud-init, SSH and DNS must pass).
- 🔒 **Keyless cosign signatures** bound to the identity of our build workflows and logged in Sigstore's Rekor: nothing to manage on your side.
- ☁️ **One cloud-init policy** for every distribution: OpenStack (ConfigDrive), Proxmox (NoCloud) and any provider that speaks either.
- 📌 **Versioned, immutable paths**: `images.openimages.cloud/<os>/<version>/<file>`, plus a `latest/` alias refreshed on each release.

---

## Available images

Versions below are read live from each image's published manifest.

### Linux

| Image | Latest | Variants | Login user | Status | Repository |
|---|---|---|---|---|---|
| [Alpaquita Linux](https://openimages.cloud/images/alpaquita-linux/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Falpaquita-linux%2Flatest%2FMANIFEST-glibc.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) | glibc, musl | `alpaquita` | ✅ Stable | [`alpaquita-linux`](https://github.com/open-img-cloud/alpaquita-linux) |
| [Alpine Linux](https://openimages.cloud/images/alpine-linux/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Falpine-linux%2Flatest%2FMANIFEST-uefi.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) | BIOS, UEFI | `alpine` | ✅ Stable | [`alpine-linux`](https://github.com/open-img-cloud/alpine-linux) |
| [Amazon Linux 2023](https://openimages.cloud/images/amazon-linux-2023/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Famazon-linux-2023%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `ec2-user` | ✅ Stable | [`amazon-linux-2023`](https://github.com/open-img-cloud/amazon-linux-2023) |
| [NixOS](https://openimages.cloud/images/nixos/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Fnixos%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `nixos` | ✅ Stable | [`nixos`](https://github.com/open-img-cloud/nixos) |
| [Oracle Linux 9](https://openimages.cloud/images/oracle-linux-9/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Foracle-linux-9%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `cloud-user` | ✅ Stable | [`oracle-linux-9`](https://github.com/open-img-cloud/oracle-linux-9) |
| [Oracle Linux 10](https://openimages.cloud/images/oracle-linux-10/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Foracle-linux-10%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `cloud-user` | ✅ Stable | [`oracle-linux-10`](https://github.com/open-img-cloud/oracle-linux-10) |
| [Amazon Linux 2](https://openimages.cloud/images/amazon-linux-2/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Famazon-linux-2%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `ec2-user` | 📦 Archive<sup>1</sup> | [`amazon-linux-2`](https://github.com/open-img-cloud/amazon-linux-2) |
| Gentoo Linux | not published yet | | | 🚧 Build pipeline WIP | [`gentoo-linux`](https://github.com/open-img-cloud/gentoo-linux) |

<sup>1</sup> Amazon Linux 2 reached end of life upstream on 2025-06-30. Builds continue for existing workloads; new deployments should target Amazon Linux 2023.

### OpenStack components

| Component | Releases | Status | Repository |
|---|---|---|---|
| [Octavia Amphora](https://openimages.cloud/images/octavia-amphora/) | `2026.1`, `2025.2`, `2025.1` | ✅ Stable | [`octavia-amphora`](https://github.com/open-img-cloud/octavia-amphora) |

> Amphora images follow the OpenStack release series. Older series stay at their immutable paths, so you can keep matching the release of your deployment.

### In preparation

| Image | Purpose | Repository |
|---|---|---|
| Windows Server 2022 | Windows guests with cloudbase-init | [`windows-server-2022`](https://github.com/open-img-cloud/windows-server-2022) |
| Cloud Rescue | Bootable rescue and diagnostic image | [`cloud-rescue`](https://github.com/open-img-cloud/cloud-rescue) |
| FreeBSD | FreeBSD guests for OpenStack | [`freebsd`](https://github.com/open-img-cloud/freebsd) |

> Need another distribution? [Open an issue](https://github.com/open-img-cloud/.github/issues): new images are added on demand.

---

## Verify a downloaded image

```bash
curl -fLO https://images.openimages.cloud/alpine-linux/3.24.1/alpine-3.24.1-uefi-x86_64.qcow2
curl -fLO https://images.openimages.cloud/alpine-linux/3.24.1/alpine-3.24.1-uefi-x86_64.qcow2.bundle

cosign verify-blob alpine-3.24.1-uefi-x86_64.qcow2 \
  --bundle alpine-3.24.1-uefi-x86_64.qcow2.bundle --new-bundle-format \
  --certificate-identity-regexp '^https://github.com/open-img-cloud/\.github/\.github/workflows/build-(libguestfs|dib|nix-flake)-image\.yml@' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

`Verified OK` means the file was produced, unmodified, by one of our reusable build workflows. The [verification guide](https://openimages.cloud/verify/) also covers checksums and reading the provenance manifest.

---

## How it works

Everything runs from this repository: **reusable workflows** and **composite actions** shared by every image repo. An image repo stays thin: a pinned `VERSION`, one build hook and an upstream watcher. Three build engines cover the catalog:

| Engine | Used for | Hook |
|---|---|---|
| libguestfs | Customising official upstream cloud images | `build/customize.sh` |
| diskimage-builder | Images assembled from scratch (Octavia, Gentoo) | `build/dib-build.sh` |
| Nix flake | NixOS, through the native NixOS image framework | `build/nix-build.sh` |

A daily watcher opens a pull request when upstream ships a new version. A tag on the merged version builds, boot-tests, signs and publishes the image. Builds run on GitHub-hosted runners with KVM.

Storage: [Infomaniak Object Storage](https://www.infomaniak.com/en/hosting/public-cloud/object-storage) in Switzerland is the single source of truth, served through the Cloudflare CDN by [`images-router`](https://github.com/open-img-cloud/images-router). The website lives in [`oic-website`](https://github.com/open-img-cloud/oic-website).

---

## Licensing

Image repositories are released under **GPL-2.0** (GPL-3.0 for `freebsd`), the website under **Apache-2.0**. See each repository's `LICENSE`.

⚠️ **The OS images themselves keep the licensing terms of their upstream distributions** (Alpine, Amazon Linux, NixOS, Oracle Linux…). Review them before production use.

---

## Contribute

Issues and pull requests are welcome: a new distribution, another architecture (arm64, riscv64), a security report or a pipeline improvement. To add an image repo, start with [`CONVENTIONS.md`](https://github.com/open-img-cloud/.github/blob/main/CONVENTIONS.md).

---

**Build once. Verify everywhere. Deploy anywhere.**
