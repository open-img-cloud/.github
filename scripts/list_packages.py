"""Fallback package listing, run in the libguestfs builder container.

For distributions libguestfs inspection does not recognise (Amazon Linux, Alpaquita...) or
cannot list (Gentoo): mount the guest read only and read the package database directly.
Prints {"format": ..., "distro": ..., "packages": [...]} as JSON; format is null when nothing
is found.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

import guestfs

RPM_DBS = ("/usr/lib/sysimage/rpm", "/var/lib/rpm")
APK_DBS = ("/lib/apk/db/installed", "/usr/lib/apk/db/installed", "/var/lib/apk/db/installed")
QF = "%{NAME}\\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\\t%{ARCH}\\n"


def mount_root(g):
    roots = g.inspect_os()
    if not roots:
        return False
    mps = g.inspect_get_mountpoints(roots[0])
    for mp in sorted(mps, key=len):
        try:
            g.mount_ro(mps[mp], mp)
        except RuntimeError:
            pass
    return True


def rpm_packages(g, tmp):
    for path in RPM_DBS:
        if not g.is_dir(path) or not g.ls(path):
            continue
        dbdir = os.path.join(tmp, "rpmdb")
        os.makedirs(dbdir, exist_ok=True)
        g.copy_out(path, dbdir)
        dbpath = os.path.join(dbdir, os.path.basename(path))
        for extra in ([], ["--define", "_db_backend bdb_ro"]):
            res = subprocess.run(
                ["rpm", "--dbpath", dbpath, *extra, "-qa", "--qf", QF],
                capture_output=True, text=True,
            )
            if res.returncode == 0 and res.stdout.strip():
                out = []
                for line in res.stdout.splitlines():
                    name, ver, arch = line.split("\t")
                    ver = ver[2:] if ver.startswith("0:") else ver
                    out.append({"name": name, "version": ver, "arch": None if arch == "(none)" else arch})
                return out
    return []


def apk_packages(g):
    # Alpine: /lib/apk/db; Alpaquita (merged /usr, /lib a symlink): /var/lib/apk/db.
    path = next(
        (p for p in APK_DBS if g.exists(p) and g.is_file(p, followsymlinks=True)), None
    )
    if path is None:
        return []
    out, cur = [], {}
    for line in g.cat(path).splitlines() + [""]:
        if not line:
            if cur.get("P"):
                out.append({"name": cur["P"], "version": cur.get("V", ""), "arch": cur.get("A")})
            cur = {}
        elif len(line) > 2 and line[1] == ":":
            cur[line[0]] = line[2:]
    return out


def gentoo_packages(g):
    base = "/var/db/pkg"
    if not g.is_dir(base):
        return []
    out = []
    for cat in g.ls(base):
        if not g.is_dir(f"{base}/{cat}"):
            continue
        for pv in g.ls(f"{base}/{cat}"):
            m = re.match(r"^(.+?)-(\d[^-]*(?:-r\d+)?)$", pv)
            if m:
                out.append({"name": f"{cat}/{m.group(1)}", "version": m.group(2), "arch": None})
    return out


def os_release_id(g):
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        if g.exists(path):
            m = re.search(r'^ID="?([^"\n]+)"?', g.cat(path), re.M)
            if m:
                return m.group(1)
    return None


def main(image):
    g = guestfs.GuestFS(python_return_dict=True)
    g.add_drive_opts(image, format="qcow2", readonly=1)
    g.launch()
    result = {"format": None, "distro": None, "packages": []}
    if mount_root(g):
        result["distro"] = os_release_id(g)
        with tempfile.TemporaryDirectory() as tmp:
            for fmt, fn in (("rpm", lambda: rpm_packages(g, tmp)), ("apk", lambda: apk_packages(g)),
                            ("ebuild", lambda: gentoo_packages(g))):
                pkgs = fn()
                if pkgs:
                    result.update(format=fmt, packages=pkgs)
                    break
    g.shutdown()
    g.close()
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main(sys.argv[1])
