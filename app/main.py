#!/usr/bin/env python3

import argparse
import anyio
import functools
import logging

from mcp.server.fastmcp import FastMCP

from blockchain import Node, StatsSubgraph
from tools_contract import Tools as ContractTools
from tools_subgraph import Tools as SubgraphTools


def _add_tool_with_error_handling(mcp, tool_func):
  """
  Helper method to add a tool to the MCP server with exception handling.
  Wraps the tool function to catch any exceptions and return them as "Error: ..." strings.
  """
  @functools.wraps(tool_func)
  async def wrapper(*args, **kwargs):
    try:
      return await tool_func(*args, **kwargs)
    except Exception as e:
      return f"Error: {e}"
  
  mcp.add_tool(wrapper)

async def main ():
  logger = logging.getLogger ("xaya-mcp")

  # Parse command-line arguments
  parser = argparse.ArgumentParser (description="Xaya MCP Server")
  parser.add_argument (
    "--port",
    type=int,
    default=8000,
    help="Port to bind the server to",
  )
  parser.add_argument (
    "--rpc_url",
    required=True,
    help="EVM node JSON-RPC endpoint",
  )
  parser.add_argument (
    "--delegation_contract",
    required=True,
    help="Address of the XayaDelegation contract",
  )
  parser.add_argument (
    "--subgraph",
    required=True,
    help="The Graph endpoint URL for the subgraph",
  )
  parser.add_argument (
    "--log_level",
    default="INFO",
    help="Set the log level (e.g., DEBUG, INFO, WARNING)",
  )
  args = parser.parse_args ()

  # Update logging level from arguments
  logging.basicConfig (
    level=args.log_level.upper(),
    format="%(levelname)s:     %(message)s",
  )
  logger = logging.getLogger ("xaya-mcp")

  try:
    node = await Node.create (args.rpc_url, args.delegation_contract)
    subgraph = StatsSubgraph (args.subgraph)
  except Exception as e:
    logger.error ("Failed to initialize blockchain node: %s", e)
    return

  logger.info (f"Initializing Xaya MCP server on 0.0.0.0:{args.port}")
  logger.info (f"Streamable HTTP endpoint will be available at http://0.0.0.0:{args.port}/mcp/")

  # Create the MCP server
  mcp = FastMCP (
    "Xaya MCP",
    port=args.port,
    host="0.0.0.0",
    debug=False,
    log_level=args.log_level.upper(),
  )

  # Create the tool providers
  contract_tools = ContractTools (node)
  subgraph_tools = SubgraphTools (subgraph, contract_tools)

  # Add contract tools to the MCP server
  _add_tool_with_error_handling (mcp, contract_tools.nameToTokenId)
  _add_tool_with_error_handling (mcp, contract_tools.tokenIdToName)
  _add_tool_with_error_handling (mcp, contract_tools.getOwner)
  _add_tool_with_error_handling (mcp, contract_tools.getOwnerById)
  _add_tool_with_error_handling (mcp, contract_tools.getWchiBalance)
  _add_tool_with_error_handling (mcp, contract_tools.getWchiAllowance)
  _add_tool_with_error_handling (mcp, contract_tools.isApprovedForAll)
  _add_tool_with_error_handling (mcp, contract_tools.getApproved)
  _add_tool_with_error_handling (mcp, contract_tools.getDelegationPermissions)
  _add_tool_with_error_handling (mcp, contract_tools.getChainInfo)

  # Add subgraph tools to the MCP server
  _add_tool_with_error_handling (mcp, subgraph_tools.getNameRegistration)
  _add_tool_with_error_handling (mcp, subgraph_tools.getNamesOwnedBy)
  _add_tool_with_error_handling (mcp, subgraph_tools.getMovesForGame)
  _add_tool_with_error_handling (mcp, subgraph_tools.getMovesForName)

  logger.info ("Starting Streamable HTTP transport")
  await mcp.run_streamable_http_async ()


if __name__ == "__main__":
  try:
    anyio.run (main)
  except KeyboardInterrupt:
    pass
