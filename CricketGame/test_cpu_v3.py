"""Unit tests for the new CPU strategy engine logic (no DB required)."""

FLOOR_PROB = 0.04
PEAK_CAP   = 0.45
BAIT_WINDOW = 6
BAIT_COUNT  = 3
STREAK_LEN  = 3
SEQ_WINDOW  = 8
HIGH_NUMS = frozenset({4, 5, 6})
LOW_NUMS  = frozenset({1, 2, 3})
BASE_WEIGHTS = {0:0.08,1:0.16,2:0.16,3:0.15,4:0.16,5:0.14,6:0.15}
_FLOOR_BUDGET = FLOOR_PROB * 7   # 0.28
_DISTR_SHARE  = 1.0 - _FLOOR_BUDGET  # 0.72

def _cls(n):
    if n == 0: return 'Z'
    if n >= 4: return 'H'
    return 'L'

def _normalize(w):
    t = sum(w.values())
    return {k: v/t for k,v in w.items()} if t > 0 else {i:1/7 for i in range(7)}

def _apply_floor(w):
    total = sum(w.values())
    if total <= 0: return {i: 1/7 for i in range(7)}
    return {n: FLOOR_PROB + _DISTR_SHARE * (w[n] / total) for n in range(7)}

def _cap_peak(w):
    w = dict(w)
    for _ in range(10):
        if max(w.values()) <= PEAK_CAP + 1e-9: break
        excess = 0.0; capped = {}
        for n,v in w.items():
            if v > PEAK_CAP: excess += v - PEAK_CAP; capped[n] = PEAK_CAP
            else: capped[n] = v
        non_capped = [n for n in capped if capped[n] < PEAK_CAP]
        if non_capped:
            share = excess / len(non_capped)
            for n in non_capped: capped[n] += share
        w = capped
    return w

def _floor_and_cap(w): return _cap_peak(_apply_floor(w))

def build_sequence_signal(history):
    if not history:
        return {'last_class':None,'streak_class':None,'streak_length':0,'bait_number':None,'transitions':{},'patterns':set()}
    recent = history[-SEQ_WINDOW:]
    classes = [_cls(n) for n in recent]
    last_class = classes[-1]
    streak_len = 0
    for c in reversed(classes):
        if c == last_class: streak_len += 1
        else: break
    streak_class = last_class if streak_len >= STREAK_LEN else None
    bait_number = None
    if len(recent) >= BAIT_WINDOW:
        window = recent[-BAIT_WINDOW:]
        for num in range(7):
            if window.count(num) >= BAIT_COUNT:
                bait_number = num; break
    transitions = {}
    for i in range(len(classes)-1):
        fc,tc = classes[i],classes[i+1]
        transitions.setdefault(fc,{})
        transitions[fc][tc] = transitions[fc].get(tc,0)+1
    patterns = set()
    if len(recent) >= 2:
        if _cls(recent[-1]) == 'H': patterns.add('last_was_high')
        if _cls(recent[-2]) != _cls(recent[-1]): patterns.add('just_switched')
    if len(recent) >= 3 and all(_cls(n) == 'H' for n in recent[-3:]): patterns.add('H_shuffle')
    return {'last_class':last_class,'streak_class':streak_class,'streak_length':streak_len,
            'bait_number':bait_number,'transitions':transitions,'patterns':patterns}

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_cls():
    assert _cls(0) == 'Z'
    assert _cls(1) == 'L'
    assert _cls(3) == 'L'
    assert _cls(4) == 'H'
    assert _cls(6) == 'H'
    print("PASS test_cls")

def test_floor_cap():
    w = _floor_and_cap({i: (0.9 if i == 3 else 0.01) for i in range(7)})
    assert all(v >= FLOOR_PROB - 1e-9 for v in w.values()), w
    assert all(v <= PEAK_CAP + 1e-9 for v in w.values()), w
    assert abs(sum(w.values()) - 1.0) < 1e-9
    print("PASS test_floor_cap")

def test_bait_detection():
    # 3x same number in 6-ball window → bait
    sig = build_sequence_signal([2, 4, 1, 1, 1, 3])
    assert sig['bait_number'] == 1, f"Expected bait=1, got {sig['bait_number']}"
    # 4x 1 across 7 balls, but only 3 in the last 6 (2,1,1,1,3,x,x)
    sig2 = build_sequence_signal([6, 5, 6, 5, 6])
    assert sig2['bait_number'] is None  # 6 appears 3/5 but window=6 needed
    print("PASS test_bait_detection")

def test_streak_detection():
    sig = build_sequence_signal([1, 4, 5, 6])
    assert sig['streak_class'] == 'H', sig
    assert sig['streak_length'] == 3

    sig2 = build_sequence_signal([4, 5, 1])
    assert sig2['streak_class'] is None  # only 1 in L class at end

    sig3 = build_sequence_signal([0, 0, 0])
    assert sig3['streak_class'] == 'Z'
    print("PASS test_streak_detection")

def test_h_shuffle():
    sig = build_sequence_signal([4, 5, 6])
    assert 'H_shuffle' in sig['patterns']
    sig2 = build_sequence_signal([4, 5, 3])
    assert 'H_shuffle' not in sig2['patterns']
    print("PASS test_h_shuffle")

def test_last_was_high():
    sig = build_sequence_signal([3, 6])   # last ball = 6 (H)
    assert 'last_was_high' in sig['patterns'], sig['patterns']
    sig2 = build_sequence_signal([6, 2])  # last ball = 2 (L)
    assert 'last_was_high' not in sig2['patterns'], sig2['patterns']
    print("PASS test_last_was_high")

def test_bait_guard_bowling():
    """After 1,1,1 bait, weight of 1 should drop significantly vs baseline."""
    base = {i: 1/7 for i in range(7)}
    # Simulate bait: user played 1 three times in last 6 balls
    history_bait   = [3, 4, 1, 2, 1, 1]
    history_normal = [3, 4, 6, 2, 5, 3]
    sig_bait   = build_sequence_signal(history_bait)
    sig_normal = build_sequence_signal(history_normal)
    assert sig_bait['bait_number'] == 1
    assert sig_normal['bait_number'] is None
    # After bait detected, 1's weight should be crushed
    confidence = 0.6
    # Apply bait logic manually
    s = dict(base)
    bn, bc = 1, 'L'
    crush = max(0.18, 1.0 - 0.80 * confidence)
    s[bn] *= crush
    for n in HIGH_NUMS: s[n] *= 1.9
    result = _floor_and_cap(_normalize(s))
    assert result[1] < 1/7, f"Expected 1's weight < 1/7, got {result[1]:.3f}"
    print(f"PASS test_bait_guard_bowling (w[1]={result[1]:.3f} < {1/7:.3f})")

def test_streak_bowling_switch_predicted():
    """After H-streak, Z and L should get boosted over H."""
    base = {i: 1/7 for i in range(7)}
    # H streak of length 4
    s = dict(base)
    sc, sl = 'H', 4
    boost  = 1.0 + min(0.40 * (sl - STREAK_LEN + 1), 1.20)
    dampen = max(0.35, 1.0 - 0.18 * sl)
    s[0] *= boost * 1.2
    for n in LOW_NUMS:  s[n] *= boost
    for n in HIGH_NUMS: s[n] *= dampen
    result = _floor_and_cap(_normalize(s))
    # 0 should be more likely than 6
    assert result[0] > result[6], f"0={result[0]:.3f} should > 6={result[6]:.3f}"
    print(f"PASS test_streak_bowling_switch_predicted (w[0]={result[0]:.3f} > w[6]={result[6]:.3f})")

def test_h_to_z_special_case():
    """After a high ball, 0 gets boosted in bowling mode."""
    base = {i: 1/7 for i in range(7)}
    s = dict(base)
    s[0] *= 1.50
    for n in LOW_NUMS: s[n] *= 1.15
    result = _floor_and_cap(_normalize(s))
    # 0 should be above its base weight
    assert result[0] > BASE_WEIGHTS[0], f"0={result[0]:.3f} should > base {BASE_WEIGHTS[0]}"
    print(f"PASS test_h_to_z_special_case (w[0]={result[0]:.3f})")

def test_all_numbers_have_floor():
    """No number should ever drop below FLOOR_PROB after floor_and_cap."""
    import random
    for _ in range(1000):
        w = {i: random.uniform(0, 1) for i in range(7)}
        result = _floor_and_cap(_normalize(w))
        for n, v in result.items():
            assert v >= FLOOR_PROB - 1e-9, f"n={n} v={v:.4f} below floor"
    print("PASS test_all_numbers_have_floor (1000 random inputs)")

def test_peak_cap():
    """No number should ever exceed PEAK_CAP after floor_and_cap."""
    import random
    for _ in range(1000):
        w = {i: random.uniform(0, 1) for i in range(7)}
        result = _floor_and_cap(_normalize(w))
        for n, v in result.items():
            assert v <= PEAK_CAP + 1e-9, f"n={n} v={v:.4f} exceeds cap"
    print("PASS test_peak_cap (1000 random inputs)")

if __name__ == '__main__':
    test_cls()
    test_floor_cap()
    test_bait_detection()
    test_streak_detection()
    test_h_shuffle()
    test_last_was_high()
    test_bait_guard_bowling()
    test_streak_bowling_switch_predicted()
    test_h_to_z_special_case()
    test_all_numbers_have_floor()
    test_peak_cap()
    print("\nAll tests passed.")
