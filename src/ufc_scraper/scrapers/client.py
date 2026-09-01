from __future__ import annotations

from dataclasses import dataclass
import random
import time
from pathlib import Path

import asyncio
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
from playwright.async_api import async_playwright

from .config import BASE_URL, build_url


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROFILE_DIR = ROOT / "data" / "browser_profile"


@dataclass(slots=True)
class UFCStatsClient:
    base_url: str = BASE_URL
    headless: bool = True
    persistent_profile: bool = False
    profile_dir: Path = DEFAULT_PROFILE_DIR
    _playwright: Playwright | None = None
    _browser: Browser | None = None
    _context: BrowserContext | None = None
    _page: Page | None = None

    def __enter__(self) -> "UFCStatsClient":
        self._playwright = sync_playwright().start()
        if self.persistent_profile:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            try:
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=self.headless,
                    viewport={"width": 1440, "height": 900},
                    locale="en-US",
                )
            except Exception:
                # If the profile is locked by a stale browser session, fall back to a normal browser context.
                self._browser = self._playwright.chromium.launch(headless=self.headless)
                self._context = self._browser.new_context(viewport={"width": 1440, "height": 900}, locale="en-US")
        else:
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(viewport={"width": 1440, "height": 900}, locale="en-US")

        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._page is not None:
            self._page.close()
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Client must be entered before accessing the page")
        return self._page

    def _looks_like_bot_check(self, html: str) -> bool:
        lowered = html.lower()
        return any(
            marker in lowered
            for marker in (
                "checking your browser",
                "this site requires javascript",
                "loading…",
                "loading...",
                "verify you are human",
            )
        )

    def get_html(
        self,
        path: str = "",
        *,
        required_selector: str | None = None,
        retries: int = 3,
        retry_delay_seconds: float = 2.0,
        settle_delay_seconds: float = 1.0,
        timeout_ms: int = 45000,
    ) -> str:
        page = self.page
        url = build_url(path) if path else self.base_url
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                except Exception:
                    pass

                if required_selector is not None:
                    page.locator(required_selector).first.wait_for(state="attached", timeout=timeout_ms)

                if settle_delay_seconds > 0:
                    time.sleep(settle_delay_seconds + random.uniform(0.15, 0.75))

                html = page.content()
                if self._looks_like_bot_check(html):
                    raise RuntimeError("Bot-check page detected")

                return html
            except Exception as exc:
                last_error = exc
                if attempt >= retries:
                    break

                time.sleep(retry_delay_seconds + random.uniform(0.5, 1.25))

        raise RuntimeError(f"Failed to load {url}") from last_error

    def get_links(self, selector: str) -> list[str]:
        page = self.page
        return page.locator(selector).evaluate_all(
            "elements => elements.map(element => element.href).filter(Boolean)"
        )


@dataclass(slots=True)
class AsyncUFCStatsClient:
    base_url: str = BASE_URL
    headless: bool = True
    persistent_profile: bool = False
    profile_dir: Path = DEFAULT_PROFILE_DIR
    _playwright: any = None
    _browser: any = None
    _context: any = None
    _page: any = None

    async def __aenter__(self) -> "AsyncUFCStatsClient":
        self._playwright = await async_playwright().start()
        if self.persistent_profile:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            try:
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=self.headless,
                    viewport={"width": 1440, "height": 900},
                    locale="en-US",
                )
            except Exception:
                self._browser = await self._playwright.chromium.launch(headless=self.headless)
                self._context = await self._browser.new_context(viewport={"width": 1440, "height": 900}, locale="en-US")
        else:
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
            self._context = await self._browser.new_context(viewport={"width": 1440, "height": 900}, locale="en-US")

        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._page is not None:
            try:
                await self._page.close()
            except Exception:
                pass
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass

    @property
    def page(self):
        if self._page is None:
            raise RuntimeError("Client must be entered before accessing the page")
        return self._page

    def _looks_like_bot_check(self, html: str) -> bool:
        lowered = html.lower()
        return any(
            marker in lowered
            for marker in (
                "checking your browser",
                "this site requires javascript",
                "loading…",
                "loading...",
                "verify you are human",
            )
        )

    async def get_html(
        self,
        path: str = "",
        *,
        required_selector: str | None = None,
        retries: int = 3,
        retry_delay_seconds: float = 2.0,
        settle_delay_seconds: float = 1.0,
        timeout_ms: int = 45000,
    ) -> str:
        page = self.page
        url = build_url(path) if path else self.base_url
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    await page.wait_for_load_state("networkidle", timeout=timeout_ms)
                except Exception:
                    pass

                if required_selector is not None:
                    await page.locator(required_selector).first.wait_for(state="attached", timeout=timeout_ms)

                if settle_delay_seconds > 0:
                    await asyncio.sleep(settle_delay_seconds + random.uniform(0.15, 0.75))

                html = await page.content()
                if self._looks_like_bot_check(html):
                    raise RuntimeError("Bot-check page detected")

                return html
            except Exception as exc:
                last_error = exc
                if attempt >= retries:
                    break

                await asyncio.sleep(retry_delay_seconds + random.uniform(0.5, 1.25))

        raise RuntimeError(f"Failed to load {url}") from last_error

    async def get_links(self, selector: str) -> list[str]:
        page = self.page
        return await page.locator(selector).evaluate_all(
            "elements => elements.map(element => element.href).filter(Boolean)"
        )
