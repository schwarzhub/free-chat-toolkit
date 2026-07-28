# mcps/

An **MCP integration** connects free-chat to a [Model Context Protocol](https://modelcontextprotocol.io)
server — a standard way to expose an external system's capabilities as callable tools. (See
[what MCP is](../README.md#mcp-model-context-protocol).)

*None yet.* Propose one as an issue or a PR — which server/API, what tools it exposes, and why it's
worth wiring in.

**Hard norm — no paid dependencies.** An MCP (or API) that requires **direct payment** (a paid key,
metered/per-call billing, a paid MCP host) will almost certainly **not** be accepted: it would bill
the operator per use and break the free, ad-funded model. **Free APIs are welcome** — and a clean MCP
that wraps a *free* API to make it easier to use is a great contribution.
