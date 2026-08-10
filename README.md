# Schwab Read-Only MCP

本地 stdio MCP：从 Charles Schwab 官方 API 读取美股行情与账户数据。没有下单、撤单、修改账户或其他写入工具。

## 已提供工具

- `get_quotes`：美股报价及基本面字段
- `get_price_history`：分钟或日线 OHLCV
- `get_option_chain`、`get_market_hours`、`get_movers`
- `get_accounts`、`get_account`、`get_transactions`

报价是否属于实时数据取决于 Schwab 账户及交易所行情授权；MCP 不会把延时行情误标为实时。

## 前置条件

1. 在 [Schwab Developer Portal](https://developer.schwab.com/) 创建应用，并将回调地址完整填入该应用设置。
2. Python 3.11+ 与 `uv`。

```bash
cd /Users/chensirui/Develop/Equity_research/schwab_readonly_mcp
uv sync
export SCHWAB_CLIENT_ID='你的 App Key'
export SCHWAB_CLIENT_SECRET='你的 App Secret'
export SCHWAB_REDIRECT_URI='与你在 Schwab 登记的一致的回调地址'
uv run schwab-readonly-mcp auth
```

授权命令会打开浏览器；授权后粘贴完整的回调 URL。令牌默认保存为
`~/.config/schwab-readonly-mcp/token.json`，目录权限为 `0700`、文件权限为 `0600`。

## 连接 Codex

在本地 MCP 配置中添加：

```json
{
  "mcpServers": {
    "schwab-readonly": {
      "command": "uv",
      "args": ["--directory", "/Users/chensirui/Develop/Equity_research/schwab_readonly_mcp", "run", "schwab-readonly-mcp", "server"],
      "env": {
        "SCHWAB_CLIENT_ID": "…",
        "SCHWAB_CLIENT_SECRET": "…",
        "SCHWAB_REDIRECT_URI": "…"
      }
    }
  }
}
```

不要把 App Secret 或 token 写进项目、提交到 Git，或提供给对话。

## 本地验证

```bash
uv run python -c "from schwab_readonly_mcp.server import create_server; print(create_server)"
```
