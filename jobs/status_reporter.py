import time

import aiohttp

from configurations import CONFIG


class StatusReporter:
    BASE_URL = "https://api.statuspage.io/v1/pages"
    MAX_LATENCY = 0.5

    def __init__(self):
        self.session = None

    async def update(self, discord_client):
        if not CONFIG.get("statuspage_api_key"):
            return
        self.session = aiohttp.ClientSession(raise_for_status=True)
        await self.update_status(discord_client)
        await self.update_metric(discord_client)
        await self.session.close()

    async def update_status(self, discord_client):
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

        async with self.session.patch(url, headers=headers, json=component):
            pass

    async def update_metric(self, discord_client):
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
        async with self.session.post(url, headers=headers, json=payload):
            pass
