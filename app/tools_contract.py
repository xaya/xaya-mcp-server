from web3.exceptions import ContractLogicError


class Tools:
  """
  Provides tools for interacting with the Xaya blockchain smart contracts.
  """

  def __init__ (self, node, gas_config=None, operator_account=None):
    self.node = node
    self.gas_config = gas_config
    self.operator_account = operator_account

  async def isApproved (self, owner, tokenId, address):
    """
    Helper method to check if an address is approved for a token (either for all or specific token).
    
    Args:
      owner: The owner of the token
      tokenId: The token ID to check
      address: The address to check approval for
    
    Returns:
      True if approved, False if not approved
    """
    # Check if the address is approved for all NFTs of the owner
    approved_for_all = await self.isApprovedForAll(owner, address)
    
    if approved_for_all:
      return True
    
    # Check if the address is approved for this specific token
    approved_address = await self.getApproved(tokenId)
    
    return approved_address == address

  def _normalize_token_id(self, token_id):
    """
    Normalizes a token ID to the proper format for web3.py ABI (uint256).
    Accepts either hex string (with 0x prefix), decimal string, or integer.
    Returns an integer suitable for uint256.
    """
    if isinstance(token_id, str):
      if token_id.startswith('0x'):
        return int(token_id, 16)
      else:
        return int(token_id)
    elif isinstance(token_id, int):
      return token_id
    else:
      raise ValueError(f"Token ID must be an integer or string, got {type(token_id)}")


  async def nameToTokenId (self, ns, name):
    """
    Converts a Xaya name (namespace and name) to its corresponding token ID.
    """
    return await self.node.accounts.functions.tokenIdForName (ns, name).call ()

  async def tokenIdToName (self, tokenId):
    """
    Converts a token ID to its corresponding Xaya name (namespace and name).
    tokenId can be an integer, decimal string, or hex string (with 0x prefix).
    """
    normalized_token_id = self._normalize_token_id(tokenId)
    ns, name = await self.node.accounts.functions.tokenIdToName (normalized_token_id).call ()
    return {"ns": ns, "name": name}

  async def getOwner (self, ns, name):
    """
    Gets the owner of a Xaya name.
    Returns the owner's address if the name is registered, otherwise an error.
    """
    try:
      tokenId = await self.node.accounts.functions.tokenIdForName (ns, name).call ()
      return await self.node.accounts.functions.ownerOf (tokenId).call ()
    except ContractLogicError as e:
      # This can happen if the name is not registered.
      raise RuntimeError (f"Name not found or error: {e}")

  async def getOwnerById (self, tokenId):
    """
    Gets the owner of a Xaya name by its token ID.
    Returns the owner's address if the token ID is valid, otherwise an error.
    tokenId can be an integer, decimal string, or hex string (with 0x prefix).
    """
    try:
      normalized_token_id = self._normalize_token_id(tokenId)
      return await self.node.accounts.functions.ownerOf (normalized_token_id).call ()
    except ContractLogicError as e:
      # This can happen if the token ID is invalid.
      raise RuntimeError (f"Token ID not found or error: {e}")

  async def getWchiBalance (self, owner):
    """
    Gets the WCHI balance of a given address.
    The balance is returned as a formatted string with the correct number of decimals.
    """
    balance = await self.node.wchi.functions.balanceOf (owner).call ()
    decimals = await self.node.wchi.functions.decimals ().call ()
    return f"{balance / 10**decimals} WCHI"

  async def getWchiAllowance (self, owner, spender):
    """
    Gets the WCHI allowance for a spender from an owner.
    The allowance is returned as a formatted string with the correct number of decimals.
    """
    allowance = await self.node.wchi.functions.allowance (owner, spender).call ()
    decimals = await self.node.wchi.functions.decimals ().call ()
    return f"{allowance / 10**decimals} WCHI"

  async def isApprovedForAll (self, owner, operator):
    """
    Checks if an operator is approved for all of an owner's Xaya account NFTs.
    """
    return await self.node.accounts.functions.isApprovedForAll (owner, operator).call ()

  async def getApproved (self, tokenId):
    """
    Gets the approved address for a single Xaya account NFT.
    tokenId can be an integer, decimal string, or hex string (with 0x prefix).
    """
    try:
      normalized_token_id = self._normalize_token_id(tokenId)
      return await self.node.accounts.functions.getApproved (normalized_token_id).call ()
    except ContractLogicError as e:
      raise RuntimeError (f"Token ID not found or error: {e}")

  async def getInfo (self):
    """
    Returns the chain ID, Xaya contract addresses, operator address, and gas configuration used by the server.
    """
    return {
      "chainId": await self.node.w3.eth.chain_id,
      "wchiAddress": self.node.wchi.address,
      "accountsAddress": self.node.accounts.address,
      "delegationAddress": self.node.delegation.address,
      "operatorAddress": self.operator_account.address if self.operator_account else None,
      "gasGwei": self.gas_config if self.gas_config else None,
    }

  async def getDelegationPermissions (self, ns, name, subject=None):
    """
    Lists the delegation permissions for a given Xaya name.
    If a subject is provided, only permissions for that subject are returned.
    """
    tokenId = await self.nameToTokenId (ns, name)
    owner = await self.getOwnerById (tokenId)

    delegationAddr = self.node.delegation.address
    approved = await self.isApproved (owner, tokenId, delegationAddr)

    permissions = await self._getPermissions (tokenId, owner, [], subject)

    return {
      "owner": owner,
      "tokenId": str(tokenId),
      "approved": approved,
      "permissions": permissions,
    }

  async def _getPermissions (self, tokenId, owner, p, subject):
    children_nodes, full_access_keys, fallback_access_keys = await self.node.delegation.functions.getDefinedKeys (tokenId, owner, p).call ()

    children = []
    for k in children_nodes:
        child_permissions = await self._getPermissions(tokenId, owner, p + [k], subject)
        child_node = {"name": k}
        child_node.update(child_permissions)
        children.append(child_node)

    full_access = []
    for addr in full_access_keys:
        if subject is None or addr == subject:
            expiration = await self.node.delegation.functions.getExpiration (tokenId, owner, p, addr, False).call ()
            full_access.append ({
                "address": addr,
                "expiration": str (expiration)
            })

    fallback_access = []
    for addr in fallback_access_keys:
        if subject is None or addr == subject:
            expiration = await self.node.delegation.functions.getExpiration (tokenId, owner, p, addr, True).call ()
            fallback_access.append ({
                "address": addr,
                "expiration": str (expiration)
            })

    return {
        "children": children,
        "fullAccess": full_access,
        "fallbackAccess": fallback_access
    }
