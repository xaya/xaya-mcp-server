BATCH_SIZE = 10


class Tools:
  """
  Provides tools for querying the Xaya stats subgraph.
  """

  def __init__ (self, subgraph, contract_tools):
    self.subgraph = subgraph
    self.contract_tools = contract_tools

  def _to_hex_id (self, n):
    """
    Converts an integer to a 32-byte hex string suitable for
    subgraph Name ID queries, matching AssemblyScript ByteArray.fromBigInt behavior.

    This uses little-endian encoding with variable length and sign extension
    when needed.
    """
    if n == 0:
        return '0x00'

    # Calculate minimum bytes needed for the number
    bit_length = n.bit_length()
    byte_length = (bit_length + 7) // 8

    # Check if we need a sign byte (when MSB would be 1)
    # This happens when the number exactly fills the byte boundary
    # or when the highest bit of the highest byte is set
    temp_bytes = n.to_bytes(byte_length, byteorder='little', signed=False)
    if temp_bytes[-1] & 0x80:  # If the MSB of the last byte is 1
        byte_length += 1  # Add sign byte

    # Convert to bytes using little-endian
    token_bytes = n.to_bytes(byte_length, byteorder='little', signed=False)

    return '0x' + token_bytes.hex()

  def getNameRegistration (self, ns, name):
    """
    Returns the registration info for a given name.
    """
    tokenId = self.contract_tools.nameToTokenId (ns, name)
    if isinstance (tokenId, str) and tokenId.startswith ("Error:"):
      return tokenId
    tokenIdHex = self._to_hex_id (tokenId)

    query = """
      query {{
        registrations (where: {{name: "{tokenId}"}})
        {{
          id
          tx {{
            id
            height
            timestamp
          }}
        }}
      }}
    """.format (tokenId=tokenIdHex)
    data = self.subgraph.query (query)
    registrations = data["registrations"]
    if len(registrations) == 0:
      return "Error: Name not found"

    registration = registrations[0]

    return {
      "txid": registration["tx"]["id"],
      "height": registration["tx"]["height"],
      "timestamp": registration["tx"]["timestamp"]
    }

  def getNamesOwnedBy (self, owner, offset=0):
    """
    Returns a batch of names owned by a given address.
    """
    query = """
      query {{
        names (
          where: {{owner: "{owner}"}},
          orderBy: id,
          orderDirection: asc,
          first: {limit},
          skip: {offset}
        ) {{
          ns {{
            ns
          }}
          name
        }}
      }}
    """.format (owner=owner, limit=BATCH_SIZE + 1, offset=offset)
    data = self.subgraph.query (query)
    names = data["names"]

    more = False
    if len (names) > BATCH_SIZE:
      more = True
      names = names[:-1]

    return {
      "names": [{"ns": n["ns"]["ns"], "name": n["name"]} for n in names],
      "more": more,
    }

  def getMovesForGame (self, game, fromTimestamp=None, toTimestamp=None, offset=0):
    """
    Returns a batch of moves for a given game, ordered newest first, optionally
    filtered within a range of timestamps.  Using null for either timestamp
    disables filtering by this timestamp.
    """
    # Build all conditions separately
    conditions = []
    conditions.append (f'{{game_: {{game: "{game}"}}}}')

    if fromTimestamp is not None:
      conditions.append (f'{{tx_: {{timestamp_gte: {fromTimestamp}}}}}')
    if toTimestamp is not None:
      conditions.append (f'{{tx_: {{timestamp_lte: {toTimestamp}}}}}')

    where = ", ".join (conditions)

    query = """
      query {{
        gameMoves (
          where: {{and: [{where}]}},
          orderBy: tx__timestamp,
          orderDirection: desc,
          first: {limit},
          skip: {offset}
        ) {{
          move {{
            tx {{
              id
              height
              timestamp
            }}
            name {{
              ns {{
                ns
              }}
              name
            }}
          }}
          gamemove
        }}
      }}
    """.format (where=where, limit=BATCH_SIZE + 1, offset=offset)
    data = self.subgraph.query (query)
    moves = data["gameMoves"]

    more = False
    if len (moves) > BATCH_SIZE:
      more = True
      moves = moves[:-1]

    return {
      "moves": [{
        "tx": {
          "id": m["move"]["tx"]["id"],
          "height": m["move"]["tx"]["height"],
          "timestamp": m["move"]["tx"]["timestamp"]
        },
        "name": {
          "ns": m["move"]["name"]["ns"]["ns"],
          "name": m["move"]["name"]["name"]
        },
        "gamemove": m["gamemove"],
      } for m in moves],
      "more": more,
    }

  def getMovesForName (self, ns, name, fromTimestamp=None, toTimestamp=None, offset=0):
    """
    Returns a batch of moves for a given name, ordered newest first, optionally
    filtered within a range of timestamps.  Using null for either timestamp
    disables filtering by this timestamp.
    """
    tokenId = self.contract_tools.nameToTokenId (ns, name)
    if isinstance (tokenId, str) and tokenId.startswith ("Error:"):
      return tokenId
    tokenIdHex = self._to_hex_id (tokenId)

    conditions = [f'{{name: "{tokenIdHex}"}}']
    if fromTimestamp is not None:
      conditions.append (f'{{tx_: {{timestamp_gte: {fromTimestamp}}}}}')
    if toTimestamp is not None:
      conditions.append (f'{{tx_: {{timestamp_lte: {toTimestamp}}}}}')
    conditions = ', '.join (conditions)

    query = """
      query {{
        moves (
          where: {{and: [{conditions}]}},
          orderBy: tx__timestamp,
          orderDirection: desc,
          first: {limit},
          skip: {offset}
        ) {{
          tx {{
            id
            height
            timestamp
          }}
          games {{
            game {{
              game
            }}
          }}
          move
        }}
      }}
    """.format (conditions=conditions, limit=BATCH_SIZE + 1, offset=offset)
    data = self.subgraph.query (query)
    moves = data["moves"]

    more = False
    if len (moves) > BATCH_SIZE:
      more = True
      moves = moves[:-1]

    return {
      "moves": [{
        "tx": {
          "id": m["tx"]["id"],
          "height": m["tx"]["height"],
          "timestamp": m["tx"]["timestamp"]
        },
        "games": [g["game"]["game"] for g in m["games"]],
        "move": m["move"],
      } for m in moves],
      "more": more,
    }
