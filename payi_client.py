import csv
import io
from concurrent.futures import ThreadPoolExecutor

import requests

# The Pay-i API returns compact PascalCase CSV headers; the rest of the app
# (prompts, transforms, docs) speaks the Query Builder's display names.
COLUMN_NAME_MAP = {
    "DateDay": "Day",
    "DateMonth": "Month",
    "DateHour": "Hour",
    "DateMinute": "Minute",
    "UseCase": "Use Case",
    "UseCaseVersion": "Use Case Version",
    "UseCaseResponseCode": "Use Case Response Code",
    "InstanceId": "Instance ID",
    "ResponseCode": "Response Code",
    "RequestLatency": "Request: Latency",
    "RequestId": "Request: ID",
    "RequestDate": "Request: Date",
    "RequestSpend": "Request: Spend",
}


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
            timeout=120,
        )
        resp.raise_for_status()
        text = resp.text.lstrip("﻿")
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames:
            reader.fieldnames = [COLUMN_NAME_MAP.get(name, name) for name in reader.fieldnames]
        rows = list(reader)

        # Filter rows by date range if a Day/Month column exists
        for date_col in ("Day", "Month"):
            if rows and date_col in rows[0]:
                filtered = []
                for row in rows:
                    date_val = row[date_col][:10] if row.get(date_col) else ""
                    if from_date <= date_val <= to_date:
                        filtered.append(row)
                if filtered:
                    return filtered
                return rows
        return rows

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
