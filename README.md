# Xaya MCP Server

An MCP (Model Context Protocol) server with StreamableHTTP transport that provides tools for interacting with the Xaya blockchain ecosystem. The server connects to both an EVM blockchain node and the
[Xaya stats subgraph](https://github.com/xaya/stats-subgraph)
to provide comprehensive access to Xaya data.

## Overview

This server provides tools for accessing and querying:

• Xaya account name resolution (converting between human-readable names and token IDs)
• Account ownership information and NFT approvals  
• WCHI token balances and allowances
• Delegation permissions for fine-grained account access control
• Account registration history and metadata
• Move history for specific accounts and games
