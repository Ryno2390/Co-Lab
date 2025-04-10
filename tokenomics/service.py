from typing import List, Dict, Any, Optional
import math

# Use Decimal for precise calculations if needed, especially for currency/tokens
# from decimal import Decimal, getcontext
# getcontext().prec = 18 # Set precision

from ..config import settings
# Assuming ledger functions are in ledger.py within the same package
from . import ledger
# Assuming routing decision model is available
# Adjust import path if needed
from ..core_ai.routing import RoutingDecision

# --- V1 Cost Parameters (Load from Settings) ---
# TODO: Add these specific cost parameters to config/settings.py and .env
BASE_FEE = float(getattr(settings, "TOKEN_BASE_FEE", 1.0))
DECOMPOSITION_COST = float(getattr(settings, "TOKEN_DECOMPOSITION_COST", 5.0))
ROUTING_COST_PER_TASK = float(getattr(settings, "TOKEN_ROUTING_COST_PER_TASK", 0.5))
SYNTHESIS_COST = float(getattr(settings, "TOKEN_SYNTHESIS_COST", 10.0))
# Tiered invocation costs
INVOCATION_COSTS = {
    "simple_fixed": float(getattr(settings, "TOKEN_INVOCATION_SIMPLE_FIXED", 2.0)),
    "complex_fixed": float(getattr(settings, "TOKEN_INVOCATION_COMPLEX_FIXED", 5.0)),
    "dynamic": float(getattr(settings, "TOKEN_INVOCATION_DYNAMIC", 10.0)),
}
# Mapping specific fixed specialist IDs (or tags) to cost tiers
# TODO: Refine this mapping based on actual specialists
SPECIALIST_COST_TIERS = {
    "SummarizationAI": "simple_fixed",
    "QuestionAnsweringAI": "simple_fixed",
    "IPFSSearchAndRetrieveAI": "complex_fixed",
    "CodeGeneratorAI": "complex_fixed",
    "DataAnalysisAI": "complex_fixed",
    # Add other fixed specialists here
}

# --- V1 Reward Parameters (Load from Settings) ---
# TODO: Add these reward parameters to config/settings.py and .env
REWARD_PER_MB = float(getattr(settings, "TOKEN_REWARD_PER_MB", 0.01))
METADATA_BONUS = float(getattr(settings, "TOKEN_METADATA_BONUS", 0.5))
# Required metadata fields for bonus
REQUIRED_METADATA_FIELDS = ["filename", "description", "tags"]
# File size limits for rewards
MIN_FILE_SIZE_BYTES = int(getattr(settings, "REWARD_MIN_FILE_SIZE_BYTES", 1)) # Min 1 byte
MAX_FILE_SIZE_BYTES = int(getattr(settings, "REWARD_MAX_FILE_SIZE_BYTES", 1 * 1024**3)) # Max 1 GB example

# --- Service Functions ---

def calculate_query_cost(routing_decisions: List[RoutingDecision]) -> float:
    """
    Calculates the total cost for processing a query based on V1 pricing model.

    Args:
        routing_decisions: List of routing decisions made for the query's sub-tasks.

    Returns:
        The total calculated cost in COLAB tokens.
    """
    num_sub_tasks = len(routing_decisions)
    total_invocation_cost = 0.0

    for decision in routing_decisions:
        if decision.route_type == 'fixed_specialist':
            specialist_id = decision.target_id or "unknown"
            # Determine cost tier based on specialist ID (or tags in metadata later)
            tier = SPECIALIST_COST_TIERS.get(specialist_id, "complex_fixed") # Default to complex if unknown
            total_invocation_cost += INVOCATION_COSTS.get(tier, 0.0)
        elif decision.route_type == 'dynamic_instance':
            total_invocation_cost += INVOCATION_COSTS.get("dynamic", 0.0)

    total_cost = (
        BASE_FEE +
        DECOMPOSITION_COST +
        (num_sub_tasks * ROUTING_COST_PER_TASK) +
        total_invocation_cost +
        SYNTHESIS_COST
    )

    print(f"Calculated Query Cost: Base({BASE_FEE}) + Decomp({DECOMPOSITION_COST}) + "
          f"Routing({num_sub_tasks}*{ROUTING_COST_PER_TASK}={num_sub_tasks * ROUTING_COST_PER_TASK}) + "
          f"Invocation({total_invocation_cost}) + Synthesis({SYNTHESIS_COST}) = {total_cost}")

    # Return cost, perhaps rounded or as Decimal
    return round(total_cost, 8) # Round to typical token precision

async def charge_user_for_query(user_id: str, cost: float) -> bool:
    """
    Attempts to deduct the query cost from the user's balance.

    Args:
        user_id: The ID of the user to charge.
        cost: The amount to deduct.

    Returns:
        True if the charge was successful, False otherwise (e.g., insufficient funds).
    """
    if not user_id:
        print("Error: Cannot charge user without user_id.")
        return False
    if cost <= 0:
        print("Info: Query cost is zero or negative, no charge applied.")
        return True # No cost means success

    print(f"Attempting to charge user '{user_id}' {cost:.8f} COLAB...")
    success = await ledger.update_user_balance(user_id, -abs(cost)) # Ensure cost is negative for debit
    if success:
        print(f"Successfully charged user '{user_id}'.")
    else:
        print(f"Failed to charge user '{user_id}' (likely insufficient funds).")
    return success

def _check_quality_v1(file_size_bytes: int, metadata: Optional[Dict[str, Any]]) -> bool:
    """Performs basic V1 quality checks."""
    if not (MIN_FILE_SIZE_BYTES <= file_size_bytes <= MAX_FILE_SIZE_BYTES):
        print(f"Quality Check Fail: File size {file_size_bytes} bytes outside limits.")
        return False
    # Duplicate CID check should happen before calling reward calculation
    return True

def _check_metadata_bonus_v1(metadata: Optional[Dict[str, Any]]) -> bool:
    """Checks if required metadata fields are present and non-empty."""
    if not metadata:
        return False
    for field in REQUIRED_METADATA_FIELDS:
        if not metadata.get(field): # Checks for key existence and non-empty value
            print(f"Metadata Bonus Check Fail: Missing or empty required field '{field}'.")
            return False
    return True

def calculate_data_reward(file_size_bytes: int, metadata: Optional[Dict[str, Any]]) -> float:
    """
    Calculates the data contribution reward based on V1 model after basic checks.
    Assumes duplicate CID check happened *before* calling this.

    Args:
        file_size_bytes: Size of the uploaded file in bytes.
        metadata: User-provided metadata dictionary.

    Returns:
        The calculated reward amount in COLAB tokens (0.0 if checks fail).
    """
    if not _check_quality_v1(file_size_bytes, metadata):
        return 0.0

    file_size_mb = file_size_bytes / (1024 * 1024)
    size_reward = file_size_mb * REWARD_PER_MB

    bonus = 0.0
    if _check_metadata_bonus_v1(metadata):
        bonus = METADATA_BONUS
        print("Metadata bonus applicable.")
    else:
        print("Metadata bonus not applicable.")

    total_reward = size_reward + bonus
    print(f"Calculated Data Reward: Size({size_reward:.8f}) + Bonus({bonus:.8f}) = {total_reward:.8f}")
    return round(total_reward, 8)

async def reward_user_for_data(user_id: str, reward: float) -> bool:
    """
    Credits a user's balance with the calculated data contribution reward.

    Args:
        user_id: The ID of the user to reward.
        reward: The amount to credit.

    Returns:
        True if the credit was successful, False otherwise.
    """
    if not user_id:
        print("Error: Cannot reward user without user_id.")
        return False
    if reward <= 0:
        print("Info: Reward amount is zero or negative, no reward applied.")
        return True # No reward is still a "success" in terms of the operation

    print(f"Attempting to reward user '{user_id}' {reward:.8f} COLAB...")
    # Use abs(reward) to ensure we are crediting
    success = await ledger.update_user_balance(user_id, abs(reward))
    if success:
        print(f"Successfully rewarded user '{user_id}'.")
    else:
        print(f"Failed to reward user '{user_id}' (ledger update failed).")
    return success