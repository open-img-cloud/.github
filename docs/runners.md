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
    podman-docker \
    qemu-kvm \
    libvirt-daemon-driver-qemu \
    jq \
    curl \
    tar \
    git \
    policycoreutils-python-utils
```

> `podman-docker` provides the `/usr/bin/docker` shim that calls podman.
> The GitHub Actions runner agent uses `docker` CLI internally to start
> the job container declared via `container:` in workflows; without the
> shim, jobs fail at "Starting job container" with `docker: command not
> found`. The shim package also installs the `/var/run/docker.sock`
> symlink pointing at the rootful podman socket (configured in §4).
>
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

### 3.3 `_work/` directory must be `container_file_t` (mandatory)

When the GHA runner downloads action implementations (e.g.
`actions/checkout`, `sigstore/cosign-installer`), it places them under
`/var/lib/gh-runner/_work/_actions/<owner>/<repo>/<sha>/`. Files inherit
the parent directory's SELinux label, which by default is `var_lib_t`.

When the runner then starts the job container with
`-v /var/lib/gh-runner/_work:/__w` (a default bind mount it does without
a `:Z` flag), rootless podman can mount the path but processes inside
the container cannot read the files. The visible symptom is **Node.js
crashing in actions/checkout** with:

```
Error: Cannot find module '/__w/_actions/actions/checkout/<sha>/dist/index.js'
code: 'MODULE_NOT_FOUND'
```

even though the file is present on the host (`ls` works as `gh-runner`).
There's no AVC entry — SELinux silently blocks the rootless container's
read of `var_lib_t` files via the bind-mount.

Apply a persistent fcontext rule so all `_work/` files (and any actions
re-downloaded later) get `container_file_t`:

```sh
sudo semanage fcontext -a -t container_file_t '/var/lib/gh-runner/_work(/.*)?'
sudo restorecon -RFv /var/lib/gh-runner/_work
```

This is **mandatory** for any job that uses JavaScript-based actions
(checkout, upload-artifact, cosign-installer, …) inside a `container:`
job — i.e. virtually every reusable-workflow consumer here.

> **Never** propose `setenforce 0` as a fix. Always trace AVCs with
> `sudo ausearch -m AVC -ts recent` and adjust contexts/booleans.

## 4. Podman socket for `container:` jobs

When a workflow job declares `container:`, the runner agent (GHA's
`docker create` path) bind-mounts `/var/run/docker.sock` into the job
container so the workflow can spawn docker-side-cars (services,
docker-in-docker patterns, etc.). Even when the workflow itself doesn't
use it, the bind mount is unconditional.

`podman-docker` (installed in §1) sets up the symlink
`/var/run/docker.sock → /run/podman/podman.sock`, but the target
service isn't enabled by default. Without this section's setup, jobs
fail at container-creation time with:

```
Error: statfs /var/run/docker.sock: permission denied
##[error]Exit code 125 returned from process: file name '/bin/docker', arguments 'create ...'
```

Three things have to be true:

1. **`podman.socket` must be running** — creates the actual unix socket
   at `/run/podman/podman.sock`.
2. **The socket must be readable by the `gh-runner` user/group** —
   default is `root:root mode 660`; needs adjustment.
3. **The `/run/podman/` directory must be traversable by `gh-runner`** —
   default is `mode 700` (root-only), blocks even
   `stat -L /var/run/docker.sock` for `gh-runner`.

Apply via systemd drop-ins:

```sh
# 4.1 Make the socket readable by gh-runner via group membership
sudo mkdir -p /etc/systemd/system/podman.socket.d
sudo tee /etc/systemd/system/podman.socket.d/group.conf <<'EOF'
[Socket]
SocketMode=0660
SocketGroup=gh-runner
EOF

# 4.2 Make /run/podman/ traversable (mode 0755 instead of default 0700)
sudo mkdir -p /etc/systemd/system/podman.service.d
sudo tee /etc/systemd/system/podman.service.d/runtime-dir.conf <<'EOF'
[Service]
RuntimeDirectoryMode=0755
EOF

# 4.3 Enable + start (or restart, if already running)
sudo systemctl daemon-reload
sudo systemctl enable --now podman.socket
sudo systemctl restart podman.service podman.socket  # picks up RuntimeDirectoryMode

# Verify
sudo -u gh-runner stat -L /var/run/docker.sock | head -3
# expected: a "regular file" / "socket" with mode srw-rw---- root:gh-runner
```

> The runtime-dir mode drop-in only takes effect when systemd recreates
> the directory — i.e. on `podman.service` restart or boot. If you've
> already started the socket once (with the default mode 700 dir), the
> drop-in won't retro-apply; either restart `podman.service` explicitly
> or `chmod 0755 /run/podman` once.

## 5. Install the GitHub Actions runner

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

## 6. Register the runner against the `open-img-cloud` org

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

## 7. Install as a systemd service

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

## 8. Verify end-to-end

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

## 9. Hardening

These are the hardenings actually applied to the production runners
(`gh-runner-1`, `gh-runner-2`). Reproduce them on every new runner.

### 9.1 Scoped runner group (`image-builders`)

Default runner groups expose runners to **all** repos in the org. We
restrict to image build repos only via a dedicated group `image-builders`,
visibility `selected`, listing the consumer repos by ID. Fork PRs from
outside collaborators on those repos require manual approval (set in
`Settings → Actions → General → Require approval for outside collaborators`).

Create / update the group via API (one-time, admin:org):

```sh
gh api -X POST /orgs/open-img-cloud/actions/runner-groups \
  --input - <<'EOF'
{
  "name": "image-builders",
  "visibility": "selected",
  "selected_repository_ids": [<repo_id_1>, <repo_id_2>, ...],
  "allows_public_repositories": true,
  "restricted_to_workflows": false
}
EOF
```

Move runners into the group (`<runner_id>` from `gh api /orgs/.../actions/runners`):

```sh
gh api -X PUT /orgs/open-img-cloud/actions/runner-groups/<group_id>/runners/<runner_id>
```

When registering a new runner, pass `--runnergroup image-builders` to
`config.sh` (already in §6).

### 9.2 Ephemeral runners — NOT APPLIED, here's why

`--ephemeral` was tested and rolled back during the first end-to-end
consumer run. The standalone-bare-metal pattern (register once with
`--ephemeral`, rely on systemd `Restart=always` to relaunch) is
**broken**: the actions/runner agent deregisters itself server-side
after each job exit, but the persisted local credentials are then
invalidated, and the systemd-restarted process can no longer reconnect.
The org-wide `/actions/runners` API drops to zero runners after the
first job runs (success OR failure), and the local agent shows
"Listening for Jobs" but is effectively a zombie.

GitHub's intended ephemeral patterns require external orchestration that
mints a fresh registration token for each runner instance:
- **JIT (Just-in-Time) runners** — an external service calls
  `POST /orgs/.../actions/runners/generate-jitconfig` per job and starts
  a new runner process with the resulting one-shot config.
- **Actions Runner Controller (ARC)** on Kubernetes — does the same
  thing automatically, scaling pods up/down per pending workflow.

Neither is in scope for this 2-runner bare-metal setup. We **stay on
persistent runners** (no `--ephemeral` flag), and rely on the
`container:` keyword in the reusable workflows for inter-job isolation
(each job runs in a fresh container, the runner host doesn't accumulate
job state in any meaningful way; the `_work/` directory is cleaned
between jobs by the runner agent).

We **do** keep the `Restart=always` drop-in — it's still valuable for
resilience against agent crashes and connection drops:

```sh
sudo mkdir -p /etc/systemd/system/actions.runner.open-img-cloud.$(hostname -s).service.d
sudo tee /etc/systemd/system/actions.runner.open-img-cloud.$(hostname -s).service.d/restart.conf <<EOF
[Service]
Restart=always
RestartSec=10
EOF
sudo systemctl daemon-reload
sudo systemctl restart actions.runner.open-img-cloud.$(hostname -s).service
```

If you ever migrate to ARC or a JIT-token orchestrator, revisit this
section.

### 9.3 Weekly podman storage GC

Each unique builder image version pulled stays on disk indefinitely.
Without cleanup, runners accumulate gigabytes over time. A weekly
systemd timer prunes images that haven't been used for 7+ days while
preserving the currently-active image.

```sh
sudo loginctl enable-linger gh-runner   # rootless podman session persistence

sudo tee /etc/systemd/system/podman-prune.service <<'EOF'
[Unit]
Description=Weekly podman GC (gh-runner)
After=network-online.target

[Service]
Type=oneshot
ExecStart=/sbin/runuser -l gh-runner -c '/usr/bin/podman system prune -af --filter until=168h'
EOF

sudo tee /etc/systemd/system/podman-prune.timer <<'EOF'
[Unit]
Description=Weekly podman GC (Sun 03:00 + jitter)

[Timer]
OnCalendar=Sun 03:00
Persistent=true
RandomizedDelaySec=30min

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now podman-prune.timer
sudo systemctl list-timers podman-prune.timer
```

The `RandomizedDelaySec=30min` jitters runners apart so they don't all
GC simultaneously. `Persistent=true` runs a missed timer at next boot
(useful if the runner host was offline at 03:00 Sunday).

### 9.4 Other recommended toggles

- **Disable workflow access from forks**: in `Settings → Actions → General
  → Fork pull request workflows from outside collaborators`, require
  approval before any fork PR can run. The runners have access to your
  Cloudflare and S3 secrets via `secrets: inherit`.
- **Runner auto-update**: keep the runner version current. The agent
  self-updates by default unless `--disableupdate` was passed at config
  time. After a self-update, `runsvc.sh` and `externals/node*/bin/*` get
  re-extracted and **lose their `bin_t` SELinux label** — but the
  persistent `semanage fcontext` rules from §3.1 mean a `restorecon`
  reapplies them automatically. Run a final `restorecon -RFv` after any
  manual `config.sh` re-run to be safe.
- **Network egress filtering**: if the host is behind a firewall, allow
  outbound to: `api.github.com`, `*.actions.githubusercontent.com`,
  `objects.githubusercontent.com`, `ghcr.io`, `quay.io`,
  `fulcio.sigstore.dev`, `rekor.sigstore.dev`, plus your Garage and R2
  endpoints.

## 10. Common failures

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
| `docker: command not found` at "Starting job container"               | Runner host missing the `docker` CLI shim. Install `podman-docker` (§1).             |
| `Error: statfs /var/run/docker.sock: permission denied`               | `podman.socket` not running, or `/run/podman/` not traversable. Apply both drop-ins from §4. |
| `Cannot find module '/__w/_actions/.../dist/index.js' MODULE_NOT_FOUND` (no AVC) | `_work/` files have label `var_lib_t`, rootless container can't read them. Apply persistent `container_file_t` fcontext (§3.3). |
| `cosign verify ... Error: no signatures found` on a multi-arch tag    | The manifest list digest is unsigned (signatures only on per-arch digests). Sign the list separately at build time. Should be fixed in the builder CI; if you see this, the builder is on an old version. |
| `cosign verify ... Error: no signatures found` (signatures actually exist) | Cosign 2.x can't read sigs created by cosign 3.x. Pin both sides of the chain to `sigstore/cosign-installer @ v4.1.2` or newer. |
| `cosign sign-blob: create bundle file: open : no such file or directory` | Cosign 3.x writes a sigstore bundle by default; pass `--bundle <path> --new-bundle-format=true` explicitly (already in the reusable workflows). |
| `virt-customize: error: cannot use '--install' because no package manager has been detected for this guest OS` | libguestfs OS inspection didn't recognize the rootfs (e.g. Alpaquita, missing `ID_LIKE=alpine`). Use `--run-command 'apk add ...'` (or distro equivalent) instead of `--install`. |
