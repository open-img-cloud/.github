# Self-hosted Rocky 10 runners — provisioning runbook

The reusable workflows in this repo (`build-libguestfs-image.yml`,
`build-dib-image.yml`) run on **self-hosted Rocky Linux 10 runners with
nested virtualization enabled** (`/dev/kvm` exposed to the runner user).
This document describes how to provision such a runner from scratch.

> **Why self-hosted, not GitHub-hosted?**
> Image builds invoke `libguestfs` / `qemu-kvm`, which spawn an appliance VM
> at runtime. Without `/dev/kvm`, the appliance falls back to TCG software
> emulation — 10–50× slower, and unreliable for builds taking >5 minutes.
> GitHub-hosted runners do not expose `/dev/kvm`. The builder image
> (`ghcr.io/stackopshq/libguestfs-tools`) itself is built on GitHub-hosted
> runners (no nested virt needed for the build of the builder), so this
> infrastructure is only needed for the **OS image builds** that consume it.

## Prerequisites on the host

Hardware / hypervisor:
- A physical machine with VT-x/AMD-V, **or** a VM whose hypervisor exposes
  nested virtualization to the guest. Verify on the guest with:
  ```sh
  lscpu | grep -E 'Virtualization|Hypervisor'   # must show vmx/svm
  cat /sys/module/kvm_intel/parameters/nested    # or kvm_amd, expect "Y" or "1"
  ```
- ≥ 4 vCPU, ≥ 8 GB RAM, ≥ 50 GB free disk recommended (libguestfs appliance
  default `LIBGUESTFS_MEMSIZE=4096` + base rootfs + sparsify scratch).

OS:
- **Rocky Linux 10** (or RHEL/AlmaLinux 10 — same package layout).
- SELinux in **Enforcing** mode (do not disable).

## 1. System packages

```sh
sudo dnf -y update
sudo dnf -y install \
    podman \
    qemu-kvm \
    libvirt-daemon-driver-qemu \
    jq \
    curl \
    tar \
    git \
    policycoreutils-python-utils
```

> `qemu-kvm` and `libvirt-daemon-driver-qemu` are needed on the **host** so
> `/dev/kvm` exists and is accessible. The builder container brings its own
> userspace tools (`qemu-img`, `virt-customize`, …) — but the kernel-side
> KVM module lives on the host.

Verify KVM is loaded:

```sh
lsmod | grep -E 'kvm_intel|kvm_amd'
ls -l /dev/kvm
# expected: crw-rw---- 1 root kvm 10, 232 ... /dev/kvm
```

## 2. Dedicated runner user

Create a system user that owns the runner. Keep it **non-root**.

```sh
sudo useradd --system --create-home --home-dir /var/lib/gh-runner --shell /bin/bash gh-runner
sudo usermod -aG kvm gh-runner   # grants /dev/kvm access
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 gh-runner  # rootless podman (see §3.2)
```

Verify:

```sh
sudo -u gh-runner stat -c '%A %G' /dev/kvm   # expect "crw-rw----" and "kvm"
sudo -u gh-runner test -r /dev/kvm && echo OK
grep '^gh-runner:' /etc/subuid /etc/subgid
```

## 3. SELinux

The runner will spawn rootless podman containers and pass `/dev/kvm` to them.
On Rocky 10 SELinux Enforcing this works out of the box for `--device=/dev/kvm`,
but **two non-obvious adjustments are required** before the runner systemd
service can start. Both are already encoded in the bootstrap below; this
section documents *why*.

### 3.1 Relabel runner executables to `bin_t`

systemd refuses to `exec` files labeled `var_lib_t` even when the file is
owned by the unit's `User=` and has mode `755`. The failure shows up as:

```
status=203/EXEC ... Unable to locate executable '/var/lib/gh-runner/runsvc.sh': Permission denied
```

with **no AVC entry in the audit log** (the denial happens before the
audit hook fires, even with `semodule -DB`). The fix is to label the
runner's entry-point scripts and bundled Node interpreter as `bin_t`,
which systemd treats as a legitimate exec target.

Apply persistently so `restorecon` doesn't undo it:

```sh
for spec in \
    '/var/lib/gh-runner/runsvc\.sh' \
    '/var/lib/gh-runner/run\.sh' \
    '/var/lib/gh-runner/run-helper\.sh' \
    '/var/lib/gh-runner/externals/node[0-9]+/bin(/.*)?'; do
  sudo semanage fcontext -a -t bin_t "$spec" 2>/dev/null || \
  sudo semanage fcontext -m -t bin_t "$spec"
done
sudo restorecon -RFv \
    /var/lib/gh-runner/runsvc.sh \
    /var/lib/gh-runner/run.sh \
    /var/lib/gh-runner/run-helper.sh \
    /var/lib/gh-runner/externals/
```

Note the `node[0-9]+` regex: actions-runner self-updates and may bump the
bundled Node major (currently `node20`); the regex covers future bumps.

### 3.2 Subuid / subgid for rootless podman

System users created via `useradd --system` do not get entries in
`/etc/subuid` and `/etc/subgid` by default. Without them, rootless podman
fails at user namespace setup with:

```
no subuid ranges found for user "gh-runner"
```

Allocate a 64K range:

```sh
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 gh-runner
```

If you have multiple non-root users running rootless podman on the same
host, allocate non-overlapping ranges (e.g. `100000-165535`,
`200000-265535`, …).

### 3.3 Workspace bind mounts

If the consumer workflow bind-mounts the runner workspace into a container
and you see AVC denials on `/var/lib/gh-runner/_work/`:

```sh
sudo restorecon -Rv /var/lib/gh-runner
```

For persistent labelling of a custom workdir:

```sh
sudo semanage fcontext -a -t container_file_t '/var/lib/gh-runner/_work(/.*)?'
sudo restorecon -Rv /var/lib/gh-runner/_work
```

> **Never** propose `setenforce 0` as a fix. Always trace AVCs with
> `sudo ausearch -m AVC -ts recent` and adjust contexts/booleans.

## 4. Install the GitHub Actions runner

Get the latest runner version from
<https://github.com/actions/runner/releases>. Replace `RUNNER_VERSION` below.

```sh
RUNNER_VERSION=2.321.0
ARCH=$(uname -m)
case "$ARCH" in
  x86_64)  RUNNER_ARCH=x64    ;;
  aarch64) RUNNER_ARCH=arm64  ;;
  *) echo "unsupported arch: $ARCH" && exit 1 ;;
esac

cd /var/lib/gh-runner
sudo -u gh-runner curl -fL -o actions-runner.tar.gz \
    "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"
sudo -u gh-runner tar xzf actions-runner.tar.gz
sudo -u gh-runner rm actions-runner.tar.gz
```

## 5. Register the runner against the `open-img-cloud` org

Generate a registration token from the org (read-only API, expires in 1h):

- UI: <https://github.com/organizations/open-img-cloud/settings/actions/runners/new>
- CLI (requires `admin:org` scope on `gh auth`):
  ```sh
  gh api -X POST /orgs/open-img-cloud/actions/runners/registration-token --jq .token
  ```

Configure the runner with the **mandatory labels** matching the workflows'
`runner_labels` default:

```sh
sudo -u gh-runner ./config.sh \
    --url https://github.com/open-img-cloud \
    --token <REGISTRATION_TOKEN> \
    --name "$(hostname -s)-rocky10" \
    --labels "self-hosted,Linux,kvm" \
    --runnergroup default \
    --work _work \
    --unattended \
    --replace
```

> **Labels matter.** The reusable workflows select runners via
> `["self-hosted","Linux","kvm"]`. A runner missing any of these will not
> pick up jobs. If you provision an arm64 host, add `arm64` to the labels
> and update the consumer repos' workflows accordingly (none currently
> distinguish architecture; arm64 is not yet a target for openimages.cloud).

## 6. Install as a systemd service

> **Apply the SELinux relabel from §3.1 first** (before `svc.sh start`),
> otherwise the service fails immediately with `status=203/EXEC`.

```sh
cd /var/lib/gh-runner
sudo ./svc.sh install gh-runner
sudo ./svc.sh start
sudo ./svc.sh status   # expect "active (running)"
```

Disable / remove later if needed:

```sh
sudo ./svc.sh stop
sudo ./svc.sh uninstall
sudo -u gh-runner ./config.sh remove --token <REMOVAL_TOKEN>
```

(Removal token is generated the same way as the registration token via
`/orgs/.../actions/runners/remove-token`.)

## 7. Verify end-to-end

From any consumer repo (e.g. `open-img-cloud/alpaquita`), trigger a
workflow_dispatch of `release.yml` with `publish: false` to dry-run a
build without uploading. Check that:

1. The runner picks up the job (`gh-runner` log: `Listening for Jobs` →
   `Running job: build`).
2. `verify-builder` succeeds (cosign verification of the builder image).
3. The `build` job pulls the builder container with `--device=/dev/kvm`.
4. `qemu-img info` and `libguestfs-test-tool` (run inside the container)
   show KVM acceleration enabled (look for `accelerator: KVM` in
   `qemu-img info` output, and `KVM enabled: yes` in test-tool output).

If KVM isn't available inside the container, the libguestfs appliance
falls back to TCG and the build is dramatically slower. Check:

```sh
podman run --rm --device=/dev/kvm ghcr.io/stackopshq/libguestfs-tools:2 \
    libguestfs-test-tool 2>&1 | grep -i 'kvm enabled'
```

## 8. Hardening

Highly recommended additions, especially for runners that build images
later promoted to production:

- **Restrict the runner to specific repos**: in the org runner group
  settings, scope to `Selected repositories` (not "All repositories"); list
  only the image repos consumed by the build workflow. This prevents
  unrelated PRs from grabbing your KVM-capable runners.
- **Disable workflow access from forks**: in `Actions → General → Fork
  pull request workflows from outside collaborators`, require approval
  before any fork PR can run on these runners. They have access to your
  Cloudflare and S3 secrets via `secrets: inherit`.
- **Auto-update the runner**: keep the runner version current. The runner
  agent self-updates by default unless `--disableupdate` was passed.
- **Ephemeral mode**: pass `--ephemeral` to `config.sh` to make the runner
  process exit after one job. Combined with a systemd `Restart=always`
  drop-in, this gives single-use runners (no inter-job state contamination).
  Trade-off: ~30 s extra startup per job.
- **podman storage quota**: long-running builders accumulate layers. Add a
  weekly `podman system prune -af` cron under the `gh-runner` user.
- **Network egress filtering**: if the host is behind a firewall, allow
  outbound to: `api.github.com`, `*.actions.githubusercontent.com`,
  `objects.githubusercontent.com`, `ghcr.io`, `quay.io`, `fulcio.sigstore.dev`,
  `rekor.sigstore.dev`, plus your Garage and R2 endpoints.

## 9. Common failures

| Symptom                                                               | Fix                                                                                  |
|-----------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| `status=203/EXEC ... Unable to locate executable '...': Permission denied` (no AVC in audit log) | systemd refuses to exec `var_lib_t`-labelled files even when the User= owns them. Apply the persistent `bin_t` fcontext rules from §3.1 + `restorecon`. |
| `no subuid ranges found for user "gh-runner"` (rootless podman)        | Allocate subuid/subgid: `sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 gh-runner` (§3.2). |
| `Could not access KVM kernel module: Permission denied`               | Runner user not in `kvm` group. `sudo usermod -aG kvm gh-runner && sudo systemctl restart gh-runner.service`. |
| `libguestfs: error: appliance closed connection unexpectedly`         | Likely OOM. Bump `LIBGUESTFS_MEMSIZE=8192` in the consumer workflow or runner host.  |
| `Cosign verification failed: certificate identity does not match`     | Builder image was rebuilt under a different repo/identity. Update `builder_cert_identity` input or revert to the canonical `stackopshq` source. |
| AVC denial on `/var/lib/gh-runner/_work/...`                          | `sudo restorecon -Rv /var/lib/gh-runner` (or persistent fcontext, see §3.3).         |
| Runner picks up jobs but they never start (queued forever)            | Labels mismatch. Confirm the runner has all of `self-hosted,Linux,kvm`.              |
| `manifest unknown` when pulling `ghcr.io/stackopshq/libguestfs-tools:vN` | Tags on GHCR have no `v` prefix — use `:N`, `:N.M`, or `:N.M.P` (e.g. `:2`, not `:v2`). |
| `podman: Error: short-name resolution enforced but cannot prompt`     | The container ref needs to be fully qualified (it is, in the workflows). Check that no caller overrides `build_container` with a short name. |
