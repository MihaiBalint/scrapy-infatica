# scrapy-infatica
scrapy-infatica provides easy use of Infatica.io proxies with the Scrapy web scraping framework

# Development

This project uses poetry, it is a prerequisite for development / contributions to this project - https://python-poetry.org/

# Requirements

* Python 3.6+
* Requests
* Scrapy

# Documentation

Add the following to your scrapy project settings:

PROXY_ENABLED = True

INFATICA_URL = "https://infatica.io/proxylistbwtraf.php?id=NNNN&hash=02abd...."

DOWNLOADER_MIDDLEWARES = {
    "scrapy_infatica.InfaticaMiddleware": 551,
}
