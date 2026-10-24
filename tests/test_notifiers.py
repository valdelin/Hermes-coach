# -*- coding: utf-8 -*-
import os
import unittest
from unittest import mock

from src.notifiers import get_notifier, NullNotifier
from src.notifiers.telegram import TelegramNotifier


class NotifierTest(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_no_creds_returns_null(self):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        n = get_notifier()
        self.assertIsInstance(n, NullNotifier)
        self.assertFalse(n.send("t", "m"))

    def test_telegram_disabled_when_missing_creds(self):
        n = TelegramNotifier(token="", chat_id="")
        self.assertFalse(n.enabled())
        self.assertFalse(n.send("t", "m"))

    def test_telegram_send_best_effort(self):
        os.environ["TELEGRAM_BOT_TOKEN"] = "x"
        os.environ["TELEGRAM_CHAT_ID"] = "1"
        n = TelegramNotifier()
        self.assertTrue(n.enabled())
        with mock.patch("urllib.request.urlopen") as m:
            class R:
                status = 200
            m.return_value.__enter__.return_value = R()
            self.assertTrue(n.send("Titulo", "mensagem"))
        self.assertTrue(m.called)

    def test_telegram_send_failure_returns_false(self):
        os.environ["TELEGRAM_BOT_TOKEN"] = "x"
        os.environ["TELEGRAM_CHAT_ID"] = "1"
        n = TelegramNotifier()
        with mock.patch("urllib.request.urlopen", side_effect=Exception("fail")):
            self.assertFalse(n.send("t", "m"))


if __name__ == "__main__":
    unittest.main()
