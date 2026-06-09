from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from .config import BASE_URL, build_url


@dataclass(slots=True)
class UFCStatsClient:
    base_url: str = BASE_URL
    headless: bool = True
    _playwright: Playwright | None = None
    _browser: Browser | None = None
    _page: Page | None = None

    def __enter__(self) -> "UFCStatsClient":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._page is not None:
            self._page.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Client must be entered before accessing the page")
        return self._page

    def get_html(self, path: str = "") -> str:
        page = self.page
        url = build_url(path) if path else self.base_url
        page.goto(url, wait_until="networkidle")
        return page.content()

    def get_links(self, selector: str) -> list[str]:
        page = self.page
        return page.locator(selector).evaluate_all(
            "elements => elements.map(element => element.href).filter(Boolean)"
        )
