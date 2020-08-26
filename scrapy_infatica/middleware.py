import random
import requests
import logging
from itertools import cycle
from collections import defaultdict
from urllib.parse import urlparse
from scrapy.exceptions import NotConfigured
from twisted.internet.error import (
    ConnectionRefusedError,
    ConnectionDone,
    ConnectionLost,
)
from .utils import exp_backoff, linear_backoff

logger = logging.getLogger(__name__)


class InfaticaMiddleware(object):
    @classmethod
    def from_crawler(cls, crawler):
        inst = cls(crawler.settings)
        inst.crawler = crawler
        return inst

    def __init__(self, settings):
        endpoint_list = get_proxy_endpoints(settings.get("INFATICA_URL"))
        self.is_enabled = settings.getbool("PROXY_ENABLED", False)
        self.is_enabled = self.is_enabled and len(endpoint_list) > 0

        self.protocol = "http://"
        self.endpoints = cycle(endpoint_list)
        if self.is_enabled:
            for n in range(random.randint(0, 100)):
                next(self.endpoints)

        self.backoff_step = 15
        self.backoff_max = 180
        self.backoff = linear_backoff(self.backoff_step, self.backoff_max)
        self.crawler = None
        self._saved_delays = defaultdict(lambda: None)

    def process_request(self, request, spider):
        session = request.headers.get(b"X-Crawlera-Session")
        if self.is_enabled is False:
            return

        session = session.decode() if session is not None else None
        if session is None or session == "create" or ":" not in session:
            endpoint = request.meta.get("x-proxy-session") or next(self.endpoints)
            session = f"{endpoint}"
            logger.info(f"Request using new proxy: {endpoint}")

        request.meta["proxy"] = f"{self.protocol}{session}"
        request.meta["x-proxy-session"] = session
        request.headers[b"X-Crawlera-Session"] = session
        check_host_header(request)
        check_transfer_encoding_header(request)

    def process_response(self, request, response, spider):
        request_proxy_session = request.meta.get("x-proxy-session")
        if request_proxy_session is not None:
            response.headers[b"X-Crawlera-Session"] = request_proxy_session

        key = self._get_slot_key(request)
        self._restore_original_delay(request)

        if self._is_banned(response):
            logger.error(f"Response body: \n\n{response.body_as_unicode()}\n\n")
            self._rotate_proxy(request)

        return response

    def process_exception(self, request, exception, spider):
        if not self._is_enabled_for_request(request):
            return
        if isinstance(
            exception, (ConnectionRefusedError, ConnectionDone, ConnectionLost)
        ):
            self._rotate_proxy(request, reason="conn_refused")

    def _is_enabled_for_request(self, request):
        dont_proxy = request.meta.get("dont_proxy", False)
        return self.is_enabled and not dont_proxy

    def _is_banned(self, response):
        return response.status == 502

    def _rotate_proxy(self, request, reason="proxy_rotation"):
        endpoint = next(self.endpoints)
        logger.info(f"Received 502 response, using new proxy: {endpoint}")
        request.meta["proxy"] = f"{self.protocol}{endpoint}"
        request.meta["x-proxy-session"] = endpoint
        request.headers[b"X-Crawlera-Session"] = endpoint

        self._set_custom_delay(request, next(self.backoff), reason=reason)

    def _get_slot_key(self, request):
        return request.meta.get("download_slot")

    def _get_slot(self, request):
        key = self._get_slot_key(request)
        return key, self.crawler.engine.downloader.slots.get(key)

    def _set_custom_delay(self, request, delay, reason=None):
        """Set custom delay for slot and save original one."""
        key, slot = self._get_slot(request)
        if not slot:
            return
        if self._saved_delays[key] is None:
            self._saved_delays[key] = slot.delay
        slot.delay = delay

    def _restore_original_delay(self, request):
        """Restore original delay for slot if it was changed."""
        key, slot = self._get_slot(request)
        if not slot:
            return
        if self._saved_delays[key] is not None:
            slot.delay, self._saved_delays[key] = self._saved_delays[key], None


def check_transfer_encoding_header(request):
    """Remove TE headers, proxy service does not support TE headers at this time"""
    for h in list(request.headers.keys()):
        if h.lower() in [b"te", b"transfer-encoding"]:
            logger.warning(f"Dropping unsupported header: {h}")
            del request.headers[h]


def check_host_header(request):
    """if the host header does not match, the proxy service gets confused"""
    host_header = None
    host_header_key = None
    for h in request.headers.keys():
        if h.lower() == b"host" and request.headers[h]:
            host_header = request.headers[h].decode("utf8")
            host_header_key = h
            break
    if host_header is None:
        return
    url_host = urlparse(request.url).netloc
    if host_header.strip() != url_host.strip():
        logger.debug(f"Correcting host header from {host_header} to {url_host}")
        request.headers[host_header_key] = url_host.encode("utf8")


def get_proxy_endpoints(proxy_pool_url: str):
    if proxy_pool_url is None:
        logger.warning(
            "Proxy disabled, missing INFATICA_URL configuration in spider settings"
        )
        return []

    logger.info("Fetching proxy pool from infatica.io")
    response = requests.get(proxy_pool_url)
    if response.status_code not in [200]:
        raise ValueError(
            f"Failed to fetch proxy pool from {proxy_pool_url}, received: {response.status_code}"
        )

    pool = response.text
    proxies = pool.split("\n")
    usable_proxies = [p.strip() for p in proxies if len(p.strip()) > 0]
    logger.info(f"Using {len(usable_proxies)} proxy endpoints from infatica.io")

    return usable_proxies
