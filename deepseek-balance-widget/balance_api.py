import requests

BALANCE_URL = "https://api.deepseek.com/user/balance"
TIMEOUT = 10


class BalanceError(Exception):
    pass


class BalanceInfo:
    def __init__(self, is_available, currency, total_balance, granted_balance, topped_up_balance):
        self.is_available = is_available
        self.currency = currency
        self.total_balance = total_balance
        self.granted_balance = granted_balance
        self.topped_up_balance = topped_up_balance

    @classmethod
    def from_response(cls, data):
        bi = data["balance_infos"][0]
        return cls(
            is_available=data["is_available"],
            currency=bi["currency"],
            total_balance=float(bi["total_balance"]),
            granted_balance=float(bi["granted_balance"]),
            topped_up_balance=float(bi["topped_up_balance"]),
        )

    def __str__(self):
        return f"Balance({self.currency} {self.total_balance:.2f}, available={self.is_available})"


def fetch_balance(api_key):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    try:
        resp = requests.get(BALANCE_URL, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise BalanceError(f"network error: {e}") from e

    if resp.status_code == 401:
        raise BalanceError("invalid API key (401)")
    if resp.status_code != 200:
        raise BalanceError(f"API error: HTTP {resp.status_code}")

    return BalanceInfo.from_response(resp.json())
