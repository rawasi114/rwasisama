"""Thin HTTP client that lets Odoo models talk to the FastAPI backend."""

from odoo import models, fields, api  # noqa: F401  (Odoo runtime only)


class PricingApiClient(models.AbstractModel):
    _name = "rps.api.client"
    _description = "Rawasi Pricing Intelligence API client"

    def _base_url(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rps.api_base_url", "http://localhost:8000")
        )

    def request(self, method, path, **kwargs):
        import requests

        url = f"{self._base_url()}{path}"
        response = requests.request(method, url, timeout=60, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}
