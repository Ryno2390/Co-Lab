import ipfshttpclient
from ..config import settings
import asyncio # Although ipfshttpclient is primarily synchronous, we might wrap calls

# --- IPFS Client Initialization ---

# Get IPFS API multiaddress from settings
# Defaulting to standard local node API address
# Example format: '/ip4/127.0.0.1/tcp/5001' or '/dns/ipfs.infura.io/tcp/5001/https'
# TODO: Add IPFS_API_MULTIADDR to config/settings.py and .env file
IPFS_API_ADDR = getattr(settings, "IPFS_API_MULTIADDR", "/ip4/127.0.0.1/tcp/5001")

# Define a timeout for IPFS operations (in seconds)
DEFAULT_IPFS_TIMEOUT = 60.0

client = None
try:
    # Connect to the IPFS daemon API
    # Note: ipfshttpclient doesn't have native async support for all operations yet.
    # We might run synchronous calls in an executor for async compatibility.
    client = ipfshttpclient.connect(addr=IPFS_API_ADDR, timeout=DEFAULT_IPFS_TIMEOUT)
    # Verify connection with a simple command
    node_id = client.id()
    print(f"Successfully connected to IPFS node: {IPFS_API_ADDR} (ID: ...{node_id['ID'][-6:]})")
except Exception as e:
    print(f"Error connecting to IPFS node at {IPFS_API_ADDR}: {e}")
    print("IPFS functionality will be unavailable.")
    client = None

# --- Client Functions ---

async def get_ipfs_content(cid: str, timeout: float = DEFAULT_IPFS_TIMEOUT) -> bytes | None:
    """
    Fetches content from IPFS corresponding to the given CID.

    Args:
        cid: The IPFS Content Identifier (string).
        timeout: Operation timeout in seconds.

    Returns:
        The content as bytes if successful, None otherwise.
    """
    if not client:
        print("Error: IPFS client not connected.")
        return None

    print(f"Attempting to fetch content for CID: {cid}")
    try:
        # ipfshttpclient.Client.cat is synchronous, run it in a thread pool executor
        # to avoid blocking the asyncio event loop.
        loop = asyncio.get_running_loop()
        # The 'timeout' parameter in client.cat might behave differently than httpx timeout.
        # Consider adding explicit asyncio.wait_for if needed.
        content_bytes = await loop.run_in_executor(
            None, # Use default ThreadPoolExecutor
            lambda: client.cat(cid, timeout=timeout)
        )
        print(f"Successfully fetched {len(content_bytes)} bytes for CID: {cid}")
        return content_bytes
    except ipfshttpclient.exceptions.ErrorResponse as e:
        # Handle errors like CID not found, etc.
        print(f"IPFS ErrorResponse fetching CID {cid}: {e.args[0] if e.args else 'Unknown IPFS Error'}")
        return None
    except Exception as e:
        # Handle other potential errors (timeouts, connection issues during call)
        print(f"Unexpected error fetching CID {cid}: {e}")
        return None

async def add_content_to_ipfs(content: bytes, timeout: float = DEFAULT_IPFS_TIMEOUT) -> str | None:
    """
    Adds content (as bytes) to IPFS.

    Args:
        content: The content to add as bytes.
        timeout: Operation timeout in seconds.

    Returns:
        The CID of the added content if successful, None otherwise.
    """
    if not client:
        print("Error: IPFS client not connected.")
        return None

    print(f"Attempting to add {len(content)} bytes to IPFS...")
    try:
        loop = asyncio.get_running_loop()
        # client.add_bytes is synchronous
        result = await loop.run_in_executor(
            None,
            lambda: client.add_bytes(content, timeout=timeout)
        )
        # result is usually a dict like {'Hash': 'Qm...', 'Name': '...', 'Size': '...'} or just the hash string depending on version/options
        cid = result if isinstance(result, str) else result.get('Hash')
        if cid:
            print(f"Successfully added content to IPFS. CID: {cid}")
            return cid
        else:
            print(f"Failed to add content to IPFS, unexpected result format: {result}")
            return None
    except ipfshttpclient.exceptions.ErrorResponse as e:
        print(f"IPFS ErrorResponse adding content: {e.args[0] if e.args else 'Unknown IPFS Error'}")
        return None
    except Exception as e:
        print(f"Unexpected error adding content to IPFS: {e}")
        return None

# Example Usage (within an async function):
# async def main():
#     cid_to_fetch = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi" # Example CID (IPFS logo)
#     content = await get_ipfs_content(cid_to_fetch)
#     if content:
#         print(f"Fetched content, size: {len(content)}")
#         # You can save or process the bytes
#
#     new_cid = await add_content_to_ipfs(b"Hello IPFS from Co-Lab!")
#     if new_cid:
#         print(f"Added test content with CID: {new_cid}")