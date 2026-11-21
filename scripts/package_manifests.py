#!/usr/bin/env python3
"""Package manifests of the published images (packages.json), for package-manifests.yml.

Runs after publication, outside the build: the image is read back from its bucket, checked
against the sha256 of versions.json, inspected offline with virt-inspector (libguestfs builder
container) and the list of installed packages is written next to it:

    <bucket>/<version>/packages.json            (packages-<variant>.json for variant images)

    {"schema": "oic-packages/v1", "image": ..., "version": ..., "variant": ...,
     "source_sha256": ..., "generated_at": ..., "format": "rpm|deb|apk|pacman|...",
     "distro": ..., "packages": [{"name": ..., "version": ..., "arch": ...}]}

Images libguestfs inspection does not list are read directly (rpm, apk and Gentoo
databases, scripts/list_packages.py); the rest (FreeBSD on ZFS, NixOS, CirrOS) is skipped,
not failed.

    package_manifests.py discover [--images "a b"] [--versions 2]    -> GitHub matrix (stdout)
    package_manifests.py extract --items JSON --builder IMAGE@DIGEST [--upload]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

CDN = "https://images.openimages.cloud"
UA = "openimages-package-manifests"
SCHEMA = "oic-packages/v1"
IMMUTABLE = "public, max-age=31536000, immutable"


def _get(url: str, *, method: str = "GET") -> bytes | None:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def manifest_name(variant: str | None) -> str:
    return f"packages-{variant}.json" if variant else "packages.json"


# -- discover ------------------------------------------------------------------------------


def discover(images: set[str], keep: int) -> list[dict]:
    index = json.loads(_get(f"{CDN}/index.json") or b"{}")
    matrix = []
    for image in index.get("images", []):
        image_id = image["id"]
        if images and image_id not in images:
            continue
        artifacts = image.get("artifacts") or []
        if not artifacts:
            continue
        # Bucket: first path segment of the artifact URL (images-router layout).
        bucket = artifacts[0]["url"].removeprefix(CDN + "/").split("/", 1)[0]
        multi = len(artifacts) > 1
        versions_url = image.get("versions_url") or f"{CDN}/{bucket}/versions.json"
        doc = json.loads(_get(versions_url) or b'{"versions": []}')
        entries = [v for v in doc.get("versions", []) if isinstance(v, dict) and v.get("version")]
        latest = image.get("latest_version")
        # The index version first, then the most recent other builds.
        entries.sort(key=lambda v: v.get("built_at") or "", reverse=True)
        entries.sort(key=lambda v: v["version"] != latest)  # stable: newest builds stay first
        items = []
        for entry in entries[:keep]:
            for a in entry.get("artifacts", []):
                variant = a.get("variant") if multi else None
                target = f"{entry['version']}/{manifest_name(variant)}"
                if _get(f"{CDN}/{bucket}/{target}", method="HEAD") is not None:
                    continue  # already there
                items.append(
                    {
                        "version": entry["version"],
                        "variant": variant,
                        "path": a["path"],
                        "sha256": a["sha256"],
                        "size": a.get("size"),
                        "target": target,
                    }
                )
        if items:
            matrix.append({"image": image_id, "bucket": bucket, "items": items})
    return matrix


# -- extract -------------------------------------------------------------------------------


def parse_inspector(xml: str) -> tuple[str | None, str | None, list[dict]]:
    root = ET.fromstring(xml)
    os_el = root.find("operatingsystem")
    if os_el is None:
        return None, None, []
    fmt = os_el.findtext("package_format")
    distro = os_el.findtext("distro")
    packages = []
    for app in os_el.findall("applications/application"):
        name = app.findtext("name")
        if not name:
            continue
        epoch = app.findtext("epoch") or "0"
        version = app.findtext("version") or ""
        release = app.findtext("release") or ""
        full = version + (f"-{release}" if release else "")
        if epoch not in ("", "0"):
            full = f"{epoch}:{full}"
        packages.append({"name": name, "version": full, "arch": app.findtext("arch") or None})
    packages.sort(key=lambda p: (p["name"], p["arch"] or ""))
    return fmt, distro, packages


def fallback_packages(builder: str, work: Path) -> tuple[str | None, str | None, list[dict]]:
    """scripts/list_packages.py in the builder: rpm, apk or Gentoo database read directly."""
    scripts = Path(__file__).resolve().parent
    res = subprocess.run(
        [
            "docker", "run", "--rm", "--device=/dev/kvm",
            "-v", f"{work}:/work:ro",
            "-v", f"{scripts}:/scripts:ro",
            builder,
            "python3", "/scripts/list_packages.py", "/work/image.qcow2",
        ],
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if res.returncode != 0:
        tail = (res.stderr or "").strip().splitlines()[-3:]
        print(f"  fallback listing failed: {' | '.join(tail)}")
        return None, None, []
    doc = json.loads(res.stdout)
    packages = sorted(doc.get("packages") or [], key=lambda p: (p["name"], p.get("arch") or ""))
    return doc.get("format"), doc.get("distro"), packages


def _aws(*args: str) -> None:
    subprocess.run(["aws", *args], check=True)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(1 << 20):
            h.update(block)
    return h.hexdigest()


def extract_one(
    image: str, bucket: str, item: dict, builder: str, work: Path, upload: bool, keep: Path | None
) -> str:
    """Return 'written', 'skipped' or raise."""
    qcow2 = work / "image.qcow2"
    qcow2.unlink(missing_ok=True)
    try:
        # Read from the bucket, not the CDN: no download counted, no edge traffic.
        _aws("s3", "cp", "--no-progress", "--only-show-errors", f"s3://{bucket}/{item['path']}", str(qcow2))
        got = _sha256(qcow2)
        if got != item["sha256"]:
            raise RuntimeError(f"sha256 mismatch: got {got}, versions.json says {item['sha256']}")
        os.chmod(work, 0o755)
        os.chmod(qcow2, 0o644)
        res = subprocess.run(
            [
                "docker", "run", "--rm", "--device=/dev/kvm",
                "-v", f"{work}:/work:ro",
                builder,
                "virt-inspector", "--no-icon", "--format=qcow2", "-a", "/work/image.qcow2",
            ],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if res.returncode != 0:
            tail = (res.stderr or "").strip().splitlines()[-3:]
            print(f"  virt-inspector failed: {' | '.join(tail)}")
            return "skipped"
        fmt, distro, packages = parse_inspector(res.stdout)
        if not packages:
            # Inspection does not know the distribution (Amazon Linux, Alpaquita) or cannot
            # list it (Gentoo): read the package database directly.
            fmt, fb_distro, packages = fallback_packages(builder, work)
            distro = distro or fb_distro
            if packages:
                print(f"  inspection listed nothing, read the {fmt} database directly")
        if not packages:
            print(f"  no package list readable by libguestfs (distro {distro or 'unknown'})")
            return "skipped"
        doc = {
            "schema": SCHEMA,
            "image": image,
            "version": item["version"],
            "variant": item["variant"],
            "source_sha256": item["sha256"],
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "format": fmt,
            "distro": distro,
            "packages": packages,
        }
        out = work / "packages.json"
        out.write_text(json.dumps(doc, indent=1) + "\n")
        print(f"  {len(packages)} {fmt} packages ({distro})")
        if keep:
            copy = keep / bucket / item["target"]
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(out.read_bytes())
        if upload:
            _aws(
                "s3", "cp", "--no-progress", "--only-show-errors",
                "--content-type", "application/json", "--cache-control", IMMUTABLE,
                str(out), f"s3://{bucket}/{item['target']}",
            )
            print(f"  uploaded {bucket}/{item['target']}")
        else:
            print(f"  dry run, not uploaded ({bucket}/{item['target']})")
        return "written"
    finally:
        qcow2.unlink(missing_ok=True)


def extract(entry: dict, builder: str, upload: bool, keep: Path | None) -> int:
    summary = []
    failed = 0
    with tempfile.TemporaryDirectory(prefix="oic-pkg-", dir=os.environ.get("RUNNER_TEMP")) as tmp:
        work = Path(tmp)
        for item in entry["items"]:
            label = f"{entry['image']} {item['version']}" + (f" ({item['variant']})" if item["variant"] else "")
            print(f"::group::{label}")
            try:
                result = extract_one(entry["image"], entry["bucket"], item, builder, work, upload, keep)
            except Exception as e:  # one image version failing does not stop the others
                print(f"::error::{label}: {e}")
                result = "failed"
                failed += 1
            print("::endgroup::")
            summary.append(f"| {label} | {result} |")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as f:
            f.write("| Image | Package manifest |\n|---|---|\n" + "\n".join(summary) + "\n")
    print("\n".join(summary))
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover")
    d.add_argument("--images", default="")
    d.add_argument("--versions", type=int, default=2)
    e = sub.add_parser("extract")
    e.add_argument("--entry", required=True, help="one matrix entry (JSON)")
    e.add_argument("--builder", required=True)
    e.add_argument("--upload", action="store_true")
    e.add_argument("--keep", type=Path, help="also copy the manifests to this directory")
    args = p.parse_args(argv)
    if args.cmd == "discover":
        matrix = discover(set(args.images.split()), max(1, args.versions))
        json.dump(matrix, sys.stdout)
        print(file=sys.stderr)
        for m in matrix:
            print(f"{m['image']}: {len(m['items'])} manifest(s) to make", file=sys.stderr)
        return 0
    return extract(json.loads(args.entry), args.builder, args.upload, args.keep)


if __name__ == "__main__":
    sys.exit(main())
