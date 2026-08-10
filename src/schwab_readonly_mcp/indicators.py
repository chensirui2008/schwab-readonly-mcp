from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any


class IndicatorError(ValueError):
    """Raised when Schwab candle data cannot support an indicator calculation."""


def _require_period(name: str, period: int) -> None:
    if period < 1:
        raise IndicatorError(f"{name} period must be at least 1.")


def _sma(values: Sequence[float], period: int) -> list[float | None]:
    _require_period("SMA", period)
    result: list[float | None] = [None] * len(values)
    running_total = 0.0
    for index, value in enumerate(values):
        running_total += value
        if index >= period:
            running_total -= values[index - period]
        if index >= period - 1:
            result[index] = running_total / period
    return result


def _ema(values: Sequence[float], period: int) -> list[float | None]:
    _require_period("EMA", period)
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    multiplier = 2 / (period + 1)
    previous = sum(values[:period]) / period
    result[period - 1] = previous
    for index in range(period, len(values)):
        previous = (values[index] - previous) * multiplier + previous
        result[index] = previous
    return result


def _rsi(closes: Sequence[float], period: int) -> list[float | None]:
    _require_period("RSI", period)
    result: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return result
    gains = [max(closes[index] - closes[index - 1], 0.0) for index in range(1, len(closes))]
    losses = [max(closes[index - 1] - closes[index], 0.0) for index in range(1, len(closes))]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    def value() -> float:
        if average_loss == 0:
            return 100.0
        return 100 - (100 / (1 + average_gain / average_loss))

    result[period] = value()
    for index in range(period + 1, len(closes)):
        average_gain = (average_gain * (period - 1) + gains[index - 1]) / period
        average_loss = (average_loss * (period - 1) + losses[index - 1]) / period
        result[index] = value()
    return result


def _atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int) -> list[float | None]:
    _require_period("ATR", period)
    result: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return result
    true_ranges = [
        max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1]))
        for index in range(1, len(closes))
    ]
    previous = sum(true_ranges[:period]) / period
    result[period] = previous
    for index in range(period + 1, len(closes)):
        previous = (previous * (period - 1) + true_ranges[index - 1]) / period
        result[index] = previous
    return result


def _iso_timestamp(candle: dict[str, Any]) -> str:
    timestamp = candle.get("datetime")
    if not isinstance(timestamp, (int, float)):
        raise IndicatorError("Every candle must contain a numeric `datetime` in milliseconds.")
    return datetime.fromtimestamp(timestamp / 1000, tz=UTC).isoformat().replace("+00:00", "Z")


def calculate_indicators(
    candles: Sequence[dict[str, Any]],
    sma_period: int = 20,
    ema_period: int = 20,
    rsi_period: int = 14,
    macd_fast_period: int = 12,
    macd_slow_period: int = 26,
    macd_signal_period: int = 9,
    bollinger_period: int = 20,
    bollinger_stddev: float = 2.0,
    atr_period: int = 14,
) -> list[dict[str, Any]]:
    """Calculate standard indicators from chronologically ordered Schwab OHLCV candles."""
    if not candles:
        raise IndicatorError("Schwab returned no candles for the requested range.")
    if macd_fast_period >= macd_slow_period:
        raise IndicatorError("MACD fast period must be less than the slow period.")
    if bollinger_stddev <= 0:
        raise IndicatorError("Bollinger standard-deviation multiplier must be positive.")

    fields = ("open", "high", "low", "close", "volume")
    normalized: list[dict[str, float | str]] = []
    for candle in candles:
        values: dict[str, float | str] = {"datetime": _iso_timestamp(candle)}
        for field in fields:
            value = candle.get(field)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise IndicatorError(f"Every candle must contain a finite numeric `{field}`.")
            values[field] = float(value)
        normalized.append(values)

    closes = [float(candle["close"]) for candle in normalized]
    highs = [float(candle["high"]) for candle in normalized]
    lows = [float(candle["low"]) for candle in normalized]
    volumes = [float(candle["volume"]) for candle in normalized]
    sma = _sma(closes, sma_period)
    ema = _ema(closes, ema_period)
    rsi = _rsi(closes, rsi_period)
    atr = _atr(highs, lows, closes, atr_period)
    fast_ema = _ema(closes, macd_fast_period)
    slow_ema = _ema(closes, macd_slow_period)
    macd = [
        fast - slow if fast is not None and slow is not None else None
        for fast, slow in zip(fast_ema, slow_ema, strict=True)
    ]
    macd_values = [value for value in macd if value is not None]
    signal_values = _ema(macd_values, macd_signal_period)
    signal: list[float | None] = [None] * len(closes)
    signal_start = next((index for index, value in enumerate(macd) if value is not None), len(closes))
    for index, value in enumerate(signal_values):
        if signal_start + index < len(signal):
            signal[signal_start + index] = value

    upper_band: list[float | None] = [None] * len(closes)
    lower_band: list[float | None] = [None] * len(closes)
    for index in range(bollinger_period - 1, len(closes)):
        window = closes[index - bollinger_period + 1 : index + 1]
        mean = sum(window) / bollinger_period
        deviation = math.sqrt(sum((value - mean) ** 2 for value in window) / bollinger_period)
        upper_band[index] = mean + bollinger_stddev * deviation
        lower_band[index] = mean - bollinger_stddev * deviation

    session_vwap: list[float | None] = []
    session = ""
    cumulative_price_volume = 0.0
    cumulative_volume = 0.0
    for candle, high, low, close, volume in zip(normalized, highs, lows, closes, volumes, strict=True):
        candle_session = str(candle["datetime"])[:10]
        if candle_session != session:
            session = candle_session
            cumulative_price_volume = 0.0
            cumulative_volume = 0.0
        cumulative_price_volume += ((high + low + close) / 3) * volume
        cumulative_volume += volume
        session_vwap.append(cumulative_price_volume / cumulative_volume if cumulative_volume else None)

    return [
        {
            **candle,
            "sma": sma[index],
            "ema": ema[index],
            "rsi": rsi[index],
            "macd": macd[index],
            "macd_signal": signal[index],
            "macd_histogram": macd[index] - signal[index]
            if macd[index] is not None and signal[index] is not None
            else None,
            "bollinger_upper": upper_band[index],
            "bollinger_lower": lower_band[index],
            "atr": atr[index],
            "session_vwap": session_vwap[index],
        }
        for index, candle in enumerate(normalized)
    ]
