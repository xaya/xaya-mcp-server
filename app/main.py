#!/usr/bin/env python3

import argparse
import logging
import os

from mcp.server.fastmcp import FastMCP
from eth_account import Account

from blockchain import Node, StatsSubgraph
from tools_contract import Tools as ContractTools
from tools_subgraph import Tools as SubgraphTools
from moves import Tools as MovesTools


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
  parser.add_argument (
    "--subgraph",
    required=True,
    help="The Graph endpoint URL for the subgraph",
  )
  parser.add_argument (
    "--gas_gwei_prio",
    type=int,
    default=0,
    help="Priority gas price in Gwei (0 means not set)",
  )
  parser.add_argument (
    "--gas_gwei_max",
    type=int,
    default=0,
    help="Maximum gas price in Gwei (0 means not set)",
  )
  args = parser.parse_args ()

  # Configure gas settings
  gas_config = None
  if args.gas_gwei_prio > 0 or args.gas_gwei_max > 0:
    gas_config = {}
    if args.gas_gwei_prio > 0:
      gas_config['prio'] = args.gas_gwei_prio
    if args.gas_gwei_max > 0:
      gas_config['max'] = args.gas_gwei_max

  # Configure operator account from environment variable
  operator_account = None
  privkey = os.environ.get('PRIVKEY')
  if privkey:
    try:
      operator_account = Account.from_key(privkey)
      logger.info(f"Operator address configured: {operator_account.address}")
    except Exception as e:
      logger.error("Failed to create account from PRIVKEY: %s", e)

  try:
    node = Node (args.rpc_url, args.delegation_contract)
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
    log_level="INFO",
  )

  # Create the tool providers
  contract_tools = ContractTools (node, gas_config, operator_account)
  subgraph_tools = SubgraphTools (subgraph, contract_tools)
  moves_tools = MovesTools (operator_account)

  # Add contract tools to the MCP server
  mcp.add_tool (contract_tools.nameToTokenId)
  mcp.add_tool (contract_tools.tokenIdToName)
  mcp.add_tool (contract_tools.getOwner)
  mcp.add_tool (contract_tools.getOwnerById)
  mcp.add_tool (contract_tools.getWchiBalance)
  mcp.add_tool (contract_tools.getWchiAllowance)
  mcp.add_tool (contract_tools.isApprovedForAll)
  mcp.add_tool (contract_tools.getApproved)
  mcp.add_tool (contract_tools.getDelegationPermissions)
  mcp.add_tool (contract_tools.getInfo)

  # Add subgraph tools to the MCP server
  mcp.add_tool (subgraph_tools.getNameRegistration)
  mcp.add_tool (subgraph_tools.getNamesOwnedBy)
  mcp.add_tool (subgraph_tools.getMovesForGame)
  mcp.add_tool (subgraph_tools.getMovesForName)

  # Add moves tools to the MCP server
  mcp.add_tool (moves_tools.hasMovePermission)

  logger.info ("Starting Streamable HTTP transport")
  mcp.run (transport="streamable-http")


if __name__ == "__main__":
  main ()