import json
import time

from eth_account import Account
from web3 import Web3
from web3.exceptions import TransactionNotFound


class Tools:
  """
  Provides tools for Xaya move operations and permission checking.
  """

  def __init__ (self, operator_account=None, contract_tools=None):
    self.operator_account = operator_account
    self.contract_tools = contract_tools

  def splitMovePath (self, move):
    """
    Extracts a path from nested single-key objects in a move value.
    
    Args:
      move: The move value to process
    
    Returns:
      Tuple of (path, value) where path is a list of keys and value is the final value
    """
    path = []
    current_value = move
    
    while (isinstance(current_value, dict) and len(current_value) == 1):
      [key] = current_value.keys()
      [nextValue] = current_value.values()
      # To send a hierarchical move, we need the actual move value
      # (without path) to be a JSON object, too.
      if not isinstance(nextValue, dict):
        break
      path.append(key)
      current_value = nextValue
    
    return path, current_value

  async def hasMovePermission (self, ns, name, move, sending_address=None):
    """
    Checks if a given address has permission to send a move for a specific Xaya name.
    
    Args:
      ns: Namespace string (required)
      name: Name string (required) 
      move: Move data as JSON (required)
      sending_address: Address to check permission for (optional, defaults to operator address)
    
    Returns:
      Boolean indicating if the address has permission to send the move
    """
    # Validate required arguments
    if not ns or not isinstance(ns, str):
      raise ValueError("ns (namespace) is required and must be a string")
    
    if not name or not isinstance(name, str):
      raise ValueError("name is required and must be a string")
    
    if move is None:
      raise ValueError("move is required")
    
    # Determine the sending address
    address_to_check = sending_address
    if not address_to_check:
      if not self.operator_account:
        raise ValueError("No sending address provided and no operator account configured")
      address_to_check = self.operator_account.address
    
    # Validate and normalize address format
    if not isinstance(address_to_check, str):
      raise ValueError("Address must be a string")
    
    # If address is all lowercase, convert to checksum format first
    if address_to_check.islower():
      try:
        address_to_check = Web3.to_checksum_address(address_to_check)
      except ValueError:
        raise ValueError("Invalid Ethereum address format")
    
    # Validate that the address is properly checksummed
    if not Web3.is_checksum_address(address_to_check):
      raise ValueError("Address must be a valid checksummed Ethereum address")
    
    # Convert name to token ID
    tokenId = await self.contract_tools.nameToTokenId(ns, name)
    
    # Get the owner of the name
    owner = await self.contract_tools.getOwnerById(tokenId)
    
    has_permission = False
    
    # Check if the address is the owner
    if address_to_check == owner:
      has_permission = True
    else:
      # Check if the address is approved for the token
      approved = await self.contract_tools.isApproved(owner, tokenId, address_to_check)
      has_permission = approved
    
    if has_permission:
      serialized_move = json.dumps(move, separators=(',', ':'))
      return {
        "hasPermission": True,
        "delegation": False,
        "move": serialized_move,
        "address": address_to_check
      }
    
    # Check delegation permissions
    delegation_addr = self.contract_tools.node.delegation.address
    delegation_approved = await self.contract_tools.isApproved(owner, tokenId, delegation_addr)
    
    if not delegation_approved:
      return {
        "hasPermission": False,
        "address": address_to_check,
        "reason": "Delegation contract is not approved for this name"
      }
    
    # Split the move path and check delegation permissions
    path, remaining_value = self.splitMovePath(move)
    
    # Check hasAccess on delegation contract (current time + 60 seconds)
    at_time = int(time.time()) + 60
    try:
      has_access = await self.contract_tools.node.delegation.functions.hasAccess(
        ns, name, path, address_to_check, at_time
      ).call()
    except Exception as e:
      raise RuntimeError(f"Error calling hasAccess: {e}")
    
    # Serialize the remaining value after path extraction
    serialized_remaining = json.dumps(remaining_value, separators=(',', ':'))
    
    return {
      "hasPermission": has_access,
      "delegation": True,
      "move": serialized_remaining,
      "address": address_to_check,
      "path": path
    }

  async def sendMove (self, ns, name, move, privkey=None, gas_gwei=None):
    """
    Sends a move for a Xaya name.

    Args:
      ns: Namespace string (required)
      name: Name string (required)
      move: Move data as JSON (required)
      privkey: Private key to use for sending (optional, defaults to operator key)
      gas_gwei: Gas settings to use (optional, defaults to configured gas)

    Returns:
      The transaction hash of the sent move.
    """

    # Validate required arguments
    if not ns or not isinstance(ns, str):
      raise ValueError("ns (namespace) is required and must be a string")
    if not name or not isinstance(name, str):
      raise ValueError("name is required and must be a string")
    if move is None:
      raise ValueError("move is required")

    # Determine the sender account to use.
    acc = None
    if privkey is not None:
      try:
        acc = Account.from_key(privkey)
      except Exception as e:
        raise ValueError(f"Invalid private key: {e}")
    else:
      acc = self.operator_account
    if acc is None:
      raise ValueError("No private key specified and no operator account configured")

    # Determine the gas settings to use.
    gas = {}
    if self.contract_tools.gas_config is not None:
      gas = self.contract_tools.gas_config.copy()
    if gas_gwei is not None:
      gas.update(gas_gwei)
    if "max" not in gas or "prio" not in gas:
      raise ValueError("Gas settings must contain 'max' and 'prio' keys")

    # Check for permissions and get the move data.
    permission = await self.hasMovePermission(ns, name, move, acc.address)
    if not permission["hasPermission"]:
      raise RuntimeError("Account does not have permission to send this move")

    node = self.contract_tools.node
    w3 = node.w3

    # Construct the contract call based on delegation type
    if permission["delegation"]:
      tx = node.delegation.functions.sendHierarchicalMove(ns, name,
                                                          permission["path"],
                                                          permission["move"])
    else:
      tx = node.accounts.functions.move(ns, name, permission["move"],
                                        2**256 - 1, 0, "0x" + "0" * 40)

    # Common transaction handling
    tx_dict = {
        "from": acc.address,
        "nonce": await w3.eth.get_transaction_count(acc.address),
        "maxFeePerGas": w3.to_wei(gas["max"], "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(gas["prio"], "gwei"),
    }
    gas_estimate_transaction = tx.build_transaction(tx_dict)
    tx_dict["gas"] = await w3.eth.estimate_gas(gas_estimate_transaction)
    signed_tx = w3.eth.account.sign_transaction(tx.build_transaction(tx_dict),
                                                acc.key)
    tx_hash = await w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return {"txid": "0x" + tx_hash.hex()}

  async def getTransactionStatus (self, txids, wait=True):
    """
    Gets the status of one or more transactions and optionally waits
    for them to be mined.

    Args:
      txids: Single transaction ID as hex string or list of transaction IDs
      wait: Whether to wait for transactions to be mined (default True)

    Returns:
      Dictionary with txid as keys and status as values
    """
    # Handle single txid vs list of txids
    if isinstance(txids, str):
      txid_list = [txids]
    else:
      txid_list = txids

    # Validate txid format
    for txid in txid_list:
      if not isinstance(txid, str):
        raise ValueError("Transaction IDs must be hex strings")
      if not txid.startswith('0x'):
        raise ValueError("Transaction IDs must start with 0x")

    w3 = self.contract_tools.node.w3
    result = {}

    for txid in txid_list:
      try:
        if wait:
          # Wait for transaction receipt with default timeout
          receipt = await w3.eth.wait_for_transaction_receipt(txid)
        else:
          # Just get the receipt if available
          receipt = await w3.eth.get_transaction_receipt(txid)

        # Check if transaction succeeded or reverted
        if receipt and receipt.status == 1:
          result[txid] = "success"
        elif receipt:
          result[txid] = "reverted"
        else:
          result[txid] = "notfound"

      except TransactionNotFound:
        result[txid] = "notfound"

    return result
