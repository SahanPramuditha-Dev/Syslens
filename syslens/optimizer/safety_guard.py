def validate_action(action_type: str) -> bool:
    """
    Validate that the optimization or cleanup action is safe to run.
    Returns False if action_type matches any restricted settings.
    """
    restricted = [
        "registry_edit",
        "driver_modification",
        "system32_delete"
    ]

    return action_type not in restricted
