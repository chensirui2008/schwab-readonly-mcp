from schwab_readonly_mcp.indicators import calculate_indicators


def _candles(count: int) -> list[dict[str, int | float]]:
    return [
        {
            "datetime": 1_704_067_200_000 + index * 86_400_000,
            "open": 100 + index,
            "high": 101 + index,
            "low": 99 + index,
            "close": 100 + index,
            "volume": 1_000 + index,
        }
        for index in range(count)
    ]


def test_calculate_indicators_returns_expected_warmup_and_values() -> None:
    result = calculate_indicators(_candles(40))

    assert result[18]["sma"] is None
    assert result[19]["sma"] == 109.5
    assert result[14]["rsi"] == 100.0
    assert result[25]["macd"] is not None
    assert result[33]["macd_signal"] is not None
    assert result[14]["atr"] == 2.0
    assert result[0]["session_vwap"] == 100.0
