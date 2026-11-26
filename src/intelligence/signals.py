from __future__ import annotations  # Allow modern type annotations (like `X | None`) without runtime issues on older Python versions

import math  # Import standard math helpers for square roots and finiteness checks (`math.isfinite`)
from dataclasses import dataclass  # Import `dataclass` decorator to define clean, structured result containers
from typing import Iterable, Sequence  # Import typing helpers for general iterables and ordered sequences


@dataclass(frozen=True)  # Make `AnomalyResult` immutable (`frozen=True`) so computed signal outputs aren't accidentally mutated
class AnomalyResult:  # Define a structured output record representing one Z-score anomaly evaluation
    item_id: str  # Unique identifier for the item/product/metric being checked
    observed_value: float  # The latest/current value being evaluated against history
    baseline_mean: float  # Average value of the historical baseline series
    baseline_std: float  # Sample standard deviation of the historical baseline series
    z_score: float | None  # Computed Z-score, or `None` when Z-score isn't defined (e.g., <2 points or zero variance)
    is_anomaly: bool  # Boolean flag indicating whether the observation exceeded the anomaly rule
    reason: str  # Short diagnostic tag explaining *why* `is_anomaly` is True or False


@dataclass(frozen=True)  # Make `CandidateMatch` immutable so candidate similarity records stay intact downstream
class CandidateMatch:  # Define a structured output record representing a potential semantic catalog match
    source_id: str  # Identifier of the source record being matched
    candidate_id: str  # Identifier of a candidate record compared against the source
    similarity_score: float  # Cosine similarity score between the two embeddings
    meets_similarity_threshold: bool  # Indicates whether `similarity_score` met or exceeded the threshold


def compute_z_score_anomaly(  # Define function to evaluate whether an observed value is anomalous vs. a baseline series
    item_id: str,  # ID of the item/record under evaluation
    observed_value: float,  # Current observed numeric value to test
    baseline_values: Sequence[float],  # Historical baseline values used to compute mean and spread
    z_threshold: float = 3.0,  # Default absolute Z-score cutoff (3.0 standard deviations) for flagging anomalies
) -> AnomalyResult:  # Return an `AnomalyResult` instance
    """Flag numeric observations that deviate sharply from a baseline series."""  # Docstring summarizing the function's purpose
    cleaned = [float(v) for v in baseline_values if v is not None and math.isfinite(v)]  # Filter out `None`, `NaN`, and `+/-inf`, converting valid items to `float`
    if len(cleaned) < 2:  # Check if we have fewer than 2 valid points (sample variance requires at least 2 observations)
        return AnomalyResult(  # Return a safe non-crashing result when baseline history is too short
            item_id=item_id,  # Preserve item ID
            observed_value=observed_value,  # Preserve observed value
            baseline_mean=cleaned[0] if cleaned else 0.0,  # Use the single available point as mean if 1 exists, else `0.0`
            baseline_std=0.0,  # Standard deviation is `0.0` when fewer than 2 points exist
            z_score=None,  # No Z-score computed because spread isn't established
            is_anomaly=False,  # Do not raise a statistical Z-score anomaly with insufficient baseline history
            reason="insufficient_baseline_history",  # Explicitly record why Z-score wasn't evaluated
        )  # End of `AnomalyResult` return for short baseline

    mean = sum(cleaned) / len(cleaned)  # Compute the arithmetic mean ($\mu$) of cleaned baseline values
    variance = sum((v - mean) ** 2 for v in cleaned) / (len(cleaned) - 1)  # Compute unbiased sample variance using `n - 1` degrees of freedom
    std = math.sqrt(variance)  # Compute sample standard deviation ($\sigma$) as the square root of variance

    if std == 0.0:  # Guard against division by zero when all baseline values are identical
        is_anomaly = float(observed_value) != mean  # Flag a shift if the observed value differs from the constant baseline
        return AnomalyResult(  # Return result tailored to zero-variance baselines
            item_id=item_id,  # Preserve item ID
            observed_value=observed_value,  # Preserve observed value
            baseline_mean=mean,  # Store the constant baseline mean
            baseline_std=0.0,  # Explicitly record zero standard deviation
            z_score=None,  # Set `z_score` to `None` since `(x - mean) / 0` is undefined
            is_anomaly=is_anomaly,  # True if `observed_value` broke away from the constant baseline
            reason="zero_baseline_variance_shift" if is_anomaly else "constant_baseline_match",  # Explain whether baseline shifted or stayed flat
        )  # End of `AnomalyResult` return for zero-variance case

    z_score = (float(observed_value) - mean) / std  # Calculate standard Z-score: how many standard deviations `observed_value` is from `mean`
    is_anomaly = abs(z_score) >= z_threshold  # Flag as anomaly if magnitude of `z_score` meets or exceeds `z_threshold`
    return AnomalyResult(  # Return full `AnomalyResult` for normal non-zero-variance baseline evaluation
        item_id=item_id,  # Preserve item ID
        observed_value=observed_value,  # Preserve observed value
        baseline_mean=round(mean, 4),  # Round baseline mean to 4 decimal places for clean serialization/display
        baseline_std=round(std, 4),  # Round baseline standard deviation to 4 decimal places
        z_score=round(z_score, 4),  # Round computed Z-score to 4 decimal places
        is_anomaly=is_anomaly,  # Store whether the threshold check triggered
        reason="z_threshold_exceeded" if is_anomaly else "within_expected_band",  # Record clear status reason for downstream/LLM inspection
    )  # End of `AnomalyResult` return


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:  # Define helper to compute cosine similarity between two vectors
    """Compute cosine similarity between two equal-length embedding vectors."""  # Docstring describing vector similarity calculation
    if len(vec_a) != len(vec_b) or not vec_a:  # Validate that both vectors are non-empty and share the same dimensionality
        raise ValueError("Vectors must be non-empty and of equal length.")  # Raise an explicit error on mismatched or empty vectors

    dot = sum(a * b for a, b in zip(vec_a, vec_b))  # Compute dot product ($A \cdot B$) across paired coordinates
    norm_a = math.sqrt(sum(a * a for a in vec_a))  # Compute Euclidean norm ($\|A\|_2$) of the first vector
    norm_b = math.sqrt(sum(b * b for b in vec_b))  # Compute Euclidean norm ($\|B\|_2$) of the second vector

    if norm_a == 0.0 or norm_b == 0.0:  # Avoid division by zero if either vector is all zeros
        return 0.0  # Return `0.0` similarity for a zero-magnitude vector

    return dot / (norm_a * norm_b)  # Return cosine similarity in `[-1.0, 1.0]` (dot product divided by product of norms)


def find_similarity_candidates(  # Define function to filter and rank candidate matches above a similarity threshold
    source_id: str,  # ID of the source item being matched
    source_embedding: Sequence[float],  # Embedding vector of the source item
    candidates: Iterable[tuple[str, Sequence[float]]],  # Iterable of `(candidate_id, candidate_embedding)` pairs to compare against
    threshold: float = 0.92,  # Minimum similarity cutoff (default `0.92`) to qualify as a candidate match
) -> list[CandidateMatch]:  # Return a list of `CandidateMatch` objects
    """Return candidate pairs above the similarity threshold, sorted descending."""  # Docstring explaining candidate filtering and ranking
    matches: list[CandidateMatch] = []  # Initialize list to collect qualifying candidate matches
    for candidate_id, cand_embedding in candidates:  # Iterate through each candidate ID and its embedding vector
        if candidate_id == source_id:  # Skip self-comparison so an item does not match against itself
            continue  # Move to the next candidate
        score = cosine_similarity(source_embedding, cand_embedding)  # Compute similarity between source and candidate embeddings
        if score >= threshold:  # Check if candidate meets or exceeds the configured similarity threshold
            matches.append(  # Append a `CandidateMatch` record for downstream attribute/SKU verification
                CandidateMatch(  # Construct `CandidateMatch` instance
                    source_id=source_id,  # Record source item ID
                    candidate_id=candidate_id,  # Record candidate item ID
                    similarity_score=round(score, 4),  # Round similarity score to 4 decimal places
                    meets_similarity_threshold=True,  # Mark that this candidate passed the similarity cutoff
                )  # End of `CandidateMatch` construction
            )  # End of `matches.append`
    matches.sort(key=lambda m: m.similarity_score, reverse=True)  # Sort matches from highest to lowest similarity score
    return matches  # Return the ranked list of candidate matches
