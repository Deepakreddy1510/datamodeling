import re
from difflib import SequenceMatcher


def tokens(text):
    raw = re.findall(r"[A-Za-z0-9]+", str(text or "").lower().replace("_", " "))
    return {singular(t) for t in raw if t and t not in {"data", "list", "values", "reference", "refs"}}


def singular(token):
    if token.endswith("ies") and len(token) > 3:
        return token[:-3] + "y"
    if token.endswith("ses") and len(token) > 3:
        return token[:-2]
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


ROLE_TOKENS = {
    "status": {"status", "state"},
    "category": {"category", "segment", "class"},
    "type": {"type", "kind"},
    "method": {"method", "mode", "channel"},
    "role": {"role"},
    "position": {"position"},
    "priority": {"priority", "severity"},
    "country": {"country"},
    "nationality": {"nationality"},
}


class ReferenceDataResolver:
    def __init__(self, business_input=None):
        self.reference_data = (business_input or {}).get("reference_data") or {}
        self.entries = []
        for key, values in self.reference_data.items():
            if isinstance(values, (list, tuple)) and values:
                self.entries.append((key, list(values), tokens(key)))

    def resolve(self, table_name, column_name, semantic_role=None):
        if not self.entries:
            return None, None
        column_tokens = tokens(column_name)
        table_tokens = tokens(table_name)
        role_tokens = ROLE_TOKENS.get(semantic_role or "", {semantic_role} if semantic_role else set())
        best = (0.0, None, None)
        for key, values, key_tokens in self.entries:
            overlap = len(column_tokens & key_tokens) * 3 + len(table_tokens & key_tokens) + len(role_tokens & key_tokens) * 2
            if semantic_role in {"status", "category", "type", "method", "role", "position"} and column_tokens & key_tokens:
                overlap += 2
            ratio = max(SequenceMatcher(None, column_name.lower(), key.lower()).ratio(), 0)
            score = overlap + ratio
            # A role-only match is useful when the reference key contains contextual table tokens.
            if role_tokens & key_tokens and table_tokens & key_tokens:
                score += 2
            if score > best[0]:
                best = (score, key, values)
        if best[1] and best[0] >= 2.4:
            return best[2], best[1]
        return None, None
