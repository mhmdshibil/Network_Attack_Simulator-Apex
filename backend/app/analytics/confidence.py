# confidence.py
# This file contains the logic for computing a confidence score for detected attack correlations.

def compute_confidence(correlations: list) -> float:
    """
    Compute confidence score (0.0 - 1.0) for detected attack correlations.
    Confidence represents how sure the system is about the risk assessment.
    """

    # If there are no correlations, the confidence is 0.
    if not correlations:
        return 0.0

    # Calculate a score based on the total number of events.
    total_events = sum(c.get("count", 1) for c in correlations)

    if total_events >= 20:
        volume_score = 1.0
    elif total_events >= 10:
        volume_score = 0.7
    elif total_events >= 5:
        volume_score = 0.4
    else:
        volume_score = 0.2

    # Calculate a score based on whether there was a burst of activity.
    burst_score = 1.0 if any(c.get("burst") for c in correlations) else 0.3

    # Calculate a score based on the diversity of attack labels.
    unique_labels = len({c.get("label") for c in correlations})
    if unique_labels >= 3:
        diversity_score = 1.0
    elif unique_labels == 2:
        diversity_score = 0.6
    else:
        diversity_score = 0.3

    # Calculate a score based on the temporal diversity of the events.
    timestamps = {c.get("timestamp") for c in correlations}
    temporal_score = 0.7 if len(timestamps) > 1 else 0.3

    # Combine the scores with different weights to get a final confidence score.
    confidence = (
        volume_score * 0.35 +
        burst_score * 0.30 +
        diversity_score * 0.20 +
        temporal_score * 0.15
    )

    # Return the confidence score, rounded to 2 decimal places and capped at 1.0.
    return round(min(confidence, 1.0), 2)