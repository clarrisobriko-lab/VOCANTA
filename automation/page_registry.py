import time
from typing import Any


FORM_SIGNAL_SELECTOR = (
    'form, input[type="file"], input[type="email"], '
    'input[name*="email" i], textarea, select'
)
ATS_HOST_MARKERS = (
    "greenhouse",
    "lever.co",
    "ashbyhq",
    "smartrecruiters",
    "workday",
    "myworkdayjobs",
)


def page_is_live(page: Any) -> bool:
    try:
        return page is not None and not page.is_closed()
    except Exception:
        return False


def page_url(page: Any) -> str:
    try:
        return str(page.url or "")
    except Exception:
        return ""


def _page_score(page: Any, preferred: Any, recency: int) -> int:
    url = page_url(page).lower()
    score = min(recency, 20)
    if page is preferred:
        score += 3
    if url and url != "about:blank":
        score += 5
    if any(marker in url for marker in ATS_HOST_MARKERS):
        score += 12
    try:
        controls = int(page.locator(FORM_SIGNAL_SELECTOR).count())
    except Exception:
        controls = 0
    score += min(controls, 8) * 6
    return score


class PageRegistry:
    def __init__(self, context: Any) -> None:
        self.context = context
        self.observed: list[Any] = []
        for page in self._context_pages():
            self._observe(page)
        try:
            context.on("page", self._observe)
        except Exception:
            pass

    def _observe(self, page: Any) -> None:
        if page not in self.observed:
            self.observed.append(page)

    def _context_pages(self) -> list[Any]:
        try:
            pages = list(self.context.pages)
        except Exception:
            return []
        for page in pages:
            self._observe(page)
        return pages

    def snapshot(self) -> set[int]:
        return {id(page) for page in self._context_pages()}

    def select(self, preferred: Any = None) -> Any | None:
        live = [page for page in self._context_pages() if page_is_live(page)]
        if not live:
            live = [page for page in self.observed if page_is_live(page)]
        if not live:
            return None
        ranked = [
            (_page_score(page, preferred, index), index, page)
            for index, page in enumerate(live)
        ]
        return max(ranked, key=lambda item: (item[0], item[1]))[2]

    def after_action(
        self,
        preferred: Any,
        before: set[int] | None = None,
        timeout_ms: int = 3500,
    ) -> Any:
        before = before or set()
        deadline = time.monotonic() + timeout_ms / 1000
        selected = self.select(preferred) or preferred
        while time.monotonic() < deadline:
            live = [
                page
                for page in self._context_pages()
                if page_is_live(page)
            ]
            new_pages = [page for page in live if id(page) not in before]
            if new_pages:
                candidate = self.select(new_pages[-1])
                if candidate is not None and page_url(candidate) != "about:blank":
                    return candidate
            candidate = self.select(preferred)
            if candidate is not None:
                selected = candidate
                if candidate is not preferred and page_url(candidate) != "about:blank":
                    return candidate
            try:
                if page_is_live(selected):
                    selected.wait_for_timeout(200)
                else:
                    time.sleep(0.2)
            except Exception:
                time.sleep(0.2)
        return self.select(selected) or selected

    def recover(self, preferred: Any = None) -> Any | None:
        if page_is_live(preferred):
            selected = self.select(preferred)
            return selected or preferred
        return self.select()
