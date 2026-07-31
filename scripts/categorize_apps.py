"""
Review datasets: categorize applications and count reviews per app.
Outputs CSVs under data/csv/catalog/
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "csv"
OUT = CSV / "catalog"
OUT.mkdir(parents=True, exist_ok=True)


# Unified hackathon-friendly categories
UNIFIED = [
    "Communication & Social",
    "Productivity & Business",
    "Finance & Payments",
    "Shopping & Commerce",
    "Travel & Local",
    "Food & Drink",
    "Entertainment & Media",
    "Games",
    "Tools & Utilities",
    "Health & Fitness",
    "Education",
    "News & Magazines",
    "Maps & Navigation",
    "Security & Privacy",
    "Photo & Video",
    "Music & Audio",
    "Lifestyle & Home",
    "Weather",
    "Open Source / Developer",
    "Other",
]


def clean_play_category(raw: str) -> str:
    """Strip Play Store rank prefixes like '#4 top free news & magazines, News & Magazines'."""
    if not isinstance(raw, str) or not raw.strip():
        return "Other"
    # take last comma segment if rank prefix present
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    # prefer known primary genre tokens
    primary = parts[-1] if parts else raw
    # if first part looks like a rank line, drop it
    if parts and re.match(r"^#\d+", parts[0]):
        primary = parts[-1]
    return primary


def map_play_to_unified(cat: str, section: str = "") -> str:
    c = (cat or "").lower()
    s = (section or "").lower()
    rules = [
        (("communication", "social"), "Communication & Social"),
        (("productivity", "business"), "Productivity & Business"),
        (("finance",), "Finance & Payments"),
        (("shopping",), "Shopping & Commerce"),
        (("travel", "local"), "Travel & Local"),
        (("food", "drink"), "Food & Drink"),
        (("entertainment", "events"), "Entertainment & Media"),
        (("tools", "personalization", "libraries"), "Tools & Utilities"),
        (("health", "fitness", "medical"), "Health & Fitness"),
        (("education", "educational"), "Education"),
        (("news", "magazines"), "News & Magazines"),
        (("maps", "navigation"), "Maps & Navigation"),
        (("photography", "video", "photo"), "Photo & Video"),
        (("music", "audio"), "Music & Audio"),
        (("lifestyle", "house", "home", "beauty", "parenting", "dating"), "Lifestyle & Home"),
        (("weather",), "Weather"),
        (("sports",), "Health & Fitness"),
        (("action", "arcade", "puzzle", "casual", "racing", "role playing", "strategy", "simulation", "adventure", "card", "board", "word", "casino", "trivia"), "Games"),
    ]
    for keys, unified in rules:
        if any(k in c for k in keys) or any(k in s for k in keys):
            return unified
    if "browser" in c or "vpn" in c:
        return "Security & Privacy"
    return "Other"


# Package-prefix / keyword rules for sealuzh (F-Droid-ish corpus)
SEALUZH_RULES: list[tuple[tuple[str, ...], str]] = [
    (("telegram", "whatsapp", "signal", "sms", "mail", "k9", "chat", "irc", "xmpp", "conversations", "facebook", "twitter"), "Communication & Social"),
    (("anki", "wikipedia", "kiwix", "duolingo", "learn", "edu", "course", "dict"), "Education"),
    (("osmand", "maps", "nav", "transit", "gps", "geo"), "Maps & Navigation"),
    (("bank", "pay", "wallet", "finance", "money", "bitcoin", "crypto"), "Finance & Payments"),
    (("shop", "amazon", "ebay", "store"), "Shopping & Commerce"),
    (("food", "recipe", "restaurant"), "Food & Drink"),
    (("camera", "photo", "gallery", "image", "video", "youtube"), "Photo & Video"),
    (("music", "audio", "podcast", "antennapod", "radio", "sound", "spotify", "vlc"), "Music & Audio"),
    (("weather",), "Weather"),
    (("news", "rss", "feedly", "npr"), "News & Magazines"),
    (("health", "habit", "fitness", "workout", "meditat", "sleep"), "Health & Fitness"),
    (("game", "puzzle", "dungeon", "emulator", "ppsspp", "scummvm", "chess", "sudoku", "pixel"), "Games"),
    (("tor", "orbot", "vpn", "privacy", "password", "keepass", "auth", "otp", "security", "firewall"), "Security & Privacy"),
    (("termux", "adb", "root", "kernel", "developer", "git", "ssh", "connectbot", "filemanager", "terminal"), "Open Source / Developer"),
    (("calendar", "task", "note", "todo", "office", "document", "reader", "pdf", "word"), "Productivity & Business"),
    (("browser", "firefox", "chrome", "duckduckgo", "opera", "brave"), "Tools & Utilities"),
    (("home", "light", "wifi", "battery", "launcher", "keyboard", "clock"), "Tools & Utilities"),
    (("wordpress", "nextcloud", "syncthing", "owncloud"), "Productivity & Business"),
]


FRIENDLY_NAMES = {
    "org.telegram.messenger": "Telegram",
    "org.wikipedia": "Wikipedia",
    "org.wordpress.android": "WordPress",
    "org.torproject.android": "Orbot (Tor)",
    "de.danoeh.antennapod": "AntennaPod",
    "com.ichi2.anki": "AnkiDroid",
    "net.osmand.plus": "OsmAnd",
    "com.termux": "Termux",
    "org.kde.kdeconnect_tp": "KDE Connect",
    "com.duckduckgo.mobile.android": "DuckDuckGo",
    "com.fsck.k9": "K-9 Mail",
    "org.isoron.uhabits": "Loop Habit Tracker",
    "com.android.keepass": "KeePassDroid",
    "org.mozilla.firefox": "Firefox",
    "com.google.android.gms": "Google Play Services",
    "org.ppsspp.ppsspp": "PPSSPP Emulator",
    "net.sourceforge.opencamera": "OpenCamera",
    "com.simplemobiletools.gallery": "Simple Gallery",
    "com.simplemobiletools.calendar": "Simple Calendar",
    "org.xbmc.kore": "Kore (Kodi remote)",
    "org.kiwix.kiwixmobile": "Kiwix",
    "org.tasks": "Tasks.org",
    "com.frostwire.android": "FrostWire",
}


def sealuzh_category(package: str) -> str:
    p = package.lower()
    for keys, cat in SEALUZH_RULES:
        if any(k in p for k in keys):
            return cat
    # org.* often OSS utilities
    if p.startswith("org.") or "github" in p or "fdroid" in p:
        return "Open Source / Developer"
    return "Other"


def sealuzh_name(package: str) -> str:
    if package in FRIENDLY_NAMES:
        return FRIENDLY_NAMES[package]
    # last two segments as readable fallback
    parts = package.split(".")
    return parts[-1].replace("_", " ").title() if parts else package


def trustpilot_to_unified(cat: str) -> str:
    c = (cat or "").lower()
    mapping = [
        (("education", "training"), "Education"),
        (("business", "legal", "government", "construction", "manufacturing"), "Productivity & Business"),
        (("home & garden", "home services", "utilities"), "Lifestyle & Home"),
        (("sports", "health", "medical", "beauty", "well-being"), "Health & Fitness"),
        (("food", "beverages", "tobacco", "restaurants", "bars"), "Food & Drink"),
        (("shopping", "fashion"), "Shopping & Commerce"),
        (("vehicles", "transportation"), "Travel & Local"),
        (("money", "insurance"), "Finance & Payments"),
        (("electronics", "technology"), "Tools & Utilities"),
        (("animals", "pets"), "Lifestyle & Home"),
        (("travel", "vacation"), "Travel & Local"),
        (("media", "publishing", "events", "entertainment", "hobbies", "crafts"), "Entertainment & Media"),
        (("public", "local"), "Other"),
    ]
    for keys, unified in mapping:
        if any(k in c for k in keys):
            return unified
    return "Other"


def build_play_apps() -> pd.DataFrame:
    info = pd.read_csv(CSV / "play_market_apps_info.csv")
    revs = pd.read_csv(CSV / "play_market_apps_reviews.csv", usecols=["app_id"])
    counts = revs.groupby("app_id").size().rename("review_count")
    info = info.merge(counts, left_on="app_id", right_index=True, how="left")
    info["review_count"] = info["review_count"].fillna(0).astype(int)
    info["play_category_raw"] = info["categories"]
    info["play_category_clean"] = info["categories"].map(clean_play_category)
    info["unified_category"] = [
        map_play_to_unified(c, s) for c, s in zip(info["play_category_clean"], info["section"])
    ]
    info["product_type"] = "App"
    info["source"] = "play_market_apps"
    info["app_key"] = info["app_id"].astype(str)
    out = info.rename(columns={"app_name": "app_name"})[
        [
            "source",
            "product_type",
            "app_key",
            "app_name",
            "unified_category",
            "play_category_clean",
            "section",
            "review_count",
            "score",
            "ratings_count",
            "downloads",
        ]
    ]
    return out.sort_values(["unified_category", "review_count"], ascending=[True, False])


def build_play_games() -> pd.DataFrame:
    info = pd.read_csv(CSV / "play_market_games_info.csv")
    revs = pd.read_csv(CSV / "play_market_games_reviews.csv", usecols=["game_id"])
    counts = revs.groupby("game_id").size().rename("review_count")
    info = info.merge(counts, left_on="game_id", right_index=True, how="left")
    info["review_count"] = info["review_count"].fillna(0).astype(int)
    info["play_category_clean"] = info["categories"].map(clean_play_category)
    info["unified_category"] = "Games"
    info["product_type"] = "Game"
    info["source"] = "play_market_games"
    info["app_key"] = info["game_id"].astype(str)
    out = info.rename(columns={"game_name": "app_name"})[
        [
            "source",
            "product_type",
            "app_key",
            "app_name",
            "unified_category",
            "play_category_clean",
            "section",
            "review_count",
            "score",
            "ratings_count",
            "downloads",
        ]
    ]
    return out.sort_values("review_count", ascending=False)


def build_sealuzh() -> pd.DataFrame:
    df = pd.read_csv(CSV / "sealuzh_app_reviews.csv", usecols=["package_name"])
    counts = df.groupby("package_name").size().rename("review_count").reset_index()
    counts["app_name"] = counts["package_name"].map(sealuzh_name)
    counts["unified_category"] = counts["package_name"].map(sealuzh_category)
    counts["source"] = "sealuzh_app_reviews"
    counts["product_type"] = "App"
    counts["app_key"] = counts["package_name"]
    counts["play_category_clean"] = ""
    counts["section"] = ""
    counts["score"] = pd.NA
    counts["ratings_count"] = pd.NA
    counts["downloads"] = pd.NA
    return counts[
        [
            "source",
            "product_type",
            "app_key",
            "app_name",
            "unified_category",
            "play_category_clean",
            "section",
            "review_count",
            "score",
            "ratings_count",
            "downloads",
        ]
    ].sort_values(["unified_category", "review_count"], ascending=[True, False])


def build_trustpilot() -> pd.DataFrame:
    df = pd.read_csv(
        CSV / "kerassy_trustpilot_reviews_123k.csv",
        usecols=["category", "company"],
    )
    g = (
        df.groupby(["company", "category"], dropna=False)
        .size()
        .rename("review_count")
        .reset_index()
    )
    g["unified_category"] = g["category"].map(trustpilot_to_unified)
    g["source"] = "trustpilot"
    g["product_type"] = "Company / Service"
    g["app_key"] = g["company"]
    g["app_name"] = g["company"]
    g["play_category_clean"] = g["category"]
    g["section"] = ""
    g["score"] = pd.NA
    g["ratings_count"] = pd.NA
    g["downloads"] = pd.NA
    return g[
        [
            "source",
            "product_type",
            "app_key",
            "app_name",
            "unified_category",
            "play_category_clean",
            "section",
            "review_count",
            "score",
            "ratings_count",
            "downloads",
        ]
    ].sort_values(["unified_category", "review_count"], ascending=[True, False])


def build_tickets_note() -> pd.DataFrame:
    """Tickets are not app-scoped; summarize by queue as 'pseudo-category'."""
    df = pd.read_csv(
        CSV / "tobi_bueck_customer_support_tickets.csv",
        usecols=["type", "queue"],
    )
    g = df.groupby(["queue", "type"]).size().rename("ticket_count").reset_index()
    g["source"] = "tobi_bueck_tickets"
    return g.sort_values("ticket_count", ascending=False)


def category_summary(all_apps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for source, part in all_apps.groupby("source"):
        for cat, sub in part.groupby("unified_category"):
            rows.append(
                {
                    "source": source,
                    "unified_category": cat,
                    "num_apps": sub["app_key"].nunique(),
                    "total_reviews": int(sub["review_count"].sum()),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["source", "total_reviews"], ascending=[True, False]
    )


def main() -> None:
    play_apps = build_play_apps()
    play_games = build_play_games()
    sealuzh = build_sealuzh()
    trustpilot = build_trustpilot()
    tickets = build_tickets_note()

    play_apps.to_csv(OUT / "play_market_apps_by_category.csv", index=False)
    play_games.to_csv(OUT / "play_market_games_by_category.csv", index=False)
    sealuzh.to_csv(OUT / "sealuzh_apps_by_category.csv", index=False)
    trustpilot.to_csv(OUT / "trustpilot_companies_by_category.csv", index=False)
    tickets.to_csv(OUT / "tickets_by_queue_type.csv", index=False)

    combined = pd.concat([play_apps, play_games, sealuzh, trustpilot], ignore_index=True)
    combined.to_csv(OUT / "all_products_review_counts.csv", index=False)

    summary = category_summary(combined)
    summary.to_csv(OUT / "category_summary_by_source.csv", index=False)

    # Top apps overall per source for quick scanning
    tops = []
    for source, part in combined.groupby("source"):
        top = part.nlargest(25, "review_count")[
            ["source", "app_name", "unified_category", "review_count", "app_key"]
        ]
        tops.append(top)
    pd.concat(tops).to_csv(OUT / "top25_apps_per_source.csv", index=False)

    print("Wrote catalog CSVs to", OUT)
    print("\n=== Category totals (all sources) ===")
    overall = (
        combined.groupby("unified_category")
        .agg(num_products=("app_key", "nunique"), total_reviews=("review_count", "sum"))
        .sort_values("total_reviews", ascending=False)
    )
    print(overall.to_string())
    print("\n=== Per-source product & review totals ===")
    print(
        combined.groupby("source")
        .agg(products=("app_key", "nunique"), reviews=("review_count", "sum"))
        .to_string()
    )
    print("\nFiles:")
    for p in sorted(OUT.glob("*.csv")):
        print(f"  {p.name} ({p.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
