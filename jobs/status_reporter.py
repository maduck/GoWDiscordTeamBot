import requests

from configurations import CONFIG


class StatusReporter:
    BASE_URL = "https://api.statuspage.io/v1/pages"
    MAX_LATENCY = 0.5

    def __init__(self):
        if not CONFIG.get("statuspage_api_key"):
            self.update = lambda x: None

    def update(self, discord_client):
        page_id = CONFIG.get("STATUSPAGE_PAGE_ID")
        component_id = CONFIG.get("STATUSPAGE_COMPONENT_ID")
        url = f"{self.BASE_URL}/{page_id}/components/{component_id}"
        headers = {"Authorization": f"OAuth {CONFIG.get('STATUSPAGE_API_KEY')}"}

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
