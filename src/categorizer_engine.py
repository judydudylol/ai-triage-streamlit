"""
Categorizer Engine
Matches emergency cases to Catergorizer.json entries using fuzzy matching.

Features:
- Multi-stage matching (exact → token overlap → partial)
- Jaccard similarity scoring
- Keyword extraction and weighting
- Alternative suggestions for disambiguation
- Caching for performance

Uses normalized case names from data_loader for consistent matching.
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from functools import lru_cache
import logging

from .data_loader import normalize_case_name

logger = logging.getLogger(__name__)


@dataclass
class TriageResult:
    """
    Result of emergency case categorization.
    
    Attributes:
        case_name: Original input query
        case_name_matched: Matched case name from Catergorizer
        category: Medical category (Cardiac, Respiratory, etc.)
        severity: Severity string (Critical, High, etc.)
        severity_level: Numeric severity 0-3
        harm_threshold_min: Minimum time to irreversible harm (minutes)
        harm_threshold_max: Maximum time to irreversible harm (minutes)
        harm_threshold_raw: Original time string (e.g., "4-6 m")
        confidence: Match confidence 0.0-1.0
        match_method: How the match was found
        matched_keywords: List of keywords that matched
        intervention: First 5 minutes intervention instructions
        equipment: Required medical equipment
        ctas: Canadian Triage and Acuity Scale (1-5)
        alternatives: Alternative matches [(case_name, score)]
    """
    case_name: str
    case_name_matched: str
    category: str
    severity: str
    severity_level: int
    harm_threshold_min: int
    harm_threshold_max: int
    harm_threshold_raw: str
    confidence: float
    match_method: str
    matched_keywords: List[str]
    intervention: str
    equipment: str
    ctas: int
    alternatives: List[Tuple[str, float]]


# =============================================================================
# TEXT PROCESSING UTILITIES
# =============================================================================

# Common medical stopwords that don't help matching
MEDICAL_STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 
    'with', 'after', 'before', 'is', 'are', 'was', 'were', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
    'could', 'may', 'might', 'must', 'can', 'be', 'am', 'patient', 'person'
}

# High-value keywords that indicate specific conditions
CRITICAL_KEYWORDS = {
    'cardiac', 'arrest', 'anaphylaxis', 'stroke', 'seizure', 'unconscious',
    'bleeding', 'choking', 'trauma', 'collapse', 'respiratory', 'asthma',
    'copd', 'heart', 'chest', 'pain', 'breathing', 'airway', 'hypoglycemic'
}


@lru_cache(maxsize=256)
def _tokenize(text: str) -> Set[str]:
    """
    Convert text to set of lowercase tokens for matching.
    
    Caching improves performance for repeated queries.
    
    Args:
        text: Input text to tokenize
    
    Returns:
        Set of normalized tokens
    
    Examples:
        >>> _tokenize("Cardiac Arrest!")
        {'cardiac', 'arrest'}
        >>> _tokenize("Severe chest pain")
        {'severe', 'chest', 'pain'}
    """
    if not text:
        return set()
    
    # Lowercase, remove punctuation, split on whitespace
    clean = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # Split and remove stopwords
    tokens = set(clean.split()) - MEDICAL_STOPWORDS
    
    return tokens


def _jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """
    Calculate Jaccard similarity coefficient between two sets.
    
    Formula: |A ∩ B| / |A ∪ B|
    
    Args:
        set1: First set
        set2: Second set
    
    Returns:
        Similarity score 0.0-1.0
    
    Examples:
        >>> _jaccard_similarity({'cardiac', 'arrest'}, {'cardiac', 'arrest'})
        1.0
        >>> _jaccard_similarity({'cardiac'}, {'respiratory'})
        0.0
    """
    if not set1 or not set2:
        return 0.0
    
    intersection = set1 & set2
    union = set1 | set2
    
    return len(intersection) / len(union) if union else 0.0


def _token_overlap_score(query_tokens: Set[str], case_tokens: Set[str]) -> float:
    """
    Calculate weighted match score based on token overlap.
    
    Weighting Strategy:
    - 60% query coverage (what % of query words matched)
    - 40% Jaccard similarity (balance of overlap vs total)
    
    This prioritizes matching the user's query terms while still
    considering the overall similarity.
    
    Args:
        query_tokens: Tokens from user query
        case_tokens: Tokens from database case
    
    Returns:
        Weighted score 0.0-1.0
    """
    if not query_tokens or not case_tokens:
        return 0.0
    
    intersection = query_tokens & case_tokens
    
    # Query coverage: fraction of query terms that matched
    query_coverage = len(intersection) / len(query_tokens) if query_tokens else 0.0
    
    # Jaccard similarity for balance
    jaccard = _jaccard_similarity(query_tokens, case_tokens)
    
    # Weighted combination
    score = 0.6 * query_coverage + 0.4 * jaccard
    
    return score


def _keyword_bonus(query_tokens: Set[str], case_tokens: Set[str]) -> float:
    """
    Calculate bonus for matching critical medical keywords.
    
    Args:
        query_tokens: Query tokens
        case_tokens: Case tokens
    
    Returns:
        Bonus score 0.0-0.2
    """
    query_critical = query_tokens & CRITICAL_KEYWORDS
    case_critical = case_tokens & CRITICAL_KEYWORDS
    matching_critical = query_critical & case_critical
    
    if not matching_critical:
        return 0.0
    
    # Bonus based on number of critical keywords matched
    return min(0.2, len(matching_critical) * 0.1)


# =============================================================================
# CATEGORIZATION FUNCTIONS
# =============================================================================

def categorize(
    case_description: str,
    symptoms: List[str],
    categorizer_data: List[Dict],
) -> Optional[TriageResult]:
    """
    Categorize an emergency case using the Catergorizer.json database.
    
    Matching Strategy (in order):
    1. Exact match after normalization (confidence: 1.0)
    2. High token overlap (confidence: 0.7-0.95)
    3. Moderate token overlap (confidence: 0.4-0.7)
    4. Fallback match (confidence: 0.1-0.4)
    
    Args:
        case_description: Free-text case description or name
        symptoms: List of symptom strings (optional)
        categorizer_data: Data from data_loader.load_categorizer()
    
    Returns:
        TriageResult with best match, or None if no match found
    
    Examples:
        >>> data = load_categorizer()
        >>> result = categorize("cardiac arrest", [], data)
        >>> result.case_name_matched
        'Cardiac Arrest'
        >>> result.confidence
        1.0
    """
    if not categorizer_data:
        logger.warning("Empty categorizer data")
        return None
    
    # Build combined query from description + symptoms
    query_text = (case_description or "").strip()
    if symptoms:
        query_text += " " + " ".join(symptoms)
    
    if not query_text:
        logger.warning("Empty query text")
        return None
    
    query_normalized = normalize_case_name(query_text)
    query_tokens = _tokenize(query_text)
    
    logger.info(f"Categorizing query: '{case_description}' ({len(query_tokens)} tokens)")
    
    # === STAGE 1: Exact match after normalization ===
    for case in categorizer_data:
        if query_normalized == case.get("case_name_normalized", ""):
            logger.info(f"Exact match found: {case['case_name']}")
            return _create_result(
                case_description=case_description,
                case=case,
                confidence=1.0,
                match_method="exact",
                matched_keywords=[query_normalized],
                alternatives=[]
            )
    
    # === STAGE 2: Token overlap matching with scoring ===
    scored_matches = []
    
    for case in categorizer_data:
        case_name = case.get("case_name", "")
        case_desc = case.get("description", "")
        case_text = f"{case_name} {case_desc}"
        case_tokens = _tokenize(case_text)
        
        # Base score from token overlap
        score = _token_overlap_score(query_tokens, case_tokens)
        
        # Bonus 1: Substring match in normalized case name
        if query_normalized in case.get("case_name_normalized", ""):
            score += 0.3
        elif case.get("case_name_normalized", "") in query_normalized:
            score += 0.25
        
        # Bonus 2: Category keyword match
        category_tokens = _tokenize(case.get("category", ""))
        if query_tokens & category_tokens:
            score += 0.1
        
        # Bonus 3: Critical medical keywords
        score += _keyword_bonus(query_tokens, case_tokens)
        
        # Track matched keywords
        matched_kw = list(query_tokens & case_tokens)
        
        # Clamp score to [0, 1]
        score = min(1.0, score)
        
        scored_matches.append((case, score, matched_kw))
    
    # Sort by score descending
    scored_matches.sort(key=lambda x: x[1], reverse=True)
    
    # Check if best match is good enough
    if not scored_matches or scored_matches[0][1] < 0.1:
        logger.warning(f"No good match found for '{case_description}'")
        return None
    
    best_case, best_score, matched_kw = scored_matches[0]
    
    logger.info(f"Best match: {best_case['case_name']} (score: {best_score:.2f})")
    
    # Get alternatives (top 3 excluding best)
    alternatives = [
        (m[0]["case_name"], round(m[1], 2))
        for m in scored_matches[1:4]
        if m[1] > 0.1
    ]
    
    # Determine confidence (slightly lower than raw score for safety)
    confidence = min(0.95, best_score)
    
    # Determine match method based on score
    if best_score >= 0.7:
        match_method = "token_overlap"
    elif best_score >= 0.4:
        match_method = "partial"
    else:
        match_method = "fallback"
    
    return _create_result(
        case_description=case_description,
        case=best_case,
        confidence=confidence,
        match_method=match_method,
        matched_keywords=matched_kw,
        alternatives=alternatives
    )


def _create_result(
    case_description: str,
    case: Dict,
    confidence: float,
    match_method: str,
    matched_keywords: List[str],
    alternatives: List[Tuple[str, float]],
) -> TriageResult:
    """Helper to create TriageResult from case data."""
    return TriageResult(
        case_name=case_description,
        case_name_matched=case.get("case_name", "Unknown"),
        category=case.get("category", "Other"),
        severity=case.get("severity", "High"),
        severity_level=case.get("severity_level", 2),
        harm_threshold_min=case.get("harm_threshold_min", 30),
        harm_threshold_max=case.get("harm_threshold_max", 30),
        harm_threshold_raw=case.get("harm_threshold_raw", ""),
        confidence=round(confidence, 2),
        match_method=match_method,
        matched_keywords=matched_keywords,
        intervention=case.get("intervention", ""),
        equipment=case.get("equipment", ""),
        ctas=case.get("ctas", 2),
        alternatives=alternatives,
    )


def categorize_by_case_name(
    case_name: str,
    categorizer_data: List[Dict],
) -> Optional[TriageResult]:
    """
    Find a case by case name only (no additional symptoms).
    
    Convenience wrapper around categorize() for backward compatibility.
    
    Args:
        case_name: Emergency case name to match
        categorizer_data: Categorizer database
    
    Returns:
        TriageResult or None
    """
    return categorize(case_name, [], categorizer_data)


def get_all_matches(
    query: str,
    categorizer_data: List[Dict],
    top_n: int = 5,
) -> List[Tuple[Dict, float]]:
    """
    Get top N matches for a query, useful for UI disambiguation.
    
    Args:
        query: Search query
        categorizer_data: Categorizer database
        top_n: Number of results to return
    
    Returns:
        List of (case_dict, score) tuples sorted by score
    
    Examples:
        >>> data = load_categorizer()
        >>> matches = get_all_matches("heart", data, top_n=3)
        >>> len(matches) <= 3
        True
    """
    if not categorizer_data or not query:
        return []
    
    query_tokens = _tokenize(query)
    query_normalized = normalize_case_name(query)
    
    scored = []
    for case in categorizer_data:
        case_text = f"{case.get('case_name', '')} {case.get('description', '')}"
        case_tokens = _tokenize(case_text)
        
        # Calculate score
        score = _token_overlap_score(query_tokens, case_tokens)
        
        # Exact match bonus
        if query_normalized == case.get("case_name_normalized", ""):
            score = 1.0
        elif query_normalized in case.get("case_name_normalized", ""):
            score += 0.3
        
        # Critical keyword bonus
        score += _keyword_bonus(query_tokens, case_tokens)
        
        # Clamp to [0, 1]
        score = min(1.0, score)
        
        scored.append((case, score))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    
    return scored[:top_n]


def get_severity_label(severity_level: int) -> str:
    """
    Convert numeric severity level to human-readable label.
    
    Args:
        severity_level: Integer 0-3
    
    Returns:
        Severity label string
    
    Examples:
        >>> get_severity_label(3)
        'Critical'
        >>> get_severity_label(0)
        'Insufficient Info'
    """
    labels = {
        0: "Insufficient Info",
        1: "Medium",
        2: "High",
        3: "Critical",
    }
    return labels.get(severity_level, "Unknown")


def get_cases_by_category(
    category: str,
    categorizer_data: List[Dict],
) -> List[Dict]:
    """
    Get all cases for a specific medical category.
    
    Args:
        category: Medical category (e.g., "Cardiac", "Respiratory")
        categorizer_data: Categorizer database
    
    Returns:
        List of matching cases
    """
    return [
        case for case in categorizer_data
        if case.get("category", "").lower() == category.lower()
    ]


def get_cases_by_severity(
    severity_level: int,
    categorizer_data: List[Dict],
) -> List[Dict]:
    """
    Get all cases for a specific severity level.
    
    Args:
        severity_level: Numeric severity 0-3
        categorizer_data: Categorizer database
    
    Returns:
        List of matching cases
    """
    return [
        case for case in categorizer_data
        if case.get("severity_level", 2) == severity_level
    ]


# =============================================================================
# TESTING & VALIDATION
# =============================================================================

if __name__ == "__main__":
    from data_loader import load_categorizer
    
    print("=" * 80)
    print("CATEGORIZER ENGINE TEST SUITE")
    print("=" * 80)
    
    try:
        data = load_categorizer()
        print(f"\n✓ Loaded {len(data)} medical cases from Catergorizer.json")
        
        # Count by category
        categories = {}
        for case in data:
            cat = case.get("category", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\nCategories:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count} cases")
        
        print("\n" + "=" * 80)
        print("MATCHING TESTS")
        print("=" * 80)
        
        # Test cases from actual data files
        test_cases = [
            # From scenarios.json
            ("Cardiac Arrest", [], 1.0, "exact"),
            ("Severe Anaphylaxis", [], 0.9, "token_overlap"),
            ("COPD Exacerbation", [], 1.0, "exact"),
            
            # From cases_send_decision.json
            ("Loss of vision + confusion", [], 0.4, "partial"),
            ("Asthma attack collapse", [], 0.7, "token_overlap"),
            ("Stroke-like sudden paralysis", [], 0.6, "partial"),
            
            # Edge cases
            ("heart stopped", [], 0.5, "partial"),
            ("can't breathe", [], 0.4, "partial"),
        ]
        
        passed = 0
        failed = 0
        
        for query, symptoms, expected_conf, expected_method in test_cases:
            print(f"\nQuery: '{query}'")
            result = categorize(query, symptoms, data)
            
            if result:
                print(f"  ✓ Matched: '{result.case_name_matched}'")
                print(f"  Method: {result.match_method} (expected: {expected_method})")
                print(f"  Confidence: {result.confidence:.0%} (expected: ~{expected_conf:.0%})")
                print(f"  Category: {result.category}, Severity: {result.severity}")
                print(f"  Harm: {result.harm_threshold_min}-{result.harm_threshold_max} min")
                print(f"  Keywords: {result.matched_keywords}")
                
                if result.alternatives:
                    print(f"  Alternatives: {result.alternatives[:2]}")
                
                # Check if confidence is reasonable
                if result.confidence >= expected_conf * 0.7:
                    passed += 1
                else:
                    failed += 1
                    print(f"  ⚠ Confidence lower than expected")
            else:
                print(f"  ✗ No match found")
                failed += 1
        
        print("\n" + "=" * 80)
        print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
        print("=" * 80)
        
        # Test multi-match function
        print("\n" + "=" * 80)
        print("TOP MATCHES TEST")
        print("=" * 80)
        
        test_query = "heart problems"
        print(f"\nQuery: '{test_query}'")
        matches = get_all_matches(test_query, data, top_n=5)
        print(f"Top {len(matches)} matches:")
        for i, (case, score) in enumerate(matches, 1):
            print(f"  {i}. {case['case_name']} (score: {score:.2f})")
        
        print("\n" + "=" * 80)
        print("✓ ALL TESTS COMPLETED")
        print("=" * 80)
        
    except FileNotFoundError as e:
        print(f"\n✗ FILE ERROR: {e}")
        print("Ensure Catergorizer.json is in /Files directory")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()