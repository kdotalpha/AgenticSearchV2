import csv
import io
from concurrent.futures import ThreadPoolExecutor

import requests


class PayiClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "xproxy-api-key": api_key,
            "Content-Type": "application/json",
        })

    def fetch_report(self, report_id: str, from_date: str, to_date: str) -> list[dict]:
        resp = self.session.get(
            f"{self.base_url}/api/v1/reports/{report_id}",
            params={"from": from_date, "to": to_date},
        )
        resp.raise_for_status()
        text = resp.text.lstrip("﻿")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    def fetch_multiple(self, report_ids: list[str], from_date: str, to_date: str) -> dict[str, list[dict]]:
        results = {}

        def _fetch(rid):
            return rid, self.fetch_report(rid, from_date, to_date)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_fetch, rid) for rid in report_ids]
            for future in futures:
                rid, rows = future.result()
                results[rid] = rows

        return results
