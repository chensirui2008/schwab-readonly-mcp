from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .auth import SchwabAuthenticator
from .client import SchwabClient
from .config import Settings


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
    ) -> Any:
        """Get historical OHLCV bars. Schwab validates allowed period/frequency combinations."""
        return api.get("/marketdata/v1/pricehistory", {
            "symbol": symbol, "periodType": period_type, "period": period,
            "frequencyType": frequency_type, "frequency": frequency,
        })

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
