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
| [Oracle Linux 8](https://openimages.cloud/images/oracle-linux-8/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Foracle-linux-8%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `cloud-user` | ✅ Stable | [`oracle-linux-8`](https://github.com/open-img-cloud/oracle-linux-8) |
| [Oracle Linux 9](https://openimages.cloud/images/oracle-linux-9/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Foracle-linux-9%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `cloud-user` | ✅ Stable | [`oracle-linux-9`](https://github.com/open-img-cloud/oracle-linux-9) |
| [Oracle Linux 10](https://openimages.cloud/images/oracle-linux-10/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Foracle-linux-10%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `cloud-user` | ✅ Stable | [`oracle-linux-10`](https://github.com/open-img-cloud/oracle-linux-10) |
| [Debian 13](https://openimages.cloud/images/debian-13/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Fdebian-13%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `debian` | ✅ Stable | [`debian-13`](https://github.com/open-img-cloud/debian-13) |
| [Debian 12](https://openimages.cloud/images/debian-12/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Fdebian-12%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `debian` | ✅ Stable | [`debian-12`](https://github.com/open-img-cloud/debian-12) |
| [Ubuntu 26.04 LTS](https://openimages.cloud/images/ubuntu-26.04/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Fubuntu-26.04%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `ubuntu` | ✅ Stable | [`ubuntu-26.04`](https://github.com/open-img-cloud/ubuntu-26.04) |
| [Ubuntu 24.04 LTS](https://openimages.cloud/images/ubuntu-24.04/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Fubuntu-24.04%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `ubuntu` | ✅ Stable | [`ubuntu-24.04`](https://github.com/open-img-cloud/ubuntu-24.04) |
| [Ubuntu 22.04 LTS](https://openimages.cloud/images/ubuntu-22.04/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Fubuntu-22.04%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `ubuntu` | ✅ Stable | [`ubuntu-22.04`](https://github.com/open-img-cloud/ubuntu-22.04) |
| [CentOS Stream 10](https://openimages.cloud/images/centos-stream-10/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Fcentos-stream-10%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `cloud-user` | ✅ Stable | [`centos-stream-10`](https://github.com/open-img-cloud/centos-stream-10) |
| [Rocky Linux 10](https://openimages.cloud/images/rocky-linux-10/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Frocky-linux-10%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `rocky` | ✅ Stable | [`rocky-linux-10`](https://github.com/open-img-cloud/rocky-linux-10) |
| [AlmaLinux 10](https://openimages.cloud/images/almalinux-10/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Falmalinux-10%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `almalinux` | ✅ Stable | [`almalinux-10`](https://github.com/open-img-cloud/almalinux-10) |
| [Rocky Linux 9](https://openimages.cloud/images/rocky-linux-9/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Frocky-linux-9%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `rocky` | ✅ Stable | [`rocky-linux-9`](https://github.com/open-img-cloud/rocky-linux-9) |
| [AlmaLinux 9](https://openimages.cloud/images/almalinux-9/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Falmalinux-9%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `almalinux` | ✅ Stable | [`almalinux-9`](https://github.com/open-img-cloud/almalinux-9) |
| [Rocky Linux 8](https://openimages.cloud/images/rocky-linux-8/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Frocky-linux-8%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `rocky` | ✅ Stable | [`rocky-linux-8`](https://github.com/open-img-cloud/rocky-linux-8) |
| [AlmaLinux 8](https://openimages.cloud/images/almalinux-8/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Falmalinux-8%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `almalinux` | ✅ Stable | [`almalinux-8`](https://github.com/open-img-cloud/almalinux-8) |
| [openSUSE Leap 16](https://openimages.cloud/images/opensuse-leap-16/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Fopensuse-leap-16%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `sles` | ✅ Stable | [`opensuse-leap-16`](https://github.com/open-img-cloud/opensuse-leap-16) |
| [Gentoo Linux](https://openimages.cloud/images/gentoo-linux/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Fgentoo-linux%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `gentoo` | ✅ Stable | [`gentoo-linux`](https://github.com/open-img-cloud/gentoo-linux) |
| [Amazon Linux 2](https://openimages.cloud/images/amazon-linux-2/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Famazon-linux-2%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `ec2-user` | 📦 Archive<sup>1</sup> | [`amazon-linux-2`](https://github.com/open-img-cloud/amazon-linux-2) |

<sup>1</sup> Amazon Linux 2 reached end of life upstream on 2025-06-30. Builds continue for existing workloads; new deployments should target Amazon Linux 2023.

### BSD

| Image | Latest | Variants | Login user | Status | Repository |
|---|---|---|---|---|---|
| [FreeBSD 14](https://openimages.cloud/images/freebsd-14/) | ![latest](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fimages.openimages.cloud%2Ffreebsd-14%2Flatest%2FMANIFEST.json&query=%24.version&label=latest&color=2459c4&cacheSeconds=3600) |  | `freebsd` | ✅ Stable<sup>2</sup> | [`freebsd`](https://github.com/open-img-cloud/freebsd) |

<sup>2</sup> 14.5 is the last FreeBSD 14 release; the 14 branch is supported until 2028-11-30. FreeBSD 15 images are in preparation.

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
| FreeBSD 15 | FreeBSD 15 guests, same build as FreeBSD 14 | [`freebsd`](https://github.com/open-img-cloud/freebsd) |

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
