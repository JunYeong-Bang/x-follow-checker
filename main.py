import argparse
import os
import sys
from typing import Dict, List, Set

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.x.com/2"


def _auth_headers(bearer_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {bearer_token}"}


def _paged_get_users(url: str, bearer_token: str, max_results: int = 1000) -> Set[str]:
    """Collect all user handles from a paginated endpoint."""
    handles: Set[str] = set()
    pagination_token = None

    while True:
        params = {
            "max_results": max_results,
            "user.fields": "username",
        }
        if pagination_token:
            params["pagination_token"] = pagination_token

        response = requests.get(url, headers=_auth_headers(bearer_token), params=params, timeout=30)

        if response.status_code != 200:
            raise RuntimeError(
                f"API error {response.status_code}: {response.text[:300]}"
            )

        payload = response.json()
        data = payload.get("data", [])
        for user in data:
            username = user.get("username")
            if username:
                handles.add(username.lower())

        meta = payload.get("meta", {})
        pagination_token = meta.get("next_token")
        if not pagination_token:
            break

    return handles


def get_following(user_id: str, bearer_token: str) -> Set[str]:
    url = f"{BASE_URL}/users/{user_id}/following"
    return _paged_get_users(url, bearer_token)


def get_followers(user_id: str, bearer_token: str) -> Set[str]:
    url = f"{BASE_URL}/users/{user_id}/followers"
    return _paged_get_users(url, bearer_token)


def analyze(following: Set[str], followers: Set[str]) -> Dict[str, List[str]]:
    one_way_following = sorted(following - followers)
    mutuals = sorted(following & followers)
    one_way_followers = sorted(followers - following)

    return {
        "one_way_following": one_way_following,
        "mutuals": mutuals,
        "one_way_followers": one_way_followers,
    }


def print_summary(result: Dict[str, List[str]]) -> None:
    print("=== Analysis Summary ===")
    print(f"One-way following (you follow them): {len(result['one_way_following'])}")
    print(f"Mutual follows: {len(result['mutuals'])}")
    print(f"One-way followers (they follow you): {len(result['one_way_followers'])}")


def print_list(title: str, values: List[str], limit: int) -> None:
    print(f"\n=== {title} ({len(values)}) ===")
    for name in values[:limit]:
        print(f"@{name}")
    if len(values) > limit:
        print(f"... and {len(values) - limit} more")


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Find one-way follows using X API v2"
    )
    parser.add_argument("--user-id", default=os.getenv("X_USER_ID"), help="Your X numeric user id")
    parser.add_argument(
        "--bearer-token",
        default=os.getenv("X_BEARER_TOKEN"),
        help="X API Bearer token",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=50,
        help="How many IDs to print per category",
    )
    args = parser.parse_args()

    if not args.user_id or not args.bearer_token:
        print("Missing credentials. Set X_USER_ID and X_BEARER_TOKEN in .env or pass arguments.")
        return 1

    try:
        following = get_following(args.user_id, args.bearer_token)
        followers = get_followers(args.user_id, args.bearer_token)
    except Exception as exc:
        print(f"Failed to fetch data: {exc}")
        return 1

    result = analyze(following, followers)
    print_summary(result)

    print_list("One-way following", result["one_way_following"], args.show)
    print_list("Mutual follows", result["mutuals"], args.show)
    print_list("One-way followers", result["one_way_followers"], args.show)

    return 0


if __name__ == "__main__":
    sys.exit(main())
