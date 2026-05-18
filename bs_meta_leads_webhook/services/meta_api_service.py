# -*- coding: utf-8 -*-
import logging

import requests

_logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class MetaAPIService:
    """
    Thin client for Meta Graph API.
    Used to retrieve full lead field values after receiving a webhook notification.
    """

    def __init__(self, env):
        self.env = env
        self.timeout = 15

    def fetch_lead(self, lead_id: str, page_access_token: str) -> dict:
        """
        Fetch a single lead's complete field data from the Graph API.

        Returns a dict containing id, created_time, field_data, ad_id, etc.
        Raises RuntimeError on API errors or network issues.
        """
        url = f"{GRAPH_API_BASE}/{lead_id}"
        params = {
            "fields": "id,created_time,ad_id,adset_id,campaign_id,form_id,field_data",
            "access_token": page_access_token,
        }

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Graph API timeout fetching lead {lead_id}")
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text if exc.response else "no body"
            raise RuntimeError(
                f"Graph API HTTP error for lead {lead_id}: {exc} — {body}"
            )
        except Exception as exc:
            raise RuntimeError(f"Graph API unexpected error for lead {lead_id}: {exc}")

        if "error" in data:
            err = data["error"]
            raise RuntimeError(
                f"Graph API error (code {err.get('code', '?')}): {err.get('message', 'unknown')}"
            )

        return data

    def fetch_form_questions(self, form_id: str, page_access_token: str) -> dict:
        """Fetch lead form question definitions (useful for dynamic field mapping)."""
        url = f"{GRAPH_API_BASE}/{form_id}"
        params = {
            "fields": "id,name,questions",
            "access_token": page_access_token,
        }
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"Graph API timeout fetching form questions for {form_id}"
            )
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text if exc.response else "no body"
            raise RuntimeError(
                f"Graph API HTTP error for form {form_id}: {exc} — {body}"
            )
        except Exception as exc:
            raise RuntimeError(f"Graph API unexpected error for form {form_id}: {exc}")

        if "error" in data:
            err = data["error"]
            raise RuntimeError(
                f"Graph API error (code {err.get('code', '?')}): {err.get('message', 'unknown')}"
            )

        return data
