import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlparse
from zipfile import ZipFile


def _strip_js_assignment(raw: str) -> str:
    """Convert `window.YTD... = [...]` into valid JSON array text."""
    eq_index = raw.find("=")
    if eq_index == -1:
        raise ValueError("Invalid archive JS format: '=' not found")

    payload = raw[eq_index + 1 :].strip()
    if payload.endswith(";"):
        payload = payload[:-1].strip()
    return payload


def _username_from_link(link: str) -> Optional[str]:
    # Parse both profile links and intent links safely.
    try:
        parsed = urlparse(link)
    except Exception:
        return None

    host = (parsed.netloc or "").lower()
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]
    if host not in {"twitter.com", "x.com"}:
        return None

    path_parts = [p for p in parsed.path.split("/") if p]
    if not path_parts:
        return None

    # Handle URLs like /intent/follow?screen_name=someone
    if len(path_parts) >= 2 and path_parts[0].lower() == "intent" and path_parts[1].lower() == "follow":
        query = parse_qs(parsed.query)
        screen_name = (query.get("screen_name") or [""])[0].strip().lstrip("@")
        return screen_name.lower() if screen_name else None

    # Ignore known non-profile routes.
    reserved = {
        "intent",
        "i",
        "home",
        "explore",
        "search",
        "settings",
        "messages",
        "notifications",
        "compose",
        "tos",
        "privacy",
    }
    candidate = path_parts[0].strip().lstrip("@")
    if not candidate or candidate.lower() in reserved:
        return None

    return candidate.lower()


def _clean_username(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip().lstrip("@").lower()
    return cleaned if cleaned else None


def _extract_accounts(items: Iterable[dict], key: str) -> Dict[str, str]:
    """Return account-key -> username map, preferring accountId for matching accuracy."""
    accounts: Dict[str, str] = {}

    for item in items:
        block = item.get(key, {})
        if not isinstance(block, dict):
            continue

        username = (
            _clean_username(block.get("screen_name"))
            or _clean_username(block.get("username"))
            or _username_from_link(str(block.get("userLink", "")))
        )

        account_id = _clean_username(block.get("accountId"))
        if account_id:
            if username:
                accounts[account_id] = username
            else:
                accounts.setdefault(account_id, account_id)
            continue

        # Fallback for archive variants without accountId.
        if username:
            accounts[f"u:{username}"] = username

    return accounts


def _load_json_from_file(path: Path) -> List[dict]:
    raw = path.read_text(encoding="utf-8")
    payload = _strip_js_assignment(raw)
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError(f"Unexpected format in {path.name}: expected list")
    return data


def _load_payload_from_file(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    payload = _strip_js_assignment(raw)
    return json.loads(payload)


def _find_archive_files_in_dir(base: Path) -> Tuple[Path, Path]:
    following_matches = list(base.rglob("following.js"))
    follower_matches = list(base.rglob("follower.js"))

    if not following_matches:
        raise FileNotFoundError("following.js not found in archive directory")
    if not follower_matches:
        raise FileNotFoundError("follower.js not found in archive directory")

    return following_matches[0], follower_matches[0]


def _find_member_name(names: List[str], target: str) -> Optional[str]:
    target_lower = target.lower()
    for name in names:
        if name.lower().endswith(target_lower):
            return name
    return None


def _load_from_zip(zip_path: Path) -> Tuple[List[dict], List[dict]]:
    with ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        following_name = _find_member_name(names, "following.js")
        follower_name = _find_member_name(names, "follower.js")

        if not following_name:
            raise FileNotFoundError("following.js not found inside zip archive")
        if not follower_name:
            raise FileNotFoundError("follower.js not found inside zip archive")

        following_raw = zf.read(following_name).decode("utf-8")
        follower_raw = zf.read(follower_name).decode("utf-8")

    following = json.loads(_strip_js_assignment(following_raw))
    followers = json.loads(_strip_js_assignment(follower_raw))

    if not isinstance(following, list) or not isinstance(followers, list):
        raise ValueError("Unexpected archive format: following/follower payload is not a list")

    return following, followers


def _load_payload_from_zip_member(zip_path: Path, member_name: str) -> Any:
    with ZipFile(zip_path, "r") as zf:
        raw = zf.read(member_name).decode("utf-8")
    return json.loads(_strip_js_assignment(raw))


def _find_profile_payload_in_zip(zip_path: Path) -> Optional[Any]:
    candidate_names = [
        "profile.js",
        "user.js",
        "personalDetails.js",
        "personaldetails.js",
        "account.js",
    ]
    payloads: List[Any] = []
    with ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
    for candidate in candidate_names:
        for member_name in names:
            base_name = Path(member_name).name.lower()
            if base_name == candidate.lower():
                try:
                    payloads.append(_load_payload_from_zip_member(zip_path, member_name))
                    break
                except Exception:
                    continue
    if payloads:
        return payloads
    return None


def _find_profile_payload_in_dir(base: Path) -> Optional[Any]:
    candidate_names = [
        "profile.js",
        "user.js",
        "personalDetails.js",
        "personaldetails.js",
        "account.js",
    ]
    payloads: List[Any] = []
    for file_name in candidate_names:
        for path in base.rglob(file_name):
            try:
                payloads.append(_load_payload_from_file(path))
                break
            except Exception:
                continue
    if payloads:
        return payloads
    return None


def _find_first_str_value(payload: Any, keys: Set[str]) -> Optional[str]:
    lowered = {k.lower() for k in keys}
    stack = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                key_lower = str(key).lower()
                if key_lower in lowered and value is not None:
                    if isinstance(value, (str, int)):
                        return str(value).strip()
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    return None


def _extract_profile_from_payload(payload: Any) -> Dict[str, str]:
    profile: Dict[str, str] = {
        "display_name": "",
        "username": "",
        "account_id": "",
        "avatar_url": "",
    }

    if payload is None:
        return profile

    display_name = _find_first_str_value(
        payload,
        {
            "name",
            "displayname",
            "display_name",
            "accountdisplayname",
            "screenname",
        },
    )
    username = _find_first_str_value(
        payload,
        {
            "username",
            "screen_name",
            "screenname",
            "handle",
            "accountusername",
        },
    )
    account_id = _find_first_str_value(
        payload,
        {
            "accountid",
            "account_id",
            "id",
            "id_str",
            "userid",
            "user_id",
        },
    )
    avatar_url = _find_first_str_value(
        payload,
        {
            "avatarmediaurl",
            "avatar_url",
            "profileimageurl",
            "profile_image_url",
            "profileimageurlhttps",
            "profile_image_url_https",
        },
    )

    cleaned_username = _clean_username(username)
    if not cleaned_username:
        link_username = _username_from_link(_find_first_str_value(payload, {"profileurl", "url", "userlink"}) or "")
        cleaned_username = _clean_username(link_username)

    profile["display_name"] = (display_name or "").strip()
    profile["username"] = cleaned_username or ""
    profile["account_id"] = (account_id or "").strip()
    profile["avatar_url"] = (avatar_url or "").strip()
    return profile


def _load_archive_items(archive_path: Path) -> Tuple[List[dict], List[dict], Optional[Any]]:
    if archive_path.is_file() and archive_path.suffix.lower() == ".zip":
        following_items, follower_items = _load_from_zip(archive_path)
        profile_payload = _find_profile_payload_in_zip(archive_path)
        return following_items, follower_items, profile_payload

    following_file, follower_file = _find_archive_files_in_dir(archive_path)
    following_items = _load_json_from_file(following_file)
    follower_items = _load_json_from_file(follower_file)
    profile_payload = _find_profile_payload_in_dir(archive_path)
    return following_items, follower_items, profile_payload


def analyze(following: Set[str], followers: Set[str]) -> Dict[str, List[str]]:
    return {
        "one_way_following": sorted(following - followers),
        "mutuals": sorted(following & followers),
        "one_way_followers": sorted(followers - following),
    }


def _sorted_usernames(keys: Set[str], preferred: Dict[str, str], fallback: Dict[str, str]) -> List[str]:
    values = []
    for key in keys:
        username = preferred.get(key) or fallback.get(key) or key
        if key.startswith("u:"):
            username = key[2:]
        values.append(username)
    return sorted(set(values))


def analyze_accounts(following_accounts: Dict[str, str], follower_accounts: Dict[str, str]) -> Dict[str, List[str]]:
    following_keys = set(following_accounts.keys())
    follower_keys = set(follower_accounts.keys())

    return {
        "one_way_following": _sorted_usernames(
            following_keys - follower_keys,
            following_accounts,
            follower_accounts,
        ),
        "mutuals": _sorted_usernames(
            following_keys & follower_keys,
            following_accounts,
            follower_accounts,
        ),
        "one_way_followers": _sorted_usernames(
            follower_keys - following_keys,
            follower_accounts,
            following_accounts,
        ),
    }


def analyze_archive_path(archive_path: Path) -> Dict[str, List[str]]:
    bundle = analyze_archive_bundle(archive_path)
    return bundle["result"]


def analyze_archive_bundle(archive_path: Path) -> Dict[str, Any]:
    following_items, follower_items, profile_payload = _load_archive_items(archive_path)

    following_accounts = _extract_accounts(following_items, "following")
    follower_accounts = _extract_accounts(follower_items, "follower")
    result = analyze_accounts(following_accounts, follower_accounts)

    return {
        "result": result,
        "counts": {
            "following_total": len(following_accounts),
            "followers_total": len(follower_accounts),
        },
        "profile": _extract_profile_from_payload(profile_payload),
    }


def write_csv(path: Path, header: str, rows: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([header])
        for row in rows:
            writer.writerow([row])


def print_summary(result: Dict[str, List[str]], show: int) -> None:
    print("=== Analysis Summary ===")
    print(f"One-way following (you follow them): {len(result['one_way_following'])}")
    print(f"Mutual follows: {len(result['mutuals'])}")
    print(f"One-way followers (they follow you): {len(result['one_way_followers'])}")

    for key, title in [
        ("one_way_following", "One-way following"),
        ("mutuals", "Mutual follows"),
        ("one_way_followers", "One-way followers"),
    ]:
        values = result[key]
        print(f"\n=== {title} ({len(values)}) ===")
        for name in values[:show]:
            print(f"@{name}")
        if len(values) > show:
            print(f"... and {len(values) - show} more")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze one-way follows from X archive")
    parser.add_argument(
        "--archive",
        required=True,
        help="Path to extracted archive folder or archive zip file",
    )
    parser.add_argument("--show", type=int, default=50, help="Max entries to print per category")
    parser.add_argument(
        "--csv-dir",
        default="",
        help="Optional directory to export CSV files",
    )
    args = parser.parse_args()

    archive_path = Path(args.archive)
    if not archive_path.exists():
        print(f"Archive path not found: {archive_path}")
        return 1

    try:
        result = analyze_archive_path(archive_path)
    except Exception as exc:
        print(f"Failed to analyze archive: {exc}")
        return 1

    print_summary(result, args.show)

    if args.csv_dir:
        csv_dir = Path(args.csv_dir)
        csv_dir.mkdir(parents=True, exist_ok=True)

        write_csv(csv_dir / "one_way_following.csv", "username", result["one_way_following"])
        write_csv(csv_dir / "mutuals.csv", "username", result["mutuals"])
        write_csv(csv_dir / "one_way_followers.csv", "username", result["one_way_followers"])

        print(f"\nCSV exported to: {csv_dir.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
