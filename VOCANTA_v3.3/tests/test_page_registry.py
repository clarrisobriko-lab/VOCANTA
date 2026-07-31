import unittest

from automation.page_registry import PageRegistry


class FakeLocator:
    def __init__(self, count):
        self.value = count

    def count(self):
        return self.value


class FakePage:
    def __init__(self, url, form_controls=0):
        self.url = url
        self.form_controls = form_controls
        self.closed = False

    def is_closed(self):
        return self.closed

    def locator(self, _selector):
        return FakeLocator(self.form_controls)

    def wait_for_timeout(self, _milliseconds):
        return None


class FakeContext:
    def __init__(self, pages):
        self.pages = list(pages)
        self.callback = None

    def on(self, event, callback):
        if event == "page":
            self.callback = callback

    def add_page(self, page):
        self.pages.append(page)
        if self.callback:
            self.callback(page)


class PageRegistryTests(unittest.TestCase):
    def test_new_application_popup_becomes_active(self):
        original = FakePage("https://example.com/job", form_controls=0)
        context = FakeContext([original])
        registry = PageRegistry(context)
        before = registry.snapshot()
        popup = FakePage(
            "https://jobs.lever.co/example/role",
            form_controls=4,
        )
        context.add_page(popup)
        selected = registry.after_action(original, before, timeout_ms=1)
        self.assertIs(selected, popup)

    def test_closed_original_rebinds_to_live_form(self):
        original = FakePage("https://example.com/job")
        popup = FakePage(
            "https://boards.greenhouse.io/example/jobs/1",
            form_controls=3,
        )
        context = FakeContext([original, popup])
        registry = PageRegistry(context)
        original.closed = True
        self.assertIs(registry.recover(original), popup)

    def test_no_live_page_returns_none(self):
        page = FakePage("https://example.com/job")
        context = FakeContext([page])
        registry = PageRegistry(context)
        page.closed = True
        self.assertIsNone(registry.recover(page))


if __name__ == "__main__":
    unittest.main()
