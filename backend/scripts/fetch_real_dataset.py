#!/usr/bin/env python
"""Fetch the real Flipkart Products Dataset used for BazaarPulse analysis.

Source: PromptCloudHQ / flipkart-products (Kaggle), mirrored on HuggingFace so it
can be downloaded without Kaggle credentials:

    https://huggingface.co/datasets/jason1966/PromptCloudHQ_flipkart-products

~20,000 real marketplace listings with retail_price, discounted_price, brand,
category tree and product_rating. Raw file: flipkart_com-ecommerce_sample.csv.

Usage:
    python scripts/fetch_real_dataset.py            # download if missing
    python scripts/fetch_real_dataset.py --force    # re-download
    python scripts/fetch_real_dataset.py --url <other-csv-url>

The downloaded CSV is intentionally NOT committed to git (see .gitignore) —
this script is the reproducible entry point.
"""

import argparse
import hashlib
import logging
import sys
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("fetch_real_dataset")

DATASET_URL = (
    "https://huggingface.co/datasets/jason1966/PromptCloudHQ_flipkart-products/"
    "resolve/main/flipkart_com-ecommerce_sample.csv"
)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TARGET = DATA_DIR / "flipkart_products.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s", url)
    headers = {"User-Agent": "bazaarpulse-dataset-fetcher/1.0"}
    tmp = target.with_suffix(".part")

    with httpx.stream("GET", url, headers=headers, timeout=120, follow_redirects=True) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        done = 0
        with tmp.open("wb") as fh:
            for chunk in resp.iter_bytes(1 << 16):
                fh.write(chunk)
                done += len(chunk)
                if total:
                    logger.info("  %.1f%% (%.1f/%.1f MB)", 100 * done / total, done / 1e6, total / 1e6)
    tmp.replace(target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch the real Flipkart products CSV.")
    parser.add_argument("--url", default=DATASET_URL)
    parser.add_argument("--force", action="store_true", help="Re-download even if present.")
    args = parser.parse_args()

    if TARGET.exists() and not args.force:
        logger.info("Already present: %s (%.1f MB)", TARGET, TARGET.stat().st_size / 1e6)
    else:
        download(args.url, TARGET)
        logger.info("Saved %s (%.1f MB)", TARGET, TARGET.stat().st_size / 1e6)

    logger.info("sha256: %s", sha256(TARGET))
    logger.info("Next: python scripts/load_kaggle_dataset.py --csv %s", TARGET)


if __name__ == "__main__":
    sys.exit(main())