def execute_actions(ip: str, actions: list, reason: str = ""):
    results = []

    for action in actions:
        if action == "block_ip":
            results.append({
                "action": "block_ip",
                "ip": ip,
                "status": "executed",
                "reason": reason
            })

        elif action == "rate_limit":
            results.append({
                "action": "rate_limit",
                "ip": ip,
                "status": "executed",
                "reason": reason
            })

        else:
            results.append({
                "action": action,
                "ip": ip,
                "status": "ignored",
                "reason": "unknown action"
            })

    return results