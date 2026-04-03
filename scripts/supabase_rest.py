from __future__ import annotations

"""
Minimal Supabase PostgREST helpers for environments (like GitHub Actions)
where direct Postgres (TCP/5432) access may be blocked.
"""

import os
from typing import Any
from urllib.parse import quote

import requests


def get_supabase_rest_base_url(supabase_url: str) -> str:
    return supabase_url.rstrip("/") + "/rest/v1"


def auth_headers(service_role_key: str) -> dict[str, str]:
    # PostgREST requires `apikey` and `Authorization: Bearer <token>`
    return {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }


def fetch_table_all(
    supabase_url: str,
    service_role_key: str,
    table: str,
    select: str = "*",
    order_by: str | None = None,
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    """
    Fetch full table via PostgREST using Range pagination.
    """
    base = get_supabase_rest_base_url(supabase_url)
    table_path = quote(table)
    url = f"{base}/{table_path}?select={select}"
    if order_by:
        url += f"&order={quote(order_by)}"

    headers = auth_headers(service_role_key)
    headers["Range"] = f"0-{page_size-1}"

    rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        headers["Range"] = f"{offset}-{offset + page_size - 1}"
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        batch = resp.json()
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    return rows


def upsert_rows(
    supabase_url: str,
    service_role_key: str,
    table: str,
    rows: list[dict[str, Any]],
    on_conflict: str,
) -> None:
    base = get_supabase_rest_base_url(supabase_url)
    table_path = quote(table)
    url = f"{base}/{table_path}?on_conflict={quote(on_conflict)}"

    headers = auth_headers(service_role_key)
    headers["Content-Type"] = "application/json"
    headers["Prefer"] = "resolution=merge-duplicates"

    resp = requests.post(url, headers=headers, json=rows, timeout=60)
    resp.raise_for_status()

