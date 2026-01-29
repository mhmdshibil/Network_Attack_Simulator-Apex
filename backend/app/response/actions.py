# actions.py
# This file contains the logic for executing response actions.

def execute_actions(ip: str, actions: list, reason: str = ""):
    """
    Simulate the execution of a list of response actions for a given IP address.
    """
    results = []

    # Iterate over the list of actions.
    for action in actions:
        # If the action is to block the IP, create a result dictionary for it.
        if action == "block_ip":
            results.append({
                "action": "block_ip",
                "ip": ip,
                "status": "executed",
                "reason": reason
            })

        # If the action is to rate limit the IP, create a result dictionary for it.
        elif action == "rate_limit":
            results.append({
                "action": "rate_limit",
                "ip": ip,
                "status": "executed",
                "reason": reason
            })

        # If the action is unknown, create a result dictionary with an "ignored" status.
        else:
            results.append({
                "action": action,
                "ip": ip,
                "status": "ignored",
                "reason": "unknown action"
            })

    # Return the list of action results.
    return results