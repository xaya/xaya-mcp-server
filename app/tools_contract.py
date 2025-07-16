from web3.exceptions import ContractLogicError


class Tools:
  """
  Provides tools for interacting with the Xaya blockchain smart contracts.
  """

  def __init__ (self, node):
    self.node = node

  def nameToTokenId (self, ns, name):
    """
    Converts a Xaya name (namespace and name) to its corresponding token ID.
    """
    try:
      return self.node.accounts.functions.tokenIdForName (ns, name).call ()
    except ContractLogicError as e:
      return f"Error: {e}"

  def tokenIdToName (self, tokenId):
    """
    Converts a token ID to its corresponding Xaya name (namespace and name).
    """
    try:
      ns, name = self.node.accounts.functions.tokenIdToName (tokenId).call ()
      return {"ns": ns, "name": name}
    except ContractLogicError as e:
      return f"Error: {e}"

  def getOwner (self, ns, name):
    """
    Gets the owner of a Xaya name.
    Returns the owner's address if the name is registered, otherwise an error.
    """
    try:
      tokenId = self.node.accounts.functions.tokenIdForName (ns, name).call ()
      return self.node.accounts.functions.ownerOf (tokenId).call ()
    except ContractLogicError as e:
      # This can happen if the name is not registered.
      return f"Error: Name not found or error: {e}"

  def getOwnerById (self, tokenId):
    """
    Gets the owner of a Xaya name by its token ID.
    Returns the owner's address if the token ID is valid, otherwise an error.
    """
    try:
      return self.node.accounts.functions.ownerOf (tokenId).call ()
    except ContractLogicError as e:
      # This can happen if the token ID is invalid.
      return f"Error: Token ID not found or error: {e}"

  def getWchiBalance (self, owner):
    """
    Gets the WCHI balance of a given address.
    The balance is returned as a formatted string with the correct number of decimals.
    """
    try:
      balance = self.node.wchi.functions.balanceOf (owner).call ()
      decimals = self.node.wchi.functions.decimals ().call ()
      return f"{balance / 10**decimals} WCHI"
    except Exception as e:
      return f"Error: {e}"

  def getWchiAllowance (self, owner, spender):
    """
    Gets the WCHI allowance for a spender from an owner.
    The allowance is returned as a formatted string with the correct number of decimals.
    """
    try:
      allowance = self.node.wchi.functions.allowance (owner, spender).call ()
      decimals = self.node.wchi.functions.decimals ().call ()
      return f"{allowance / 10**decimals} WCHI"
    except Exception as e:
      return f"Error: {e}"

  def isApprovedForAll (self, owner, operator):
    """
    Checks if an operator is approved for all of an owner's Xaya account NFTs.
    """
    try:
      return self.node.accounts.functions.isApprovedForAll (owner, operator).call ()
    except Exception as e:
      return f"Error: {e}"

  def getApproved (self, tokenId):
    """
    Gets the approved address for a single Xaya account NFT.
    """
    try:
      return self.node.accounts.functions.getApproved (tokenId).call ()
    except ContractLogicError as e:
      return f"Error: Token ID not found or error: {e}"

  def getChainInfo (self):
    """
    Returns the chain ID and Xaya contract addresses used by the server.
    """
    return {
      "chainId": self.node.w3.eth.chain_id,
      "wchiAddress": self.node.wchi.address,
      "accountsAddress": self.node.accounts.address,
      "delegationAddress": self.node.delegation.address,
    }

  def getDelegationPermissions (self, ns, name, subject=None):
    """
    Lists the delegation permissions for a given Xaya name.
    If a subject is provided, only permissions for that subject are returned.
    """
    try:
      tokenId = self.nameToTokenId (ns, name)
      if isinstance (tokenId, str) and tokenId.startswith ("Error:"):
        return tokenId

      owner = self.getOwnerById (tokenId)
      if isinstance (owner, str) and owner.startswith ("Error:"):
            return owner

      delegationAddr = self.node.delegation.address
      approved = self.isApprovedForAll (owner, delegationAddr)
      if not approved:
            approved = self.getApproved (tokenId) == delegationAddr

      permissions = self._getPermissions (tokenId, owner, [], subject)

      return {
        "owner": owner,
        "tokenId": str(tokenId),
        "approved": approved,
        "permissions": permissions,
      }
    except Exception as e:
      return f"Error: {e}"

  def _getPermissions (self, tokenId, owner, p, subject):
    children_nodes, full_access_keys, fallback_access_keys = self.node.delegation.functions.getDefinedKeys (tokenId, owner, p).call ()

    children = []
    for k in children_nodes:
        child_permissions = self._getPermissions(tokenId, owner, p + [k], subject)
        child_node = {"name": k}
        child_node.update(child_permissions)
        children.append(child_node)

    full_access = []
    for addr in full_access_keys:
        if subject is None or addr == subject:
            expiration = self.node.delegation.functions.getExpiration (tokenId, owner, p, addr, False).call ()
            full_access.append ({
                "address": addr,
                "expiration": str (expiration)
            })

    fallback_access = []
    for addr in fallback_access_keys:
        if subject is None or addr == subject:
            expiration = self.node.delegation.functions.getExpiration (tokenId, owner, p, addr, True).call ()
            fallback_access.append ({
                "address": addr,
                "expiration": str (expiration)
            })

    return {
        "children": children,
        "fullAccess": full_access,
        "fallbackAccess": fallback_access
    }
