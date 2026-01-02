#!/usr/bin/env python3

"""
SPDX-FileCopyrightText: 2024 Adithya R
SPDX-License-Identifier: MIT
"""

import requests
import subprocess
import sys
import xml.etree.ElementTree as ET

if len(sys.argv) != 2:
    print("Usage:\n\t./merge-tag.py <tag>")
    sys.exit(1)

tag = sys.argv[1]

modules = {
    "audio-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/qcom/opensource/audio-kernel-ar",
    "bt-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/bt-kernel",
    "camera-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/camera-kernel",
    "data-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/data-kernel/",
    "dataipa": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/dataipa",
    "datarmnet": "https://git.codelinaro.org/clo/la/platform/vendor/qcom/opensource/datarmnet",
    "datarmnet-ext": "https://git.codelinaro.org/clo/la/platform/vendor/qcom/opensource/datarmnet-ext",
    "display-drivers": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/display-drivers",
    "dsp-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/qcom/opensource/dsp-kernel",
    "eva-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/eva-kernel",
    "fingerprint": "https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/fingerprint",
    "graphics-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/qcom/opensource/graphics-kernel",
    "mm-drivers": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/mm-drivers",
    "mm-sys-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/mm-sys-kernel",
    "mmrm-driver": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/mmrm-driver",
    "securemsm-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/qcom/opensource/securemsm-kernel",
    "spu-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/qcom/opensource/spu-kernel",
    "synx-kernel": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/synx-kernel",
    "touch-drivers": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/touch-drivers",
    "video-driver": "https://git.codelinaro.org/clo/la/platform/vendor/opensource/video-driver",
    "wlan/fw-api": "https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/fw-api",
    "wlan/platform": "https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/platform",
    "wlan/qca-wifi-host-cmn": "https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/qca-wifi-host-cmn",
    "wlan/qcacld-3.0": "https://git.codelinaro.org/clo/la/platform/vendor/qcom-opensource/wlan/qcacld-3.0",
}

# These are in a separate manifest
separated_techpacks = {
    "audio-kernel": "audio",
    "bt-kernel": "btfm",
    "camera-kernel": "camera",
    "display-drivers": "display",
    "eva-kernel": "cv",
    "graphics-kernel": "graphics",
    "mm-drivers": "display",
    "mmrm-driver": "video",
    "video-driver": "video",
    "wlan/fw-api": "wlan",
    "wlan/platform": "wlan",
    "wlan/qca-wifi-host-cmn": "wlan",
    "wlan/qcacld-3.0": "wlan",
}

# Input revision from user - fallback
# for that facepalm moment when they forget to release a manifest xml
def get_revision_from_user():
    i = input("Enter custom tag or revision to proceed, or s to skip: ")
    return None if i.casefold() == 's' else i

# Parses the module revision from a vendor manifest
def get_revision_from_manifest(tag, path, techpack=None):
    if techpack is None:
        root = manifest_root
    else:
        response = requests.get(f"https://git.codelinaro.org/clo/la/techpack/{techpack}/manifest/-/raw/release/{tag}.xml")
        if response.status_code != 200:
            print("Failed to load", techpack, "manifest!")
            return get_revision_from_user()
        root = ET.fromstring(response.content)

    for project in root.findall('project'):
        repo_path = project.get('path')
        if repo_path is not None and repo_path.endswith(path):
            return project.get('revision')

    if techpack is None:
        print("Failed to obtain revision from vendor manifest!")
    else:
        print("Failed to obtain revision from", techpack, "techpack manifest!")

    return get_revision_from_user()

# Obtains the tag for the given techpack manifest from vendor manifest
def get_techpack_tag(techpack):
    refs = manifest_root.find('refs')
    if refs is not None:
        for image in refs:
            project = image.get('project')
            if project == "techpack/" + techpack + "/manifest":
                return image.get('tag')

    print("Failed to obtain", techpack, "techpack tag from manifest!")

# Returns (actual_revision, display_revision)
def get_revision(path):
    if path in separated_techpacks.keys():
        techpack = separated_techpacks.get(path)
        tp_tag = get_techpack_tag(techpack)
        if tp_tag is not None:
            print("Techpack tag:", tp_tag)
            return (get_revision_from_manifest(tp_tag, path, techpack), tp_tag)
    else:
        return (get_revision_from_manifest(tag, path), tag)

# HERE IT BEGINS
response = requests.get(f"https://git.codelinaro.org/clo/la/la/vendor/manifest/-/raw/release/{tag}.xml")
if response.status_code != 200:
    print("Tag does not exist!")
    sys.exit(1)

# print(response.content)
manifest_root = ET.fromstring(response.content)

for path, url in modules.items():
    print("\nMerging", path)

    revs = get_revision(path)
    if revs is None:
        print("Failed to obtain revision, skipping!")
        continue

    rev, display_rev = revs
    if rev is None:
        print("No revision obtained, skipping!")
        continue

    print("URL:", url)
    print("Revision:", rev)

    commit_msg = f"{path}: Merge tag '{display_rev}'"
    if display_rev != tag:
        commit_msg += f"\n\nFrom vendor tag: '{tag}'"

    # git fetch must be successful
    subprocess.run(["git", "fetch", url, rev], check=True)

    # Try the merge
    merge = subprocess.run([
        "git",
        "merge",
        "FETCH_HEAD",
        "-Xsubtree=qcom/opensource/" + path,
        "-m",
        commit_msg,
        "--log=100"
    ])

    # Merge failed!
    if merge.returncode != 0:
        print("\nMerge conflict detected in", path)

        while True:
            conflicts = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=U"],
                capture_output=True,
                text=True
            ).stdout.strip()

            if not conflicts:
                print("Conflicts resolved, continuing script...")

                # Commit only if merge still in progress
                merge_head = subprocess.run(
                    ["git", "rev-parse", "-q", "--verify", "MERGE_HEAD"],
                    capture_output=True
                )

                if merge_head.returncode == 0:
                    subprocess.run(["git", "commit", "--no-edit"], check=False)

                break

            print("\nConflicting files:")
            print(conflicts)
            input("\nResolve conflicts, then press ENTER to continue...")

    print("Successfully merged!")