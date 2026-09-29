import unittest
from unittest.mock import patch

import private_settings as PS


class PrivateSettingsTests(unittest.TestCase):
    def test_defaults_are_neutral(self):
        s = PS.parse("")
        self.assertEqual(s["state"], "")
        self.assertEqual(s["watch"], [])
        self.assertEqual(s["modes"]["food"], "off")
        self.assertEqual(s["problems"], [])

    def test_modes_state_and_watch_words(self):
        s = PS.parse("""
            # comment
            food: push
            Cheap: QUIET
            state: nsw
            watch: dyson, lego ,
        """)
        self.assertEqual(s["modes"]["food"], "push")
        self.assertEqual(s["modes"]["cheap"], "quiet")
        self.assertEqual(s["state"], "NSW")
        self.assertEqual(s["watch"], ["dyson", "lego"])

    def test_bad_lines_reported_without_breaking_the_rest(self):
        s = PS.parse("food: loud\nstate: XYZ\nnonsense\nfreebies: off")
        self.assertEqual(len(s["problems"]), 3)
        self.assertEqual(s["modes"]["food"], "off")        # unchanged default
        self.assertEqual(s["modes"]["freebies"], "off")
        self.assertEqual(s["state"], "")

    def test_strongest_mode_wins(self):
        s = PS.parse("cheap: quiet\nbig_discounts: push")
        self.assertEqual(PS.mode_for(["under $5", "72% off"], s), "push")
        self.assertEqual(PS.mode_for(["under $5"], s), "quiet")

    def test_everything_off_means_not_sent(self):
        s = PS.parse("cheap: off")
        self.assertEqual(PS.mode_for(["under $5"], s), "off")
        self.assertEqual(PS.mode_for(["big store"], s), "off")   # a boost alone is not a category

    def test_food_percent_is_food_not_big_discount(self):
        s = PS.parse("food: quiet\nbig_discounts: push")
        self.assertEqual(PS.mode_for(["FOOD", "55% off food"], s), "quiet")

    def test_tech_rule_override_and_default(self):
        s = PS.parse("tech: quiet\nps5_consoles: off\nlaptops: push")
        self.assertEqual(PS.mode_for(["Tech: Laptops"], s), "push")
        self.assertEqual(PS.mode_for(["Tech: PS5 consoles"], s), "off")
        self.assertEqual(PS.mode_for(["Tech: Audio & wearables"], s), "quiet")

    def test_environment_wins_over_local_file(self):
        with patch.dict("os.environ", {"ALERT_SETTINGS": "food: push\nstate: VIC"}):
            s = PS.load("/nonexistent")
        self.assertEqual((s["modes"]["food"], s["state"]), ("push", "VIC"))


class QuietDeliveryTests(unittest.TestCase):
    def test_quiet_uses_low_priority_and_off_sends_nothing(self):
        import ozwatch
        sent = []
        with patch.object(ozwatch, "NTFY_TOPIC", "t"), \
             patch("urllib.request.urlopen", side_effect=lambda req, timeout: sent.append(req) or _Resp()):
            ozwatch.push("title", "body", "https://x", False, "quiet")
            ozwatch.push("title", "body", "https://x", True, "push")
            ozwatch.push("title", "body", "https://x", True, "off")
        self.assertEqual([r.get_header("Priority") for r in sent], [PS.QUIET_PRIORITY, "5"])


class _Resp:
    def read(self):
        return b""


if __name__ == "__main__":
    unittest.main()
