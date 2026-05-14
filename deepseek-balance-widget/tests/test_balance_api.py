import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from balance_api import fetch_balance, BalanceError, BalanceInfo


def test_balance_info_from_response():
    resp = {
        "is_available": True,
        "balance_infos": [
            {
                "currency": "CNY",
                "total_balance": "110.50",
                "granted_balance": "10.50",
                "topped_up_balance": "100.00"
            }
        ]
    }
    info = BalanceInfo.from_response(resp)
    assert info.is_available is True
    assert info.currency == "CNY"
    assert info.total_balance == 110.50
    assert info.granted_balance == 10.50
    assert info.topped_up_balance == 100.00


def test_balance_info_str_representation():
    info = BalanceInfo(True, "CNY", 88.00, 8.00, 80.00)
    s = str(info)
    assert "88.00" in s
    assert "CNY" in s


def test_fetch_balance_http_error(monkeypatch):
    import balance_api as ba

    def mock_get(*args, **kwargs):
        raise ba.requests.ConnectionError("network down")
    monkeypatch.setattr(ba.requests, "get", mock_get)

    with pytest.raises(BalanceError, match="network"):
        fetch_balance("sk-test")
