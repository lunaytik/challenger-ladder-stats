import time

import requests

from src.rate_limiter import RateLimiter

retry_timeout = [5, 10, 20, 30]


class RiotAPI:
    def __init__(self, limiter: RateLimiter, headers: dict[str, str]):
        self.headers = headers
        self.limiter = limiter

    def safe_get(self, url: str, retry_count: int = 0):
        self.limiter.wait_if_needed()

        try:
            resp = requests.get(url, headers=self.headers)
        except requests.exceptions.ConnectionError as e:
            if retry_count >= 4:
                raise RiotAPIError(f"Connexion impossible après plusieurs tentatives : {e}") from e
            wait_time = retry_timeout[retry_count]
            time.sleep(wait_time)
            return self.safe_get(url, retry_count + 1)

        self.limiter.record_call()

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 5))
            time.sleep(retry_after)
            return self.safe_get(url, retry_count + 1)
        elif resp.status_code == 404:
            raise RiotNotFoundError("Resource not found", resp.status_code)
        elif resp.status_code == 400:
            raise RiotBadRequestError("Bad request", resp.status_code)
        elif resp.status_code == 401 or resp.status_code == 403:
            raise RiotUnauthorizedError("Unauthorized", resp.status_code)
        elif (
            resp.status_code == 500
            or resp.status_code == 502
            or resp.status_code == 503
            or resp.status_code == 504
        ):
            if retry_count > 4:
                raise RiotServerError("Internal server error", resp.status_code)
            retry_after = retry_timeout[retry_count]
            time.sleep(retry_after)
            return self.safe_get(url, retry_count + 1)

        return resp.json()


class RiotAPIError(Exception):
    pass


class RiotNotFoundError(RiotAPIError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class RiotServerError(RiotAPIError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class RiotUnauthorizedError(RiotAPIError):
    def __init__(self, message, status_code=None):
        super().__init__(message)


class RiotBadRequestError(RiotAPIError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
