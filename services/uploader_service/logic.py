import asyncio
import httpx
from typing import Dict, Any, Optional

# Import necessary clients and services from shared modules
# Assumes monorepo structure or installed package
try:
    from ...data_layer import ipfs_client
    from ...tokenomics import service as tokenomics_service
    from ...tokenomics import ledger # Import ledger module for DB functions
    from ...config import settings
    # Need the URL for the indexer's announcement endpoint
    INDEXER_ANNOUNCE_URL = getattr(settings, "INDEXER_API_URL", "http://localhost:8010") + "/announce"
    INTERNAL_API_KEY = getattr(settings, "INTERNAL_API_KEY", "change-this-in-production")
except ImportError:
    print("Warning: Could not import shared modules (ipfs_client, tokenomics_service, ledger, settings). Using simulations.")
    ipfs_client = None
    tokenomics_service = None
    ledger = None # Set ledger to None if import fails
    INDEXER_ANNOUNCE_URL = "http://localhost:8010/announce" # Fallback
    INTERNAL_API_KEY = "change-this-in-production" # Fallback

# Removed in-memory cache and placeholder functions for duplicate check

async def announce_to_indexer(cid: str, user_metadata: Optional[Dict[str, Any]], uploader_id: Optional[str]):
    """Sends announcement to the Indexer Service webhook."""
    payload = {
        "cid": cid,
        "uploader_id": uploader_id,
        "user_metadata": user_metadata or {},
        # Add timestamp if needed
    }
    headers = {"X-API-Key": INTERNAL_API_KEY} # Use internal API key
    try:
        async with httpx.AsyncClient() as client:
            print(f"Announcing CID {cid} to Indexer at {INDEXER_ANNOUNCE_URL}")
            response = await client.post(INDEXER_ANNOUNCE_URL, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status() # Check for HTTP errors
            print(f"Announcement for CID {cid} accepted by Indexer.")
            return True
    except Exception as e:
        print(f"Error announcing CID {cid} to Indexer: {e}")
        # Decide how to handle announcement failure - log, retry later?
        return False


async def handle_upload(
    user_id: str,
    content_bytes: bytes,
    user_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handles the logic for uploading content, checking quality, awarding rewards, and announcing.

    Args:
        user_id: Identifier of the user uploading.
        content_bytes: The file content as bytes.
        user_metadata: Metadata provided by the user.

    Returns:
        A dictionary containing {'cid': str|None, 'reward_amount': float|None, 'error': str|None}
    """
    cid: Optional[str] = None
    reward_amount: float = 0.0
    error_message: Optional[str] = None
    file_size_bytes = len(content_bytes)

    # Ensure necessary modules were imported
    if not ipfs_client or not tokenomics_service or not ledger or not settings:
         return {
             "cid": None, "reward_amount": None,
             "error": "Upload service configuration error (missing dependencies)."
         }

    try:
        # 1. Add to IPFS
        cid = await ipfs_client.add_content_to_ipfs(content_bytes)
        if not cid:
            raise IOError("Failed to add content to IPFS.")
        print(f"Successfully added to IPFS: {cid}")

        # 2. Perform Quality & Duplicate Checks (V1)
        # Use ledger function for persistent check
        is_duplicate = await ledger.check_if_rewarded(cid)
        # Basic size check is implicitly done by reward calculation logic

        if is_duplicate:
            print(f"CID {cid} is a duplicate, no reward will be issued.")
            reward_amount = 0.0 # Ensure reward is zero
        else:
            # 3. Calculate Reward (only if not duplicate)
            reward_amount = tokenomics_service.calculate_data_reward(file_size_bytes, user_metadata)

            # 4. Award Reward (if applicable)
            if reward_amount > 0:
                reward_success = await tokenomics_service.reward_user_for_data(user_id, reward_amount)
                if reward_success:
                    # Use ledger function to mark as rewarded
                    await ledger.add_rewarded_upload(cid)
                else:
                    print(f"Warning: Failed to credit reward to user {user_id} for CID {cid}")
                    reward_amount = 0.0 # Reset reward amount if crediting failed

        # 5. Announce to Indexer (regardless of reward status, but only if IPFS add succeeded)
        await announce_to_indexer(cid, user_metadata, user_id)

    except Exception as e:
        print(f"Error during upload handling for user {user_id}: {e}")
        error_message = str(e)
        # Reset potentially partially assigned values on error
        cid = None # Don't return CID if overall process failed after IPFS add
        reward_amount = 0.0

    return {
        "cid": cid, # Return CID only if IPFS add succeeded and no later *critical* error occurred
        "reward_amount": reward_amount if reward_amount > 0 else None,
        "error": error_message
    }