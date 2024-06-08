import time

import requests

from configurations import CONFIG


class StatusReporter:
    BASE_URL = "https://api.statuspage.io/v1/pages"
    MAX_LATENCY = 0.5

    def __init__(self):
        if not CONFIG.get("statuspage_api_key"):
            print("Uh-oh.")
            self.update = lambda x: None

    def update(self, discord_client):
        self.update_status(discord_client)
        self.update_metric(discord_client)

    def update_status(self, discord_client):
        page_id = CONFIG.get("statuspage_page_id")
        component_id = CONFIG.get("statuspage_component_id")
        url = f"{self.BASE_URL}/{page_id}/components/{component_id}"
        headers = {"Authorization": f"OAuth {CONFIG.get('statuspage_api_key')}"}

        status = "operational"
        if discord_client.latency > self.MAX_LATENCY:
            status = "degraded_performance"
        elif (
                discord_client.user is None
                or not discord_client.is_ready()
                or discord_client.is_closed()
        ):
            status = "degraded_performance"
        component = {"component": {"status": status}}

        r = requests.patch(url, headers=headers, json=component)
        r.raise_for_status()

    def update_metric(self, discord_client):
        page_id = CONFIG.get("statuspage_page_id")
        metric_id = CONFIG.get("statuspage_metric_id")
        url = f"{self.BASE_URL}/{page_id}/metrics/data"
        headers = {"Authorization": f"OAuth {CONFIG.get('statuspage_api_key')}"}

        if not (latency := discord_client.latency * 1000):
            return

        payload = {
            "data": {
                metric_id: [{
                    'timestamp': int(time.time()),
                    'value': latency
                }]
            }
        }
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
