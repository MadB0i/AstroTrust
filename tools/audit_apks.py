"""Unified static forensic audit tool for commercial Android astrology APKs.

Reproduces manifest permission/queries inspection, APK file overlap metrics
(Astrotalk vs. Pandit Ji), Hermes bundle / DEX endpoint discovery, and exact
extraction + categorization of Astrotalk's `assets/apppackges.json` tracker list.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_APK_DIR = Path(r"D:\ASTRO")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "data" / "results" / "apk_forensic_summary.json"

TARGET_APKS = (
    "Astrotalk.apk",
    "Pandit Ji.apk",
    "Reva.apk",
    "AstroTime.apk",
    "AstroSage AI.apk",
)


def parse_axml(data: bytes) -> dict[str, Any]:
    """Parse Android binary XML for manifest metadata, permissions, and <queries>."""
    if len(data) < 12 or struct.unpack_from("<HH", data, 0) != (3, 8):
        raise ValueError("Not a valid binary AndroidManifest.xml")

    strings: list[str] = []
    pos = 8
    manifest_attrs: dict[str, Any] = {}
    permissions: list[str] = []
    query_packages: list[str] = []
    query_intents = 0
    in_queries = 0

    while pos + 8 <= len(data):
        ctype, _hdr, csize = struct.unpack_from("<HHI", data, pos)
        if csize < 8:
            break
        if ctype == 1:  # RES_STRING_POOL_TYPE
            scount, _, flags, soff = struct.unpack_from("<IIII", data, pos + 8)
            utf8 = bool(flags & 0x100)
            offsets = struct.unpack_from(f"<{scount}I", data, pos + 28)
            base = pos + soff
            strings = []
            for o in offsets:
                p = base + o
                if utf8:
                    p += 2 if (data[p] & 0x80) else 1
                    p += 2 if (data[p] & 0x80) else 1
                    end = data.find(b"\x00", p)
                    strings.append(data[p : (end if end != -1 else p)].decode("utf-8", "replace"))
                else:
                    ln = struct.unpack_from("<H", data, p)[0]
                    strings.append(data[p + 2 : p + 2 + ln * 2].decode("utf-16le", "replace"))
        elif ctype == 0x0102:  # RES_XML_START_ELEMENT_TYPE
            name_idx = struct.unpack_from("<i", data, pos + 20)[0]
            tag = strings[name_idx] if 0 <= name_idx < len(strings) else ""
            attr_count = struct.unpack_from("<H", data, pos + 28)[0]
            attrs: dict[str, Any] = {}
            for i in range(attr_count):
                apos = pos + 36 + i * 20
                aname_idx, rval = struct.unpack_from("<ii", data, apos + 4)
                dval = struct.unpack_from("<I", data, apos + 16)[0]
                aname = strings[aname_idx] if 0 <= aname_idx < len(strings) else f"attr_{i}"
                val: Any = strings[rval] if 0 <= rval < len(strings) else dval
                attrs[aname] = val
            if tag == "manifest":
                manifest_attrs = attrs
            elif tag == "uses-permission" and isinstance(attrs.get("name"), str):
                permissions.append(str(attrs["name"]))
            elif tag == "queries":
                in_queries += 1
            elif in_queries > 0 and tag == "package" and isinstance(attrs.get("name"), str):
                query_packages.append(str(attrs["name"]))
            elif in_queries > 0 and tag == "intent":
                query_intents += 1
        elif ctype == 0x0103:  # RES_XML_END_ELEMENT_TYPE
            name_idx = struct.unpack_from("<i", data, pos + 20)[0]
            tag = strings[name_idx] if 0 <= name_idx < len(strings) else ""
            if tag == "queries" and in_queries > 0:
                in_queries -= 1
        pos += csize

    return {
        "package": manifest_attrs.get("package"),
        "version_name": manifest_attrs.get("versionName"),
        "version_code": manifest_attrs.get("versionCode"),
        "permissions_count": len(set(permissions)),
        "has_query_all_packages": "android.permission.QUERY_ALL_PACKAGES" in permissions,
        "has_detect_screen_capture": "android.permission.DETECT_SCREEN_CAPTURE" in permissions,
        "query_package_tags": len(query_packages),
        "unique_query_packages": sorted(set(query_packages)),
        "query_intent_tags": query_intents,
    }


_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "AI Assistants",
        (),
        (
            "com.openai.chatgpt",
            "com.google.android.apps.bard",
            "com.anthropic.claude",
            "ai.perplexity.app.android",
            "com.microsoft.copilot",
            "com.deepseek.chat",
            "notion.id",
            "com.amazon.dee.app",
        ),
    ),
    (
        "Gig-Economy Driver & Delivery Partner",
        (),
        (
            "com.ubercab.driver",
            "com.olacabs.oladriver",
            "com.rapido.rider",
            "in.juspay.nammayatripartner",
            "com.theporter.android.driverapp",
            "in.swiggy.deliveryapp",
            "com.zomato.delivery",
            "com.zepto.rider",
            "com.urbanclap.provider",
        ),
    ),
    (
        "Rail & Commuter Transit",
        (),
        (
            "cris.org.in.prs.ima",
            "com.railyatri.in.mobile",
            "com.ixigo.train.ixitrain",
            "com.whereismytrain.android",
        ),
    ),
    (
        "Indian Government Identity & Welfare",
        (),
        (
            "com.digilocker.android",
            "in.gov.umang.negd.g2c",
            "in.gov.uidai.mAadhaarPlus",
            "com.nic.mparivahan",
            "com.nic.project.pmkisan",
            "com.beneficiaryapp",
            "nic.goi.aarogyasetu",
            "org.digiyatra.org",
        ),
    ),
    (
        "Reproductive Health, Pregnancy & Mental Therapy",
        (),
        (
            "com.betterhelp",
            "com.talkspace.talkspaceapp",
            "org.iggymedia.periodtracker",
            "com.clue.android",
            "in.plackal.lovecyclesfree",
            "com.popularapp.periodcalendar",
            "premom.eh.com.ehpremomapp",
            "com.glow.android",
            "com.ovuline.fertility",
            "com.ovuline.pregnancy",
            "com.hp.pregnancy.lite",
            "com.babycenter.pregnancytracker",
            "com.wte.view",
            "com.healofy",
            "in.mylo.pregnancy.baby.app",
            "com.tickledmedia.ParentTown",
        ),
    ),
    (
        "Dating, Matrimony & Live Video Chat",
        (
            "matrimony",
            "shaadi",
            "bumble",
            "tinder",
            "hinge",
            "okcupid",
            "happn",
            "betterhalf",
            "trulymadly",
            "quackquack",
            "aisle",
            "jodii",
            "jodi365",
            "m4marry",
            "jeevansathi",
            "dil mil",
            "plenty of fish",
            "coffee meets",
            "eharmony",
            "badoo",
            "zoosk",
            "hily",
            "azar",
            "chamet",
            "tango",
            "bigo live",
        ),
        ("boo.enterprises.dating.boo", "com.match.android.matchmobile", "com.dating.for.all"),
    ),
    (
        "Consumer Loans, BNPL, Gold Loans & Credit",
        (
            "moneyview",
            "earlysalary",
            "mpokket",
            "kissht",
            "true balance",
            "cashe",
            "lazypay",
            "simpl",
            "paysense",
            "moneytap",
            "home credit",
            "stashfin",
            "muthoot",
            "manappuram",
            "rupeek",
            "cibil",
            "onescore",
            "paisabazaar",
            "bajaj finserv",
            "kreditbee",
            "credit karma",
            "affirm",
            "klarna",
            "afterpay",
            "okcredit",
            "khatabook",
            "vyapar",
            "onecard",
            "scapia",
            "sbi card",
            "amex india",
            "american express",
        ),
        ("com.naviapp", "indwin.c3.shareapp"),
    ),
    (
        "Stock Trading, Wealth & Crypto",
        (
            "groww",
            "zerodha",
            "paytm money",
            "angel one",
            "upstox",
            "indwealth",
            "mosl",
            "univest",
            "smallcase",
            "smartspends",
            "fyers",
            "dhan",
            "vested",
            "5paisa",
            "tickertape",
            "hdfc sky",
            "icici direct",
            "kotak neo",
            "stable money",
            "robinhood",
            "schwab",
            "fidelity",
            "e*trade",
            "webull",
            "coinbase",
            "wealthsimple",
            "wazirx",
            "coindcx",
            "coinswitch",
            "mudrex",
            "zebpay",
            "binance",
            "bybit",
            "kucoin",
            "whitepivot",
        ),
        (),
    ),
    (
        "Real-Money Gambling, Fantasy Sports & Betting",
        (
            "probo",
            "zupee",
            "winzo",
            "dream11",
            "my11circle",
            "last ball six",
            "jumbo",
            "junglee",
            "games365",
            "melbet",
            "playerport",
            "pokerstars",
            "a23",
            "parimatch",
            "draftkings",
            "fanduel",
            "betmgm",
            "caesars",
            "prizepicks",
            "underdog",
            "bet365",
            "sky bet",
            "paddy power",
            "william hill",
            "betfair",
            "ladbrokes",
            "sportsbet",
            "national lottery",
            "rummy",
            "teen patti",
            "pokerbaazi",
            "pocket52",
            "1xbet",
            "ludo king",
        ),
        (
            "com.mpl.androidapp.cash",
            "com.mpl.androidapp.opiniowin",
            "au.com.tabcorp.sportsbet",
            "nz.co.tab.TAB_Mobile",
            "com.getstan",
            "com.eloelo",
        ),
    ),
    (
        "Competitor Astrology, Tarot, Psychic & Advisor",
        (
            "astro",
            "kundli",
            "horoscope",
            "tarot",
            "psychic",
            "palm",
            "numerolog",
            "panditji",
            "co-star",
            "chani",
            "timepassages",
            "sanctuary",
            "keen",
            "purple garden",
            "kasamba",
            "purple ocean",
            "mysticsense",
            "oranum",
            "soulight",
            "varta panel",
            "anytime astro",
            "vama",
            "bodhi",
            "yodha",
            "suvich",
            "melooha",
            "horocosmo",
            "the pattern",
            "divine",
            "ganeshaspeaks",
            "guruji",
            "gurudev",
            "align27",
            "cosmic insights",
            "pocket insight",
            "nebula",
            "moonly",
        ),
        (),
    ),
    (
        "Devotional, Panchang & Spiritual",
        (
            "sri mandir",
            "devdham",
            "utsav",
            "bhakti",
            "sadhguru",
            "art of living",
            "heartfulness",
            "murli",
            "panchang",
            "hindu calendar",
            "kalnirnay",
            "sadhana",
            "lifeguru",
            "shyam baba",
            "ttdevasthanams",
            "vaishnodevi",
            "vaastu",
            "insight timer",
        ),
        (),
    ),
    (
        "Health, Insurance, Pharmacy & Wearables",
        (
            "policybazaar",
            "acko",
            "star health",
            "niva bupa",
            "care health",
            "practo",
            "tata 1mg",
            "pharmeasy",
            "apollo 24",
            "truemeds",
            "cult.fit",
            "healthifyme",
            "fittr",
            "strava",
            "myfitnesspal",
            "nike run",
            "calm",
            "headspace",
            "ultrahuman",
            "samsung health",
            "galaxy wearable",
            "fitbit",
            "garmin",
            "mi fitness",
            "noisefit",
            "zepp",
            "pixel watch",
            "whoop",
            "oura",
            "peloton",
            "noom",
            "weightwatchers",
            "cvs health",
            "digit insurance",
        ),
        (),
    ),
    (
        "EdTech, Exam Prep & Job Search",
        (
            "seekho",
            "physicswallah",
            "testbook",
            "adda247",
            "unacademy",
            "byju",
            "vedantu",
            "doubtnut",
            "embibe",
            "utkarsh",
            "studyiq",
            "khan global",
            "oliveboard",
            "exampur",
            "duolingo",
            "upgrad",
            "coursera",
            "naukri",
            "foundit",
            "indeed",
            "glassdoor",
            "apna",
            "workindia",
            "internshala",
            "linkedin",
        ),
        (),
    ),
    (
        "Global Banking, UPI, Wallets & Remittance",
        (
            "phonepe",
            "cred",
            "google pay",
            "paytm",
            "bhim",
            "mobikwik",
            "freecharge",
            "airtel thanks",
            "jiomoney",
            "payzapp",
            "axis pay",
            "axis bank",
            "bandhan",
            "bank of baroda",
            "canara",
            "dbs ",
            "dcb upi",
            "fino payment",
            "hdfc bank",
            "hsbc",
            "icici bank",
            "iob upi",
            "indusind",
            "j&k bank",
            "kvb ",
            "smartz",
            "kotak",
            "federal bank",
            "maharashtra upi",
            "mi pay",
            "paybee",
            "pnb one",
            "samsung pay",
            "sbi upi",
            "south indian",
            "union bank",
            "uco bank",
            "yes bank",
            "bullet",
            "wise",
            "idfc first",
            "au 0101",
            "yono sbi",
            "fedmobile",
            "bob world",
            "chase",
            "bank of america",
            "wells fargo",
            "citi mobile",
            "capital one",
            "discover",
            "u.s. bank",
            "pnc mobile",
            "td bank",
            "usaa",
            "ally",
            "sofi",
            "chime",
            "venmo",
            "cash app",
            "zelle",
            "paypal",
            "barclays",
            "lloyds",
            "halifax",
            "natwest",
            "royal bank of scotland",
            "santander",
            "tsb",
            "nationwide",
            "monzo",
            "starling",
            "revolut",
            "rbc mobile",
            "td canada",
            "scotiabank",
            "bmo",
            "cibc",
            "tangerine",
            "commbank",
            "anz ",
            "westpac",
            "nab",
            "up bank",
            "bnz mobile",
            "enbd",
            "liv x",
            "adcb",
            "fab mobile",
            "mashreq",
            "ocbc",
            "uob tmrw",
            "remitly",
            "western union",
            "xoom",
            "worldremit",
            "moneygram",
            "ria money",
            "instarem",
            "al ansari",
            "lulu money",
            "jar",
            "jupiter money",
            "fi money",
        ),
        (),
    ),
    (
        "OTT Streaming, Media, News & Audio",
        (
            "netflix",
            "amazon prime",
            "cdi video",
            "sonyliv",
            "hotstar",
            "jiotv",
            "jiocinema",
            "hoichoi",
            "stage",
            "etv win",
            "smart tv",
            "eros now",
            "sun nxt",
            "altbalaji",
            "shemaroo",
            "lionsgate",
            "docubay",
            "epic on",
            "mx player",
            "manorama max",
            "minitv",
            "apple tv",
            "cityshort",
            "chaupal",
            "planet marathi",
            "olly plus",
            "saina",
            "watcho",
            "tata play",
            "twitch",
            "hindustan times",
            "aaj tak",
            "cricbuzz",
            "sportskeeda",
            "kuku fm",
            "pocket fm",
            "cricheroes",
            "espncricinfo",
            "spotify",
            "times of india",
            "inshorts",
            "youtube",
            "zee5",
            "voot",
            "economic times",
            "mint",
            "the hindu",
            "bloomberg",
            "wall street journal",
            "financial times",
            "nytimes",
            "economist",
            "apple music",
            "amazon music",
            "audible",
            "kindle",
            "storytel",
            "mubi",
            "medium",
            "blinkist",
            "hulu",
            "hbo max",
            "disney+",
            "peacock",
            "paramount+",
            "sling tv",
            "pluto tv",
            "sky go",
            "bbc iplayer",
            "yupptv",
            "willow",
            "sharechat",
            "moj",
            "josh",
            "dailyhunt",
            "pratilipi",
            "public",
            "kutumb",
            "way2news",
            "dainik bhaskar",
            "amar ujala",
            "lokmat",
            "loksatta",
            "roposo",
            "chingari",
            "jiosaavn",
            "gaana",
            "wynk",
        ),
        ("ahaflix.tv",),
    ),
)


def categorize_tracked_apps(apps_raw: list[dict[str, str]]) -> dict[str, int]:
    """Deterministically bin Astrotalk's assets/apppackges.json entries by domain."""
    counts: Counter[str] = Counter()
    for entry in apps_raw:
        pkg = entry["package_name"]
        nl = entry["name"].lower()
        pl = pkg.lower()
        assigned = "Travel, E-Commerce, Ride-Hailing, Food & Other"
        for category, keywords, exact_pkgs in _CATEGORY_RULES:
            if pkg in exact_pkgs or (keywords and any(k in nl or k in pl for k in keywords)):
                assigned = category
                break
        counts[assigned] += 1
    return dict(counts.most_common())


def _scan_sdk_signals(blob: bytes) -> list[str]:
    low = blob.lower()
    markers = (
        ("appsflyer", b"appsflyer"),
        ("rudderstack", b"rudder-prod" if b"rudder-prod" in low else b"rudderstack"),
        ("posthog", b"posthog"),
        ("clevertap", b"clevertap"),
        ("mixpanel", b"mixpanel"),
        ("razorpay", b"razorpay"),
        ("paytm_sdk", b"paytm"),
        ("cashfree", b"cashfree"),
        ("phonepe_sdk", b"phonepe"),
        ("firebase", b"firebase"),
        ("rootbeer_libtoolchecker", b"toolchecker"),
        ("packagemanager_getinstalled", b"getinstalledpackages"),
        ("packagemanager_queryintent", b"queryintentactivities"),
    )
    return sorted({label for label, token in markers if token in low})


def inspect_single_apk(path: Path) -> dict[str, Any]:
    """Return static manifest, asset, and endpoint summary for one APK."""
    if not path.is_file():
        return {"filename": path.name, "status": "missing"}
    size = path.stat().st_size
    if size == 0:
        return {"filename": path.name, "status": "empty_stub_0_bytes", "size_bytes": 0}

    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as zf:
        infos = {zi.filename: (zi.file_size, zi.CRC) for zi in zf.infolist()}
        names = set(infos)
        manifest = parse_axml(zf.read("AndroidManifest.xml"))
        dex_files = sorted(n for n in names if n.startswith("classes") and n.endswith(".dex"))
        has_apppackges = "assets/apppackges.json" in names
        has_rn = "assets/index.android.bundle" in names
        dex_and_bundle_blobs = [
            zf.read(t) for t in dex_files + (["assets/index.android.bundle"] if has_rn else [])
        ]
        combined_code_blob = b"".join(dex_and_bundle_blobs)

        tracker_evidence: dict[str, Any] = {}
        if has_apppackges:
            apps_raw = json.loads(zf.read("assets/apppackges.json").decode("utf-8"))
            tracked_pkgs = {entry["package_name"] for entry in apps_raw}
            qset = set(manifest["unique_query_packages"])
            tracker_evidence = {
                "apppackges_entries": len(apps_raw),
                "apppackges_unique_packages": len(tracked_pkgs),
                "manifest_query_coverage_of_apppackges": len(tracked_pkgs & qset),
                "dex_has_external_package_tracker": b"ExternalPackageTracker" in combined_code_blob,
                "dex_has_execute_24h_check": b"execute_24h_check" in combined_code_blob,
                "dex_has_user_apps_installed_route": b"user/apps/installed" in combined_code_blob,
                "dex_has_save_user_upi_apps_route": b"save/user-upi-apps" in combined_code_blob,
                "category_breakdown": categorize_tracked_apps(apps_raw),
            }

        # Check first-party / sibling backend domain strings in DEX & RN bundle
        url_re = re.compile(rb"https?://[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?:/[A-Za-z0-9._/-]*)?")
        first_party_urls: Counter[str] = Counter()
        for blob in dex_and_bundle_blobs:
            for m in url_re.findall(blob):
                u = m.decode("utf-8", "ignore")
                low = u.lower()
                if any(
                    kw in low
                    for kw in (
                        "astrotalk",
                        "astrobuddy",
                        "theastrotime",
                        "revaastro",
                        "sharechat",
                        "astrosage",
                        "ojassoft",
                    )
                ) and not any(bad in low for bad in ("cdn-sc-g.sharechat.com", "schema")):
                    first_party_urls[u[:100]] += 1

    return {
        "filename": path.name,
        "status": "ok",
        "size_bytes": size,
        "sha256": sha256,
        "zip_entry_count": len(infos),
        "dex_count": len(dex_files),
        "react_native_hermes": has_rn,
        "manifest": {k: v for k, v in manifest.items() if k != "unique_query_packages"},
        "unique_query_packages_count": len(manifest["unique_query_packages"]),
        "sdk_signals": _scan_sdk_signals(combined_code_blob),
        "tracker_evidence": tracker_evidence,
        "top_first_party_urls": [u for u, _ in first_party_urls.most_common(12)],
        "_zip_infos": infos,
    }


def compare_binary_overlap(apk_a: Path, apk_b: Path) -> dict[str, Any]:
    """Measure zip path and exact byte+CRC overlap between two APKs."""
    with zipfile.ZipFile(apk_a) as za, zipfile.ZipFile(apk_b) as zb:
        map_a = {zi.filename: (zi.file_size, zi.CRC) for zi in za.infolist()}
        map_b = {zi.filename: (zi.file_size, zi.CRC) for zi in zb.infolist()}
        dex_b = b"".join(
            zb.read(n) for n in sorted(map_b) if n.startswith("classes") and n.endswith(".dex")
        )
    shared_paths = set(map_a) & set(map_b)
    byte_identical = sum(1 for p in shared_paths if map_a[p] == map_b[p])
    return {
        "apk_a_entries": len(map_a),
        "apk_b_entries": len(map_b),
        "shared_paths": len(shared_paths),
        "shared_paths_pct_of_b": round(100.0 * len(shared_paths) / len(map_b), 2),
        "byte_crc_identical": byte_identical,
        "byte_identical_pct_of_a": round(100.0 * byte_identical / len(map_a), 2),
        "byte_identical_pct_of_b": round(100.0 * byte_identical / len(map_b), 2),
        "apk_b_dex_astrotalk_mentions": dex_b.lower().count(b"astrotalk"),
        "apk_b_dex_astrobuddy_mentions": dex_b.lower().count(b"astrobuddy"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk-dir", type=Path, default=DEFAULT_APK_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_JSON)
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    for name in TARGET_APKS:
        res = inspect_single_apk(args.apk_dir / name)
        res.pop("_zip_infos", None)
        results.append(res)

    overlap: dict[str, Any] = {}
    at_path = args.apk_dir / "Astrotalk.apk"
    pj_path = args.apk_dir / "Pandit Ji.apk"
    if at_path.is_file() and pj_path.is_file():
        overlap = compare_binary_overlap(at_path, pj_path)

    payload = {
        "apk_dir": str(args.apk_dir),
        "apks": results,
        "astrotalk_vs_panditji_overlap": overlap,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("=== ASTROTRUST APK FORENSIC SUMMARY ===")
    for item in results:
        if item["status"] != "ok":
            print(f"- {item['filename']}: {item['status']}")
            continue
        m = item["manifest"]
        print(
            f"- {item['filename']}: pkg={m['package']} v{m['version_name']} "
            f"(code {m['version_code']}) | {item['size_bytes']:,} B | "
            f"sha256={item['sha256'][:16]}... | <queries>={m['query_package_tags']} "
            f"({item['unique_query_packages_count']} unique) | "
            f"intents={m['query_intent_tags']} | "
            f"DETECT_SCREEN_CAPTURE={m['has_detect_screen_capture']}"
        )
        if item["tracker_evidence"]:
            print(f"    tracker={item['tracker_evidence']}")
    if overlap:
        print(f"Astrotalk vs Pandit Ji overlap: {overlap}")
    print(f"Saved summary JSON -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
