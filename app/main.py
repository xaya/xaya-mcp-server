#!/usr/bin/env python3

import argparse
import logging

from mcp.server.fastmcp import FastMCP

from blockchain import Node
from tools import XayaTools


def main ():
  # Configure logging
  logging.basicConfig (
    level=logging.INFO,
    format="%(levelname)s:     %(message)s",
  )
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
  args = parser.parse_args ()

  try:
    node = Node (args.rpc_url, args.delegation_contract)
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
    log_level="INFO",
  )


  # Create the tool provider and add all its methods to the MCP server.
  tool_provider = XayaTools (node)
  mcp.add_tool (tool_provider.nameToTokenId)
  mcp.add_tool (tool_provider.tokenIdToName)
  mcp.add_tool (tool_provider.getOwner)
  mcp.add_tool (tool_provider.getOwnerById)
  mcp.add_tool (tool_provider.getWchiBalance)
  mcp.add_tool (tool_provider.getWchiAllowance)
  mcp.add_tool (tool_provider.isApprovedForAll)
  mcp.add_tool (tool_provider.getApproved)
  mcp.add_tool (tool_provider.getChainInfo)


  logger.info ("Starting Streamable HTTP transport")
  mcp.run (transport="streamable-http")


if __name__ == "__main__":
  main ()

