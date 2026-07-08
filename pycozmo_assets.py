"""
Ensure PyCozmo Cozmo assets are present (auto-download on first run).
"""

import os
import shutil
import ssl
import urllib.request
import zipfile

import pycozmo.util

OBB_URL = (
    "https://media.githubusercontent.com/media/cristobalraya/cozmo-archive/"
    "master/applications/com.anki.cozmo_3.4.0-1204_plus_OBB.zip"
)

ssl._create_default_https_context = ssl._create_unverified_context  # noqa


class AssetDownloadError(Exception):
    """Failed to download or extract PyCozmo resources."""


def assets_available():
    asset_dir = pycozmo.util.get_cozmo_asset_dir()
    return os.path.exists(asset_dir / "resources.txt")


def _download_file(fspec):
    try:
        with urllib.request.urlopen(OBB_URL) as response, open(fspec, "wb") as f:
            while True:
                data = response.read(8192)
                if not data:
                    break
                f.write(data)
        return True
    except Exception:
        return False


def _extract_archive(fspec, dspec):
    try:
        os.makedirs(str(dspec))
    except FileExistsError:
        pass
    try:
        with zipfile.ZipFile(str(fspec), "r") as f:
            f.extractall(str(dspec))
        return True
    except Exception:
        return False


def download_assets():
    """Download and extract Cozmo resources (same steps as pycozmo_resources.py)."""
    asset_dir = pycozmo.util.get_cozmo_asset_dir()
    resource_file = asset_dir / "obb.zip"

    try:
        os.makedirs(asset_dir)
    except FileExistsError:
        pass

    print("Downloading Cozmo assets (~150 MB). This may take a few minutes...")
    if not _download_file(resource_file):
        raise AssetDownloadError("Download failed. Check your internet connection and try again.")

    print("Extracting resources...")
    if not _extract_archive(resource_file, asset_dir / "obb"):
        raise AssetDownloadError("Extraction failed.")

    os.remove(str(resource_file))

    if not _extract_archive(
        asset_dir / "obb" / "Android" / "obb" / "com.anki.cozmo" / "main.1204.com.anki.cozmo.obb",
        asset_dir / "..",
    ):
        raise AssetDownloadError("Secondary extraction failed.")

    shutil.rmtree(asset_dir / "obb")

    if not _extract_archive(
        asset_dir / "cozmo_resources" / "sound" / "AudioAssets.zip",
        asset_dir / "cozmo_resources" / "sound",
    ):
        raise AssetDownloadError("Sound extraction failed.")

    if not assets_available():
        raise AssetDownloadError(
            "Download finished but resources.txt was not found in {}.".format(asset_dir))

    print("PyCozmo resources ready in {}.".format(asset_dir))


def ensure_assets():
    """Check for Cozmo assets and download them on first run."""
    asset_dir = pycozmo.util.get_cozmo_asset_dir()
    if assets_available():
        return

    print("PyCozmo resources not found in {}.".format(asset_dir))
    download_assets()
