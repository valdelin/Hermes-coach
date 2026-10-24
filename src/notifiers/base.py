# -*- coding: utf-8 -*-
from __future__ import annotations
from abc import ABC, abstractmethod


class Notifier(ABC):
    @abstractmethod
    def send(self, title: str, message: str, level: str = "info") -> bool:
        raise NotImplementedError


class NullNotifier(Notifier):
    def send(self, title: str, message: str, level: str = "info") -> bool:
        return False
