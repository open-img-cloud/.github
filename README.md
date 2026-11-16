<p align="center">
  <a href="https://openimages.cloud">
    <img src="https://openimages.cloud/img/og.png" alt="Open Image Cloud: signed, boot-tested cloud images for OpenStack and Proxmox" width="720">
  </a>
</p>

<p align="center">
  <a href="https://openimages.cloud/images/"><b>Catalog</b></a> ·
  <a href="https://openimages.cloud/docs/">Documentation</a> ·
  <a href="https://openimages.cloud/oic-sync/">oic-sync</a> ·
  <a href="https://openimages.cloud/verify/">Verify an image</a> ·
  <a href="https://github.com/open-img-cloud/.github/issues">Request an image</a>
</p>

# Open Image Cloud

Ready-to-use qcow2 cloud images for **OpenStack** and **Proxmox VE**, built in the open from
the official images of each distribution, **signed** with Sigstore cosign and **boot-tested on a
real OpenStack** before every release.

⭐ **If these images save you time, star this repository**: it is the home of the project, and
stars are how other operators find it.

## Why

Every cloud operator ends up rebuilding the same images: download the upstream one, add the
guest agent, fix cloud-init, set the Glance properties, check that it boots, repeat at every
upstream release. Open Image Cloud does that once, in public, for everyone:

- **30+ images**: AlmaLinux, Alpine, Amazon Linux, Arch, CentOS Stream, Debian, Fedora, FreeBSD,
  Gentoo, NixOS, openSUSE, Oracle Linux, Rocky Linux, Ubuntu, plus OpenStack service images
  (Octavia amphora, Manila, Trove), a rescue image and CirrOS;
- **always current**: a daily watcher follows each upstream, a merge publishes the new version;
- **verifiable**: keyless cosign signatures bound to these build workflows, digests and
  provenance in every `MANIFEST.json`;
- **tested where it runs**: SSH with the injected key, cloud-init, DNS, IPv6, root filesystem
  growth and guest agent on a live OpenStack, for every release.

## Use it

```sh
# OpenStack Glance or Proxmox VE templates, kept up to date (pipx, .deb, .rpm or container)
pipx install 'oic-sync[openstack]'
oic-sync openstack sync --cloud mycloud --image debian-13 --image ubuntu-24.04

# Or download an image directly
M=https://images.openimages.cloud/debian-13/latest/MANIFEST.json
F=$(curl -fsS $M | jq -r .filename); V=$(curl -fsS $M | jq -r .version)
curl -fLO https://images.openimages.cloud/debian-13/$V/$F
```

Per-image commands (OpenStack properties, Proxmox `qm` template) are on each
[catalog page](https://openimages.cloud/images/).

## What is in this repository

The shared pipeline every image repository calls: reusable build workflows (libguestfs,
diskimage-builder, Nix flake, FreeBSD), the composite actions that sign, publish and boot-test,
the cloud-init policy, the [`CONVENTIONS.md`](CONVENTIONS.md) and the
[image standards](docs/IMAGE_STANDARDS.md). Each image lives in its own repository, listed on
the [organisation page](https://github.com/open-img-cloud).

## Contribute

A new distribution, another architecture, a bug in an image, a security report: issues and pull
requests are welcome. Start with [`CONVENTIONS.md`](CONVENTIONS.md); security reports go through
[`SECURITY.md`](SECURITY.md).

## License

Pipeline and tooling under [GPL-2.0](LICENSE). The images keep the licensing terms of their
upstream distributions.
