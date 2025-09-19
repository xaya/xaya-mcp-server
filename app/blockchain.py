import json
import logging
import os.path
import httpx

from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware

class StatsSubgraph:
  """
  Helper class to query the stats subgraph.
  """

  def __init__ (self, url):
    self.url = url
    self.client = httpx.AsyncClient()

  async def query (self, query):
    """
    Runs a GraphQL query against the configured subgraph.
    If the query is successful, the `data` object from the response
    is returned.  Otherwise an exception is raised.
    """
    logging.debug ("Running GraphQL query:\\n%s", query)
    r = await self.client.post (self.url, json={"query": query})
    r.raise_for_status ()
    res = r.json ()
    if "errors" in res:
      raise RuntimeError (f"GraphQL query failed: {res['errors']}")
    return res["data"]

class Node:
  """
  Represents the connection to a blockchain node and the Xaya contracts.
  """

  def __init__ (self):
    """
    Initialises the instance.  This is private, use `create` to
    construct an instance properly.
    """
    pass

  @staticmethod
  async def create (rpcUrl, delegationContract):
    """
    Factory method to create a new instance and connect to the contracts.
    """

    res = Node ()

    logging.info ("Setting up Web3 connection to %s", rpcUrl)
    res.w3 = AsyncWeb3(AsyncHTTPProvider(rpcUrl))
    res.w3.middleware_onion.inject (ExtraDataToPOAMiddleware, layer=0)

    # Determine base path for loading ABIs.
    myPath = os.path.dirname (__file__)
    abiPath = os.path.join (myPath, "..", "abi")

    with open (os.path.join (abiPath, "WCHI.json"), "r") as f:
      wchiAbi = json.load (f)
    with open (os.path.join (abiPath, "IXayaAccounts.json"), "r") as f:
      accountsAbi = json.load (f)
    with open (os.path.join (abiPath, "XayaDelegation.json"), "r") as f:
      delegationAbi = json.load (f)


    res.delegation = res.w3.eth.contract (address=delegationContract,
                                              abi=delegationAbi["abi"])
    accountsAddr = await res.delegation.functions.accounts ().call ()
    res.accounts = res.w3.eth.contract (address=accountsAddr,
                                           abi=accountsAbi["abi"])
    wchiAddr = await res.accounts.functions.wchiToken ().call ()
    res.wchi = res.w3.eth.contract (address=wchiAddr, abi=wchiAbi["abi"])

    chainId = await res.w3.eth.chain_id
    logging.info ("Connected to chain ID: %d", chainId)
    logging.info ("WCHI contract at %s", res.wchi.address)
    logging.info ("Xaya Accounts contract at %s", res.accounts.address)
    logging.info ("Xaya Delegation contract at %s", res.delegation.address)

    return res
