"""
Download Silent Stakeholder datasets and export to CSV.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download, list_repo_files

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "data" / "csv"
RAW_DIR = ROOT / "data" / "raw"
CSV_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(msg, flush=True)


def save_df(df: pd.DataFrame, name: str) -> Path:
    out = CSV_DIR / name
    df.to_csv(out, index=False, encoding="utf-8")
    log(f"  OK {out.name}: {len(df):,} rows, {out.stat().st_size / 1e6:.1f} MB")
    return out


def export_hf_dataset(repo_id: str, out_name: str) -> None:
    from datasets import load_dataset

    log(f"\n[HF] Loading {repo_id} ...")
    ds = load_dataset(repo_id)
    frames = []
    for split, split_ds in ds.items():
        df = split_ds.to_pandas()
        df["split"] = split
        frames.append(df)
        log(f"  split={split}: {len(df):,} rows")
    save_df(pd.concat(frames, ignore_index=True), out_name)


def download_play_market_csvs() -> None:
    """Play Market 1M reviews is already CSV on Hugging Face."""
    repo = "dmytrobuhai/play_market_2025_1m_reviews_500_titles"
    log(f"\n[HF files] Downloading CSVs from {repo} ...")
    files = [f for f in list_repo_files(repo, repo_type="dataset") if f.endswith(".csv")]
    log(f"  found: {files}")
    for fname in files:
        local = hf_hub_download(
            repo_id=repo,
            filename=fname,
            repo_type="dataset",
            local_dir=str(RAW_DIR / "play_market_2025"),
            local_dir_use_symlinks=False,
        )
        # Copy/export into data/csv with clear names
        src = Path(local)
        dest = CSV_DIR / f"play_market_{src.name}"
        # Stream copy to avoid huge memory if already csv
        if not dest.exists() or dest.stat().st_size != src.stat().st_size:
            dest.write_bytes(src.read_bytes())
        log(f"  OK {dest.name}: {dest.stat().st_size / 1e6:.1f} MB")


def try_kaggle(dataset: str, dest_subdir: str) -> bool:
    """Return True if download succeeded."""
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except Exception as e:
        log(f"[Kaggle] package import failed: {e}")
        return False

    cred = Path.home() / ".kaggle" / "kaggle.json"
    if not cred.exists():
        log(f"[Kaggle] missing credentials at {cred}")
        return False

    out = RAW_DIR / dest_subdir
    out.mkdir(parents=True, exist_ok=True)
    try:
        api = KaggleApi()
        api.authenticate()
        log(f"\n[Kaggle] Downloading {dataset} ...")
        api.dataset_download_files(dataset, path=str(out), unzip=True)
        # Move/copy csvs to data/csv
        for csv in out.rglob("*.csv"):
            dest = CSV_DIR / f"kaggle_{dest_subdir}_{csv.name}"
            dest.write_bytes(csv.read_bytes())
            log(f"  OK {dest.name}: {dest.stat().st_size / 1e6:.1f} MB")
        return True
    except Exception as e:
        log(f"[Kaggle] failed for {dataset}: {e}")
        return False


def try_alt_hf_tickets() -> None:
    """If Kaggle 200k is unavailable, note known HF alternatives are DIFFERENT datasets."""
    log("\n[Note] Kaggle 200k tickets requires kaggle.json — skipping alt mirrors to avoid wrong data.")


def write_manifest(results: dict) -> None:
    manifest = CSV_DIR / "DOWNLOAD_MANIFEST.json"
    manifest.write_text(json.dumps(results, indent=2), encoding="utf-8")
    log(f"\nManifest written: {manifest}")


def main() -> int:
    results: dict = {"ok": [], "failed": [], "skipped": []}

    # 1) sealuzh/app_reviews
    try:
        export_hf_dataset("sealuzh/app_reviews", "sealuzh_app_reviews.csv")
        results["ok"].append("sealuzh/app_reviews -> sealuzh_app_reviews.csv")
    except Exception as e:
        results["failed"].append({"source": "sealuzh/app_reviews", "error": str(e)})
        log(f"FAILED sealuzh/app_reviews: {e}")

    # 2) Play market (HF mirror of Kaggle dataset — already CSV)
    try:
        download_play_market_csvs()
        results["ok"].append(
            "dmytrobuhai/play_market_2025_1m_reviews_500_titles -> play_market_*.csv"
        )
    except Exception as e:
        results["failed"].append({"source": "play_market_2025", "error": str(e)})
        log(f"FAILED play_market: {e}")

    # 3) Kerassy/trustpilot-reviews-123k
    try:
        export_hf_dataset(
            "Kerassy/trustpilot-reviews-123k", "kerassy_trustpilot_reviews_123k.csv"
        )
        results["ok"].append(
            "Kerassy/trustpilot-reviews-123k -> kerassy_trustpilot_reviews_123k.csv"
        )
    except Exception as e:
        results["failed"].append(
            {"source": "Kerassy/trustpilot-reviews-123k", "error": str(e)}
        )
        log(f"FAILED trustpilot: {e}")

    # 4) Tobi-Bueck/customer-support-tickets
    try:
        export_hf_dataset(
            "Tobi-Bueck/customer-support-tickets",
            "tobi_bueck_customer_support_tickets.csv",
        )
        results["ok"].append(
            "Tobi-Bueck/customer-support-tickets -> tobi_bueck_customer_support_tickets.csv"
        )
    except Exception as e:
        results["failed"].append(
            {"source": "Tobi-Bueck/customer-support-tickets", "error": str(e)}
        )
        log(f"FAILED tobi tickets: {e}")

    # 5) Kaggle 200k tickets
    if try_kaggle(
        "mirzayasirabdullah07/customer-support-tickets-dataset-200k-records",
        "tickets_200k",
    ):
        results["ok"].append("kaggle tickets 200k")
    else:
        results["skipped"].append(
            {
                "source": "mirzayasirabdullah07/customer-support-tickets-dataset-200k-records",
                "reason": "Needs ~/.kaggle/kaggle.json (Kaggle API token)",
            }
        )
        try_alt_hf_tickets()

    # 6) Also try Kaggle play-market in case user has creds (HF already covered)
    if try_kaggle(
        "dmytrobuhai/play-market-2025-1m-reviews-500-titles", "play_market_kaggle"
    ):
        results["ok"].append("kaggle play-market (duplicate of HF)")
    else:
        results["skipped"].append(
            {
                "source": "dmytrobuhai/play-market-2025-1m-reviews-500-titles",
                "reason": "No Kaggle creds; used Hugging Face CSV mirror instead",
            }
        )

    # GitHub backlog needs a specific repo — write placeholder note
    note = CSV_DIR / "GITHUB_BACKLOG_README.txt"
    note.write_text(
        "GitHub issues/milestones require ONE specific product repo "
        "(e.g. laurent22/joplin).\n"
        "Provide owner/repo and we will export github_issues.csv + github_milestones.csv.\n",
        encoding="utf-8",
    )
    results["skipped"].append(
        {
            "source": "api.github.com issues+milestones",
            "reason": "Needs a chosen app repo (owner/name)",
        }
    )

    write_manifest(results)
    log("\n=== DONE ===")
    log(f"CSV folder: {CSV_DIR}")
    for p in sorted(CSV_DIR.glob("*.csv")):
        log(f"  - {p.name} ({p.stat().st_size / 1e6:.1f} MB)")
    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
