import logging
import time
from collections import deque

logger = logging.getLogger(__name__)


def _clean(target_deque: deque, window: int):
    now = time.time()
    while len(target_deque) > 0 and now - target_deque[0] > window:
        target_deque.popleft()


def _check_limit(target_deque: deque, window: int, limit: int):
    now = time.time()
    if len(target_deque) >= limit:
        wait_time = (target_deque[0] + window) - now
        if wait_time >= 1:
            logger.info(f"Rate limit atteint ({limit} req/{window}s) -> attente {wait_time:.1f}s")
        time.sleep(wait_time)


class RateLimiter:
    """
    thresholds : liste de tuples (limit, window)
        limit  -> nombre max de requêtes autorisées
        window -> durée de la fenêtre en secondes

    Exemple : [(20, 1), (100, 120)]
    -> 20 requêtes max par seconde, 100 max par 2 minutes
    """

    def __init__(self, thresholds: list[tuple[int, int]]):
        self.thresholds = [
            {"limit": limit, "window": window, "deque": deque()} for limit, window in thresholds
        ]

    def wait_if_needed(self):
        for threshold in self.thresholds:
            _clean(threshold["deque"], threshold["window"])
            _check_limit(threshold["deque"], threshold["window"], threshold["limit"])

    def record_call(self):
        now = time.time()
        for threshold in self.thresholds:
            threshold["deque"].append(now)
