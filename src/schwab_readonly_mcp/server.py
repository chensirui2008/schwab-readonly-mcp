from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP

from .auth import SchwabAuthenticator
from .client import SchwabClient
from .config import Settings
from .indicators import calculate_indicators


def _epoch_milliseconds(iso_datetime: str) -> int:
    """Convert an ISO-8601 instant to the milliseconds required by Schwab."""
    parsed = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Date-time values must include a UTC offset, for example `2026-08-10T20:00:00Z`.")
    return int(parsed.astimezone(UTC).timestamp() * 1000)


def create_server(client: SchwabClient | None = None) -> FastMCP:
    mcp = FastMCP("schwab-readonly")
    api = client or SchwabClient(SchwabAuthenticator(Settings.from_environment()))

    @mcp.tool()
    def get_quotes(symbols: list[str], fields: str = "quote,fundamental") -> Any:
        """Get Schwab quotes for US equity symbols. Values may be delayed by exchange entitlement."""
        return api.get("/marketdata/v1/quotes", {"symbols": ",".join(symbols), "fields": fields})

    @mcp.tool()
    def get_price_history(
        symbol: str,
        period_type: str = "day",
        period: int = 10,
        frequency_type: str = "minute",
        frequency: int = 1,
        start_datetime: str | None = None,
        end_datetime: str | None = None,
        include_extended_hours: bool = True,
    ) -> Any:
        """Get every OHLCV candle Schwab allows for the requested period or ISO-8601 time range."""
        params: dict[str, Any] = {
            "symbol": symbol, "periodType": period_type, "period": period,
            "frequencyType": frequency_type, "frequency": frequency,
            "needExtendedHoursData": include_extended_hours,
        }
        if start_datetime is not None:
            params["startDate"] = _epoch_milliseconds(start_datetime)
        if end_datetime is not None:
            params["endDate"] = _epoch_milliseconds(end_datetime)
        return api.get("/marketdata/v1/pricehistory", params)

    @mcp.tool()
    def get_technical_indicators(
        symbol: str,
        period_type: str = "year",
        period: int = 1,
        frequency_type: str = "daily",
        frequency: int = 1,
    ) -> Any:
        """Calculate SMA20, EMA20, RSI14, MACD(12,26,9), Bollinger(20,2), ATR14 and session VWAP from Schwab candles."""
        history = api.get("/marketdata/v1/pricehistory", {
            "symbol": symbol, "periodType": period_type, "period": period,
            "frequencyType": frequency_type, "frequency": frequency,
            "needExtendedHoursData": True,
        })
        if not isinstance(history, dict):
            raise ValueError("Schwab price history response is not an object.")
        candles = history.get("candles")
        if not isinstance(candles, list):
            raise ValueError("Schwab price history response does not contain a candle list.")
        return {
            "symbol": symbol,
            "empty": history.get("empty"),
            "indicators": calculate_indicators(candles),
        }

    @mcp.tool()
    def get_fundamentals(symbol: str) -> Any:
        """Get Schwab's available issuer fundamentals for one symbol; it is not a replacement for full financial statements."""
        return api.get("/marketdata/v1/instruments", {"symbol": symbol, "projection": "fundamental"})

    @mcp.tool()
    def get_option_chain(symbol: str, contract_type: str = "ALL", strike_count: int = 10) -> Any:
        """Get a read-only option chain with Schwab-provided Greeks where available."""
        return api.get("/marketdata/v1/chains", {
            "symbol": symbol, "contractType": contract_type, "strikeCount": strike_count,
        })

    @mcp.tool()
    def get_market_hours(markets: list[str], date: str | None = None) -> Any:
        """Get market-session hours, optionally for an ISO date."""
        params: dict[str, Any] = {"markets": ",".join(markets)}
        if date is not None:
            params["date"] = date
        return api.get("/marketdata/v1/markets", params)

    @mcp.tool()
    def get_movers(index: str = "$SPX", sort: str = "PERCENT_CHANGE_UP", frequency: int = 0) -> Any:
        """Get top movers for $SPX, $COMPX, or $DJI."""
        return api.get(f"/marketdata/v1/movers/{index}", {"sort": sort, "frequency": frequency})

    @mcp.tool()
    def get_accounts(include_positions: bool = False) -> Any:
        """List linked Schwab accounts and, optionally, their positions. This tool never changes accounts."""
        params = {"fields": "positions"} if include_positions else None
        return api.get("/trader/v1/accounts", params)

    @mcp.tool()
    def get_account(account_hash: str, include_positions: bool = False) -> Any:
        """Read balances and optional positions for one account hash returned by get_accounts."""
        params = {"fields": "positions"} if include_positions else None
        return api.get(f"/trader/v1/accounts/{account_hash}", params)

    @mcp.tool()
    def get_transactions(
        account_hash: str, start_date: str, end_date: str, transaction_types: str = "TRADE"
    ) -> Any:
        """Read transaction history in an inclusive ISO-date range; this never submits an order."""
        return api.get(f"/trader/v1/accounts/{account_hash}/transactions", {
            "startDate": start_date, "endDate": end_date, "types": transaction_types,
        })

    return mcp
