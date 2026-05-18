# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import urllib.parse

import requests as _requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/meta/leads/webhook"
OAUTH_SCOPES = "pages_manage_ads,pages_manage_metadata,leads_retrieval,pages_show_list"


class MetaLeadsWebhookController(http.Controller):
    """
    Handles the Meta Webhook lifecycle:
      GET  /meta/leads/webhook  — hub.challenge verification
      POST /meta/leads/webhook  — incoming lead notification (HMAC-SHA256 verified)
    """

    # ── GET: Webhook URL Verification ────────────────────────────────────────

    @http.route(
        WEBHOOK_PATH,
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def verify_webhook(self, **kwargs):
        """
        Meta sends a GET to verify the endpoint.
        We echo back hub.challenge only when the verify token matches.
        """
        mode = kwargs.get("hub.mode")
        token = kwargs.get("hub.verify_token")
        challenge = kwargs.get("hub.challenge", "")

        expected_token = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("meta_leads.verify_token", "")
        )

        if mode == "subscribe" and token and token == expected_token:
            _logger.info("Meta webhook: verification challenge accepted.")
            return request.make_response(
                challenge,
                headers=[("Content-Type", "text/plain")],
            )

        _logger.warning(
            "Meta webhook: verification FAILED. mode=%s, token_match=%s",
            mode,
            token == expected_token,
        )
        return request.make_response(
            "Verification failed",
            status=403,
            headers=[("Content-Type", "text/plain")],
        )

    # ── POST: Incoming Lead Notification ─────────────────────────────────────

    @http.route(
        WEBHOOK_PATH,
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def receive_lead(self, **kwargs):
        """
        Receives Meta lead notification, validates HMAC-SHA256 signature,
        and enqueues each lead for async processing.
        Always returns HTTP 200 to Meta immediately.
        """
        raw_body = request.httprequest.get_data(as_text=True)

        if not self._verify_signature(
            raw_body, request.httprequest.headers, request.env
        ):
            _logger.warning("Meta webhook: HMAC signature mismatch — request rejected.")
            return request.make_response(
                json.dumps({"error": "Invalid signature"}),
                status=403,
                headers=[("Content-Type", "application/json")],
            )

        try:
            payload = json.loads(raw_body)
        except (ValueError, TypeError) as exc:
            _logger.error("Meta webhook: JSON parse error: %s", exc)
            return request.make_response(
                json.dumps({"error": "Invalid JSON"}),
                status=400,
                headers=[("Content-Type", "application/json")],
            )

        if payload.get("object") != "page":
            _logger.debug(
                "Meta webhook: ignoring object type=%s", payload.get("object")
            )
            return request.make_response(
                json.dumps({"status": "ignored"}),
                headers=[("Content-Type", "application/json")],
            )

        enqueued = 0
        for entry in payload.get("entry", []):
            page_id = str(entry.get("id", ""))
            for change in entry.get("changes", []):
                if change.get("field") != "leadgen":
                    continue
                value = change.get("value", {})
                meta_lead_id = str(value.get("leadgen_id", ""))
                if not meta_lead_id:
                    continue

                try:
                    # Idempotency check before insert
                    existing = (
                        request.env["meta.lead.queue"]
                        .sudo()
                        .search(
                            [
                                ("meta_lead_id", "=", meta_lead_id),
                            ],
                            limit=1,
                        )
                    )
                    if existing:
                        _logger.info(
                            "Meta webhook: lead %s already queued (state=%s), skipping.",
                            meta_lead_id,
                            existing.state,
                        )
                        # Mark as duplicate if still pending/processing to surface in UI
                        if existing.state in ("pending", "processing"):
                            existing.write({"state": "duplicate"})
                        continue

                    request.env["meta.lead.queue"].sudo().create(
                        {
                            "meta_lead_id": meta_lead_id,
                            "page_id": page_id,
                            "form_id": str(value.get("form_id", "")),
                            "ad_id": str(value.get("ad_id", "")),
                            "adset_id": str(value.get("adset_id", "")),
                            "campaign_id_meta": str(value.get("campaign_id", "")),
                            "raw_payload": json.dumps(value, indent=2),
                            "state": "pending",
                        }
                    )
                    enqueued += 1
                    _logger.info(
                        "Meta webhook: enqueued lead %s from page %s.",
                        meta_lead_id,
                        page_id,
                    )

                except Exception as exc:
                    _logger.exception(
                        "Meta webhook: failed to enqueue lead %s: %s", meta_lead_id, exc
                    )

        return request.make_response(
            json.dumps({"status": "ok", "enqueued": enqueued}),
            headers=[("Content-Type", "application/json")],
        )

    # ── OAuth: Start flow ─────────────────────────────────────────────────────

    @http.route(
        "/meta/oauth/start",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def oauth_start(self, **kwargs):
        """Redirect to Meta OAuth dialog so user can grant pages_manage_ads scope."""
        ICP = request.env["ir.config_parameter"].sudo()
        app_id = ICP.get_param("meta_leads.app_id", "")
        if not app_id:
            return request.make_response(
                "meta_leads.app_id system parameter not set.",
                status=400,
                headers=[("Content-Type", "text/plain")],
            )
        base_url = ICP.get_param("web.base.url", "")
        redirect_uri = base_url.rstrip("/") + "/meta/oauth/callback"
        params = urllib.parse.urlencode(
            {
                "client_id": app_id,
                "redirect_uri": redirect_uri,
                "scope": OAUTH_SCOPES,
                "response_type": "code",
                "state": "odoo_meta_leads",
            }
        )
        return request.redirect(f"https://www.facebook.com/dialog/oauth?{params}")

    # ── OAuth: Callback ───────────────────────────────────────────────────────

    @http.route(
        "/meta/oauth/callback",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def oauth_callback(self, code=None, state=None, error=None, **kwargs):
        """Exchange code → token and store in ir.config_parameter."""
        if error:
            _logger.error("Meta OAuth error: %s", error)
            return request.make_response(
                f"<html><body><h2>OAuth Error</h2><p>{error}</p></body></html>",
                status=400,
                headers=[("Content-Type", "text/html")],
            )
        if not code:
            return request.make_response(
                "<html><body><h2>Error</h2><p>No code received.</p></body></html>",
                status=400,
                headers=[("Content-Type", "text/html")],
            )

        ICP = request.env["ir.config_parameter"].sudo()
        app_id = ICP.get_param("meta_leads.app_id", "")
        app_secret = ICP.get_param("meta_leads.app_secret", "")
        base_url = ICP.get_param("web.base.url", "")
        redirect_uri = base_url.rstrip("/") + "/meta/oauth/callback"

        # Exchange auth code for short-lived token
        resp = _requests.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            timeout=15,
        )
        data = resp.json()
        if "error" in data:
            _logger.error("Meta OAuth token exchange error: %s", data)
            return request.make_response(
                f"<html><body><h2>Token Error</h2><pre>{json.dumps(data, indent=2)}</pre></body></html>",
                status=400,
                headers=[("Content-Type", "text/html")],
            )

        short_token = data.get("access_token", "")

        # Exchange for 60-day long-lived token
        ll_resp = _requests.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            },
            timeout=15,
        )
        ll_data = ll_resp.json()
        long_token = ll_data.get("access_token", short_token)
        expires_in = ll_data.get("expires_in", "unknown")

        # Persist in system parameters
        ICP.set_param("meta_leads.access_token", long_token)
        _logger.info(
            "Meta OAuth: new long-lived token stored (expires_in=%s). Scopes: %s",
            expires_in,
            OAUTH_SCOPES,
        )

        # Get page tokens and store the test business page token
        pages_resp = _requests.get(
            "https://graph.facebook.com/v21.0/me/accounts",
            params={"access_token": long_token, "fields": "id,name,access_token"},
            timeout=15,
        )
        pages_data = pages_resp.json()
        pages_html = ""
        for page in pages_data.get("data", []):
            pid = page.get("id", "")
            pname = page.get("name", "")
            ptoken = page.get("access_token", "")
            # Update any matching meta.lead.config with new page token
            configs = (
                request.env["meta.lead.config"].sudo().search([("page_id", "=", pid)])
            )
            if configs:
                configs.write({"page_access_token": ptoken})
                ICP.set_param(f"meta_leads.page_token_{pid}", ptoken)
                pages_html += (
                    f"<li>✅ <b>{pname}</b> ({pid}) — token updated in config</li>"
                )
            else:
                ICP.set_param(f"meta_leads.page_token_{pid}", ptoken)
                request.env["meta.lead.config"].sudo().create(
                    {
                        "name": f"{pname} (auto-created)",
                        "page_id": pid,
                        "page_access_token": ptoken,
                        "active": True,
                    }
                )
                pages_html += (
                    f"<li>✅ <b>{pname}</b> ({pid}) — config auto-created</li>"
                )

        html = f"""<!DOCTYPE html>
<html>
<head><title>Meta OAuth Complete</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:40px auto;padding:0 20px}}
h2{{color:#1877f2}}.success{{background:#d4edda;border:1px solid #c3e6cb;padding:15px;border-radius:5px}}
ul{{padding-left:20px}}a{{color:#1877f2}}</style></head>
<body>
<h2>✅ Meta OAuth Authorization Complete</h2>
<div class="success">
  <p><strong>Long-lived token stored</strong> (valid ~60 days, expires_in={expires_in}s)</p>
  <p>Scopes granted: <code>{OAUTH_SCOPES}</code></p>
</div>
<h3>Pages with updated tokens:</h3>
<ul>{pages_html or "<li>No pages found</li>"}</ul>
<p>You can now <a href="/web#action=meta_leads_webhook.action_meta_lead_config">open Meta Lead Configs</a> to verify.</p>
</body>
</html>"""
        return request.make_response(html, headers=[("Content-Type", "text/html")])

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _verify_signature(raw_body: str, headers, env) -> bool:
        """
        Verify the X-Hub-Signature-256 header using HMAC-SHA256.
        Meta signs the raw request body with the App Secret.
        """
        signature_header = headers.get("X-Hub-Signature-256", "")
        if not signature_header.startswith("sha256="):
            _logger.debug(
                "Meta webhook: X-Hub-Signature-256 header missing or malformed."
            )
            return False

        received_sig = signature_header[len("sha256=") :]
        app_secret = (
            env["ir.config_parameter"].sudo().get_param("meta_leads.app_secret", "")
        )
        if not app_secret:
            _logger.error(
                'Meta webhook: system parameter "meta_leads.app_secret" is not configured!'
            )
            return False

        expected_sig = hmac.HMAC(
            app_secret.encode("utf-8"),
            raw_body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(received_sig, expected_sig)
