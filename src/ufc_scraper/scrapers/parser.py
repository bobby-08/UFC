from __future__ import annotations

from bs4 import BeautifulSoup


class UFCStatsParser:
    def soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def text(self, element, default: str = "") -> str:
        if element is None:
            return default
        return element.get_text(" ", strip=True)

    def attr(self, element, name: str, default: str = "") -> str:
        if element is None:
            return default
        value = element.get(name, default)
        return default if value is None else str(value)

    def texts(self, elements) -> list[str]:
        return [element.get_text(" ", strip=True) for element in elements]

    def links(self, root, selector: str) -> list[str]:
        return [str(link.get("href", "")) for link in root.select(selector)]
