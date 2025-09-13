import json
from web3 import Web3


class Tools:
  """
  Provides tools for Xaya move operations and permission checking.
  """

  def __init__ (self, operator_account=None):
    self.operator_account = operator_account

  def hasMovePermission (self, ns, name, move, sending_address=None):
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
      return "Error: ns (namespace) is required and must be a string"
    
    if not name or not isinstance(name, str):
      return "Error: name is required and must be a string"
    
    if move is None:
      return "Error: move is required"
    
    # Determine the sending address
    address_to_check = sending_address
    if not address_to_check:
      if not self.operator_account:
        return "Error: No sending address provided and no operator account configured"
      address_to_check = self.operator_account.address
    
    # Validate and normalize address format
    if not isinstance(address_to_check, str):
      return "Error: Address must be a string"
    
    # If address is all lowercase, convert to checksum format first
    if address_to_check.islower():
      try:
        address_to_check = Web3.to_checksum_address(address_to_check)
      except ValueError:
        return "Error: Invalid Ethereum address format"
    
    # Validate that the address is properly checksummed
    if not Web3.is_checksum_address(address_to_check):
      return "Error: Address must be a valid checksummed Ethereum address"
    
    # Mock implementation - for now always return True
    # TODO: Implement actual permission checking logic
    return {
      "hasPermission": True,
      "namespace": ns,
      "name": name,
      "checkedAddress": address_to_check,
      "note": "Mock implementation - always returns True"
    }