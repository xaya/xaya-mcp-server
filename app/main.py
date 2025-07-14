#!/usr/bin/env python3

import argparse
import logging
from mcp.server.fastmcp import FastMCP


def main ():
  # Configure logging to match FastMCP style
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
    help="Port to bind the server to (default: 8000)",
  )
  args = parser.parse_args ()

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

  # MCP tools will be added here later

  logger.info ("Starting Streamable HTTP transport")
  mcp.run (transport="streamable-http")


if __name__ == "__main__":
  main ()
