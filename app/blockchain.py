import json
import logging
import os.path
import requests

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

class StatsSubgraph:
  """
  Helper class to query the stats subgraph.
  """

  def __init__ (self, url):
    self.url = url

  def query (self, query):
    """
    Runs a GraphQL query against the configured subgraph.
    If the query is successful, the `data` object from the response
    is returned.  Otherwise an exception is raised.
    """
    logging.info ("Running GraphQL query:\\n%s", query)
    r = requests.post (self.url, json={"query": query})
    r.raise_for_status ()
    res = r.json ()
    if "errors" in res:
      raise RuntimeError (f"GraphQL query failed: {res['errors']}")
    return res["data"]

class Node:
  """
  Represents the connection to a blockchain node and the Xaya contracts.
  """

  def __init__ (self, rpcUrl, delegationContract):
    """
    Initialises the instance and connects to the contracts.
    """

    logging.info ("Setting up Web3 connection to %s", rpcUrl)
    self.w3 = Web3 (Web3.HTTPProvider (rpcUrl))
    self.w3.middleware_onion.inject (ExtraDataToPOAMiddleware, layer=0)

    # Determine base path for loading ABIs.
    myPath = os.path.dirname (__file__)
    abiPath = os.path.join (myPath, "..", "abi")

    with open (os.path.join (abiPath, "WCHI.json"), "r") as f:
      wchiAbi = json.load (f)
    with open (os.path.join (abiPath, "IXayaAccounts.json"), "r") as f:
      accountsAbi = json.load (f)
    with open (os.path.join (abiPath, "XayaDelegation.json"), "r") as f:
      delegationAbi = json.load (f)

    self.delegation = self.w3.eth.contract (address=delegationContract,
                                              abi=delegationAbi["abi"])
    accountsAddr = self.delegation.functions.accounts ().call ()
    self.accounts = self.w3.eth.contract (address=accountsAddr,
                                           abi=accountsAbi["abi"])
    wchiAddr = self.accounts.functions.wchiToken ().call ()
    self.wchi = self.w3.eth.contract (address=wchiAddr, abi=wchiAbi["abi"])

    logging.info ("Connected to chain ID: %d", self.w3.eth.chain_id)
    logging.info ("WCHI contract at %s", self.wchi.address)
    logging.info ("Xaya Accounts contract at %s", self.accounts.address)
    logging.info ("Xaya Delegation contract at %s", self.delegation.address)

