from dealhunter.identity.normalization import extract_signature, is_hard_reject, parse_package

def check_invariant(n1, q1, u1, n2, q2, u2, should_reject, reason):
    s1 = extract_signature("", n1, q1, u1)
    s2 = extract_signature("", n2, q2, u2)
    rej, r = is_hard_reject(s1, s2)
    assert rej == should_reject, f"Failed: {n1} vs {n2}. Expected reject={should_reject}, got {rej} ({r})"

# 2 x 600 ml != single 1.2 L
check_invariant("2 x 600 ml", None, None, "1.2 L", 1.2, "L", True, "Count mismatch")

# 1 L != 12 x 1 L
check_invariant("1 L", 1, "L", "12 x 1 L", None, None, True, "Count mismatch")

# 600 ml != 24 x 600 ml
check_invariant("600 ml", 600, "ml", "24 x 600 ml", None, None, True, "Count mismatch")

# 950 g != 1 kg
check_invariant("950 g", 950, "g", "1 kg", 1, "kg", True, "Total quantity mismatch")

print("All invariants passed.")
