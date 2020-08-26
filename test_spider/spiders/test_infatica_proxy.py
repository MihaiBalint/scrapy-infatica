# -*- coding: utf-8 -*-
import scrapy
import logging

from scrapy.http import Request

logger = logging.getLogger(__name__)


class TestInfaticaProxySpider(scrapy.Spider):
    name = "test_infatica_proxy"
    allowed_domains = ["github.com", "google.com"]
    start_urls = ["http://github.com/"]

    def __init__(self):
        self.session = "create"

    def start_requests(self):
        requests = []
        requests.append(
            Request(
                "https://github.com/",
                meta={"handle_httpstatus_all": True, "dont_filter": True},
                headers=self._get_headers(host="github.com"),
            )
        )
        requests.append(
            # Works
            Request(
                "https://google.com/",
                meta={"handle_httpstatus_all": True, "dont_filter": True},
                headers=self._get_headers(host="google.com"),
            )
        )

        return requests

    def parse(self, response):
        if response.status in [0, 403]:
            return response.request.copy()

    def _get_headers(self, json: bool = False, host: str = None):
        host = host or "github.com"
        accept_anything = (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        )
        accept_anything = "application/json"
        return {
            "X-Crawlera-Session": self.session,
            "Host": host,
            "Origin": f"https://{host}",
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "application/json" if json else accept_anything,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "TE": "Trailers",
            "X-Referer": "null",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
