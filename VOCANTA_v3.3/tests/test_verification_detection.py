import unittest

from automation.browser import _detect_human_verification


class FakeLocator:
    def __init__(self, *, count=0, visible=True, text=""):
        self._count = count
        self._visible = visible
        self._text = text

    def count(self):
        return self._count

    def nth(self, index):
        return self

    def is_visible(self):
        return self._visible

    def inner_text(self):
        return self._text


class FakePage:
    def __init__(self, url, mapping, body_text=""):
        self.url = url
        self.mapping = mapping
        self.body_text = body_text

    def locator(self, selector):
        if selector == "body":
            return FakeLocator(count=1, text=self.body_text)
        return FakeLocator(count=self.mapping.get(selector, 0))


class VerificationDetectionTests(unittest.TestCase):
    def test_greenhouse_standard_form_is_not_captcha(self):
        page = FakePage(
            "https://job-boards.greenhouse.io/canonical/jobs/1",
            {
                'input[type="email"]': 1,
                'input[type="file"]': 1,
                'form input:not([type="hidden"])': 5,
            },
            body_text="Apply for this job First Name Last Name Email Resume CV",
        )
        decision = _detect_human_verification(page)
        self.assertFalse(decision.blocked)
        self.assertEqual(decision.reasons, ())

    def test_visible_recaptcha_widget_is_blocked(self):
        selector = 'iframe[src*="recaptcha" i], iframe[title*="recaptcha" i]'
        page = FakePage("https://example.com/apply", {selector: 1})
        decision = _detect_human_verification(page)
        self.assertTrue(decision.blocked)
        self.assertIn("visible reCAPTCHA iframe", decision.reasons[0])

    def test_challenge_text_without_form_is_blocked(self):
        page = FakePage(
            "https://example.com/apply",
            {},
            body_text="Verify you are human to continue",
        )
        decision = _detect_human_verification(page)
        self.assertTrue(decision.blocked)
        self.assertIn("visible challenge text", decision.reasons[0])

    def test_hidden_keyword_in_page_source_is_irrelevant(self):
        page = FakePage(
            "https://job-boards.greenhouse.io/example/jobs/2",
            {'input[type="email"]': 1},
            body_text="Apply for this job",
        )
        decision = _detect_human_verification(page)
        self.assertFalse(decision.blocked)


if __name__ == "__main__":
    unittest.main()
