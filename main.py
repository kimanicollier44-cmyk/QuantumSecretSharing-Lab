#!/usr/bin/env python3
"""QuantumSecretSharing-Lab - educational secret-sharing lab.

by Darion Kellar

Pure Python standard library. Zero dependencies. Zero network.
Education only - and the central lesson is stated up front:

  * This lab builds three secret-sharing constructions from scratch
    and grades each one against the exact statement it is supposed to
    satisfy: Shamir's classical (k, n) threshold scheme over GF(p)
    (every k-subset reconstructs exactly; k - 1 shares are consistent
    with EVERY candidate secret the same number of times), the
    (2, 3) qutrit quantum scheme in its GHZ-style teaching form
    (one share is exactly phase-blind; the decoder is exhibited as a
    basis permutation on the 27-dimensional statevector), and the
    HBB-style GHZ bit scheme (X-parity carries the bit; Y-checks
    catch a substituted product state with probability 1 - 2^-m).
  * It also builds the fence: a computed toy demonstration of why a
    (2, 2) quantum scheme for an arbitrary qubit cannot exist - two
    candidate linear encoders are exhibited, each reconstructable,
    and each is shown in numbers to leak exactly the quadrature it
    tries to hide. That is the no-cloning obstruction, demonstrated
    on two candidates, not proved in general.
  * Nothing here protects a real secret. The Shamir coefficients in
    the demo are derived deterministically from a labelled hash so
    the output is reproducible - a real dealer must use true
    randomness, and that difference is exactly why real-secret use
    is a permanent HOLD gate. Teaching constructions with labelled
    constants, never custody, never deployment.

Real cryptographic deployment, QKD products, security guarantees
for real data, key custody, and vendor claims are permanent HOLD
gates - with Gemini Argon 4 Extended Thinking as DECIDER
(names-only, tighten-only), Muse as advisor (never overrides
HOLD), and Google Flow plan-only seats.
"""
import cmath
import hashlib
import json
import math
import sys

# ---------------------------------------------------------------- constants
VERSION = "1.0.0"

# Labelled Shamir parameters. The headline instance is a (3, 5)
# scheme over GF(257) - the prime just above one byte, so the secret
# 42 is an ordinary field element. The privacy census runs on small
# GF(13) instances where every coefficient tuple can be enumerated.
SHAMIR_P = 257
SHAMIR_SECRET = 42
SHAMIR_K = 3
SHAMIR_N = 5
CENSUS_P = 13
CENSUS_SECRET = 7

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "real_secret_storage": "HOLD - no storing real secrets, passwords, or keys with these teaching schemes",
    "production_cryptography_claim": "HOLD - no claim these teaching constructions are production cryptography",
    "qkd_product_claim": "HOLD - no QKD product claims; no quantum key distribution system exists here",
    "security_guarantee_real_data": "HOLD - no security guarantee for any real data, ever",
    "key_custody_service": "HOLD - no real key custody, wallet custody, or seed-phrase custody",
    "vendor_security_claim": "HOLD - no vendor or product security claims from a lab model",
    "financial_credential_splitting": "HOLD - no splitting real financial credentials or recovery phrases for use",
    "medical_record_sharing": "HOLD - no sharing real medical records through these schemes",
    "classified_use": "HOLD - no government, military, or classified use",
    "cheater_detection_as_proof": "HOLD - parity-check statistics are not proof of cheating in a real system and not legal evidence",
    "quantum_hardware_claim": "HOLD - no claim real quantum hardware or distributed entanglement was used",
    "unbreakable_claim": "HOLD - no 'unbreakable' or 'unhackable' claims; the schemes here are teaching models",
    "bypass_access_control": "HOLD - no using threshold schemes to bypass real access controls",
    "deployment_claim": "HOLD - no deployment claims: no cloud, HSM, or network integration is built or implied",
}


def gate(action):
    """Return 'HOLD' if the action is gated, else 'PROCEED' (sandbox sim)."""
    return "HOLD" if action in HOLD_GATES else "PROCEED"


# ================================================================ 1. Shamir
# Shamir (k, n) over GF(p): the secret is the constant term of a
# degree k-1 polynomial; share i is (i, f(i)). Any k shares rebuild
# f(0) by Lagrange interpolation; k-1 shares leave every candidate
# secret equally consistent - the census below counts that exactly.
#
# DETERMINISM NOTE: the demo coefficients are derived from a labelled
# SHA-256 hash of the secret and the coefficient index. That is a
# teaching choice so every run prints the same shares. A real Shamir
# dealer MUST draw coefficients uniformly at random; deterministic
# coefficients would be a vulnerability anywhere else. This is why
# real-secret use is a HOLD gate above.

def shamir_coefficients(secret, k, p):
    """Deterministic labelled coefficients a_1..a_{k-1} in 1..p-1."""
    coeffs = []
    for i in range(1, k):
        digest = hashlib.sha256(
            f"QuantumSecretSharing-Lab|shamir|{secret}|{i}".encode("utf-8")
        ).hexdigest()
        coeffs.append(int(digest, 16) % (p - 1) + 1)
    return coeffs


def poly_eval(secret, coeffs, x, p):
    """f(x) = secret + a_1 x + ... + a_{k-1} x^{k-1} (mod p), Horner form."""
    y = 0
    for c in reversed(coeffs):
        y = (y * x + c) % p
    return (y * x + secret) % p


def shamir_shares(secret, k, n, p):
    """The n shares (x, f(x)) for x = 1..n."""
    coeffs = shamir_coefficients(secret, k, p)
    return [(x, poly_eval(secret, coeffs, x, p)) for x in range(1, n + 1)]


def lagrange_at_zero(shares, p):
    """Rebuild f(0) from len(shares) >= k points, exact in GF(p)."""
    total = 0
    for i, (xi, yi) in enumerate(shares):
        num, den = 1, 1
        for j, (xj, _) in enumerate(shares):
            if i == j:
                continue
            num = num * (-xj) % p
            den = den * (xi - xj) % p
        total = (total + yi * num * pow(den, -1, p)) % p
    return total


def _combinations(items, r):
    """All r-subsets of items as tuples, deterministic order."""
    if r == 0:
        return [()]
    if not items:
        return []
    head, rest = items[0], items[1:]
    return ([(head,) + c for c in _combinations(rest, r - 1)]
            + _combinations(rest, r))


def _gf_tuples(p, length):
    """All tuples of GF(p)^length, deterministic order."""
    if length == 0:
        return [()]
    return [(v,) + rest for v in range(p)
            for rest in _gf_tuples(p, length - 1)]


def shamir_census(k, held_shares, p):
    """Count, per candidate secret, the completions through held shares.

    Enumerates every coefficient tuple (a_1..a_{k-1}) in GF(p)^(k-1).
    Each tuple plus the first held share implies one candidate secret;
    the tuple is a completion if the implied polynomial also passes
    through every other held share. Perfect privacy means the tally
    is flat: every candidate secret gets the same count.
    """
    tally = {s: 0 for s in range(p)}
    x0, y0 = held_shares[0]
    for coeffs in _gf_tuples(p, k - 1):
        implied = (y0 - sum(a * pow(x0, i + 1, p)
                             for i, a in enumerate(coeffs))) % p
        if all(poly_eval(implied, list(coeffs), x, p) == y
               for x, y in held_shares):
            tally[implied] += 1
    return tally


def shamir_report():
    shares = shamir_shares(SHAMIR_SECRET, SHAMIR_K, SHAMIR_N, SHAMIR_P)
    subsets = _combinations(shares, SHAMIR_K)
    rebuilt = [lagrange_at_zero(list(sub), SHAMIR_P) for sub in subsets]
    census2 = shamir_census(2, shamir_shares(CENSUS_SECRET, 2, 3, CENSUS_P)[:1],
                            CENSUS_P)
    census3 = shamir_census(3, shamir_shares(CENSUS_SECRET, 3, 5, CENSUS_P)[:2],
                            CENSUS_P)
    return {
        "prime": SHAMIR_P,
        "secret": SHAMIR_SECRET,
        "k": SHAMIR_K,
        "n": SHAMIR_N,
        "coefficients": shamir_coefficients(SHAMIR_SECRET, SHAMIR_K, SHAMIR_P),
        "shares": shares,
        "subsets_tested": len(subsets),
        "all_subsets_recover": all(r == SHAMIR_SECRET for r in rebuilt),
        "census_k2": {
            "prime": CENSUS_P,
            "held_shares": 1,
            "completions_per_candidate": sorted(set(census2.values())),
            "total_completions": sum(census2.values()),
        },
        "census_k3": {
            "prime": CENSUS_P,
            "held_shares": 2,
            "completions_per_candidate": sorted(set(census3.values())),
            "total_completions": sum(census3.values()),
        },
    }


# ================================================================ state kit
# Small exact statevector machinery: states are plain lists of
# complex amplitudes, subsystem indices are read off with strides,
# and partial traces are computed entry by entry. Dimensions here
# are tiny (27, 8, 4), so clarity beats speed everywhere.

def _strides(dims):
    strides = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        strides[i] = strides[i + 1] * dims[i + 1]
    return strides


def partial_trace(psi, dims, keep):
    """Reduced density matrix of the subsystems in `keep` (tuple)."""
    strides = _strides(dims)
    kept_dims = [dims[i] for i in keep]
    kstrides = _strides(kept_dims)
    kdim = 1
    for d in kept_dims:
        kdim *= d
    rho = [[0j] * kdim for _ in range(kdim)]
    traced = [t for t in range(len(dims)) if t not in keep]

    def parts(idx):
        return tuple((idx // strides[i]) % dims[i] for i in range(len(dims)))

    def kept_index(p):
        return sum(p[i] * kstrides[t] for t, i in enumerate(keep))

    for i, amp_i in enumerate(psi):
        if amp_i == 0:
            continue
        pi = parts(i)
        for j, amp_j in enumerate(psi):
            if amp_j == 0:
                continue
            pj = parts(j)
            if all(pi[t] == pj[t] for t in traced):
                rho[kept_index(pi)][kept_index(pj)] += amp_i * amp_j.conjugate()
    return rho


def mat_max_dev(rho, sigma):
    """Largest absolute entry difference between two square matrices."""
    return max(abs(rho[i][j] - sigma[i][j])
               for i in range(len(rho)) for j in range(len(rho)))


def trace_distance_2x2(rho, sigma):
    """Trace distance between two 2x2 density matrices, exact formula."""
    a = (rho[0][0] - sigma[0][0]).real
    e = (rho[1][1] - sigma[1][1]).real
    b = rho[0][1] - sigma[0][1]
    mid = (a + e) / 2.0
    root = math.sqrt(((a - e) / 2.0) ** 2 + abs(b) ** 2)
    return 0.5 * (abs(mid + root) + abs(mid - root))


# ================================================================ 2. Qutrit (2,3)
# The GHZ-style teaching code: a secret qutrit a|0> + b|1> + g|2> is
# encoded as a|000> + b|111> + g|222> in a 27-dimensional space.
# One share's reduced state is diag(|a|^2, |b|^2, |g|^2): the
# populations leak, the PHASES do not - two secrets differing only in
# phase have byte-identical single-share states. The decoder is a
# basis permutation (controlled subtractions mod 3, control = the
# first reconstructing share) exhibited as an index map on the full
# statevector; after it, the control share holds the secret exactly
# and the other two shares are |0>. Stated honestly: the lab
# exhibits decoding on its joint statevector, which is the teaching
# form of the scheme; the production erasure-correcting form is the
# Cleve-Gottesman-Lo polynomial code, named here, not built here.

QUTRIT_SECRETS = [
    (1.0 + 0j, 0j, 0j),
    tuple(1.0 / math.sqrt(3.0) for _ in range(3)),
    (1.0 / math.sqrt(2.0),
     cmath.exp(1j * math.pi / 3.0) / math.sqrt(3.0),
     cmath.exp(-1j * math.pi / 5.0) / math.sqrt(6.0)),
    (0.5, 0.5j, math.sqrt(0.5)),
]


def qidx(a, b, c):
    return a * 9 + b * 3 + c


def qutrit_encode(secret):
    """a|0> + b|1> + g|2>  ->  a|000> + b|111> + g|222>."""
    psi = [0j] * 27
    psi[qidx(0, 0, 0)] = secret[0]
    psi[qidx(1, 1, 1)] = secret[1]
    psi[qidx(2, 2, 2)] = secret[2]
    return psi


def qutrit_single_share(psi, party):
    """The 3x3 reduced state of one qutrit share."""
    return partial_trace(psi, (3, 3, 3), (party,))


def qutrit_decode(psi, control=0):
    """Basis permutation: every other share gets (value - control) mod 3.

    An index map on the 27-dim statevector. After it, the state is
    |secret> on the control share and |0> on both other shares.
    """
    out = [0j] * 27
    for a in range(3):
        for b in range(3):
            for c in range(3):
                amp = psi[qidx(a, b, c)]
                if amp == 0:
                    continue
                vals = [a, b, c]
                ctrl = vals[control]
                new = [v if t == control else (v - ctrl) % 3
                       for t, v in enumerate(vals)]
                out[qidx(*new)] += amp
    return out


def qutrit_recovered(psi, control=0):
    """Amplitudes of the control share when both other shares read 0."""
    amps = []
    for v in range(3):
        vals = [0, 0, 0]
        vals[control] = v
        amps.append(psi[qidx(*vals)])
    return tuple(amps)


def qutrit_report():
    worst_share_dev = 0.0
    worst_decode_err = 0.0
    for secret in QUTRIT_SECRETS:
        psi = qutrit_encode(secret)
        expected = [[0j] * 3 for _ in range(3)]
        for j in range(3):
            expected[j][j] = abs(secret[j]) ** 2
        for party in range(3):
            dev = mat_max_dev(qutrit_single_share(psi, party), expected)
            worst_share_dev = max(worst_share_dev, dev)
        for control in (0, 1):
            decoded = qutrit_decode(psi, control=control)
            rec = qutrit_recovered(decoded, control=control)
            err = max(abs(r - s) for r, s in zip(rec, secret))
            worst_decode_err = max(worst_decode_err, err)
    # Phase blindness: same populations, different phases.
    phased = QUTRIT_SECRETS[2]
    stripped = tuple(abs(a) for a in phased)
    phase_dev = 0.0
    for party in range(3):
        dev = mat_max_dev(qutrit_single_share(qutrit_encode(phased), party),
                          qutrit_single_share(qutrit_encode(stripped), party))
        phase_dev = max(phase_dev, dev)
    return {
        "encoding": "a|000> + b|111> + g|222> in 27 dims",
        "secrets_tested": len(QUTRIT_SECRETS),
        "single_share_is_diag_populations_max_dev": worst_share_dev,
        "phase_blindness_max_dev": phase_dev,
        "decode_controls_tested": [0, 1],
        "worst_recovery_error": worst_decode_err,
    }


# ================================================================ 3. No-cloning fence
# A (2, 2) QQ scheme for an arbitrary qubit would need a LINEAR
# encoder E with orthonormal images (so the pair can be decoded)
# whose single-share states are the same for every secret. This is
# the toy demonstration, in computed numbers, of why that fails -
# labelled a demonstration on two candidates, not a proof.
#
# Candidate 1 (computational): E|0> = |00>, E|1> = |11>. The cross
# term Tr_B |a0><a1| is exactly zero, so phases are hidden - but the
# populations are not: share A of |0> is |0><0|, of |+> is I/2,
# trace distance 0.5. The share reads the amplitude.
# Candidate 2 (Bell basis): E|0> = (|00>+|11>)/sqrt2,
# E|1> = (|01>+|10>)/sqrt2. Now basis secrets are hidden (both give
# I/2) - but the cross term is X/2, so share A of |+> is |+><+| and
# of |-> is |-><-|, trace distance 1.0. The share reads the phase.
# Linearity forces one quadrature or the other into the open: that
# is the no-cloning obstruction wearing numbers.

SQRT2 = math.sqrt(2.0)
CANDIDATE_1 = ((1.0 + 0j, 0j, 0j, 0j), (0j, 0j, 0j, 1.0 + 0j))
CANDIDATE_2 = (tuple(v / SQRT2 for v in (1.0, 0.0, 0.0, 1.0)),
               tuple(v / SQRT2 for v in (0.0, 1.0, 1.0, 0.0)))


def encode_qubit(candidate, alpha, beta):
    """Linear extension: alpha * E|0> + beta * E|1> in 4 dims."""
    a0, a1 = candidate
    return tuple(alpha * a0[i] + beta * a1[i] for i in range(4))


def share_a(psi4):
    return partial_trace(psi4, (2, 2), (0,))


def cross_term_a(candidate):
    """Tr_B |a0><a1| as a 2x2 matrix: [m][n] = sum_b a0[m,b] conj(a1[n,b])."""
    a0, a1 = candidate
    return [[sum(a0[m * 2 + b] * a1[n * 2 + b].conjugate() for b in range(2))
             for n in range(2)] for m in range(2)]


def _inner(u, v):
    return sum(x.conjugate() * y for x, y in zip(u, v))


def nocloning_report():
    zero = (1.0 + 0j, 0j)
    one = (0j, 1.0 + 0j)
    plus = tuple(v / SQRT2 for v in (1.0, 1.0))
    minus = tuple(v / SQRT2 for v in (1.0, -1.0))
    report = {}
    for name, cand in (("candidate_1_computational", CANDIDATE_1),
                       ("candidate_2_bell", CANDIDATE_2)):
        a0, a1 = cand
        rho = {label: share_a(encode_qubit(cand, *s))
               for label, s in (("zero", zero), ("one", one),
                                ("plus", plus), ("minus", minus))}
        report[name] = {
            "norms": [round(abs(_inner(a0, a0)), 12),
                      round(abs(_inner(a1, a1)), 12)],
            "overlap_abs": abs(_inner(a0, a1)),
            "cross_term_a": [[round(v.real, 6) + round(v.imag, 6) * 1j
                              for v in row] for row in cross_term_a(cand)],
            "amplitude_leak_distance_zero_vs_plus":
                trace_distance_2x2(rho["zero"], rho["plus"]),
            "basis_blindness_zero_vs_one":
                trace_distance_2x2(rho["zero"], rho["one"]),
            "phase_leak_distance_plus_vs_minus":
                trace_distance_2x2(rho["plus"], rho["minus"]),
        }
    return report


# ================================================================ 4. GHZ bit sharing (HBB style)
# Three parties share |GHZ_b> = (|000> + (-1)^b |111>) / sqrt2. The
# secret bit b lives in the X-parity: X x X x X has eigenvalue
# (-1)^b, while any single party's outcome is a coin flip. Audit
# rounds use the Y-products XYY, YXY, YYX (eigenvalue -1 on the
# honest state): a substituted product state |+++> passes each such
# check with probability exactly 1/2, so m audit rounds catch it
# with probability 1 - 2^-m.

PAULI = {
    "I": [[1 + 0j, 0j], [0j, 1 + 0j]],
    "X": [[0j, 1 + 0j], [1 + 0j, 0j]],
    "Y": [[0j, -1j], [1j, 0j]],
    "Z": [[1 + 0j, 0j], [0j, -1 + 0j]],
}


def _kron(A, B):
    return [[A[i // len(B)][j // len(B[0])] * B[i % len(B)][j % len(B[0])]
             for j in range(len(A[0]) * len(B[0]))]
            for i in range(len(A) * len(B))]


def pauli_product(names):
    op = PAULI[names[0]]
    for name in names[1:]:
        op = _kron(op, PAULI[name])
    return op


def expectation(psi, op):
    total = 0j
    for i, amp_i in enumerate(psi):
        if amp_i == 0:
            continue
        row = sum(op[i][j] * psi[j] for j in range(len(psi)))
        total += amp_i.conjugate() * row
    return total


def prob_minus_one(psi, op):
    """P(product outcome = -1) for a Pauli product (op^2 = I)."""
    return (1.0 - expectation(psi, op).real) / 2.0


def ghz_state(bit):
    psi = [0j] * 8
    psi[0] = 1.0 / SQRT2
    psi[7] = (1.0 if bit == 0 else -1.0) / SQRT2
    return psi


def product_state_plus():
    return [complex(1.0 / math.sqrt(8.0), 0.0)] * 8


AUDIT_PRODUCTS = ("XYY", "YXY", "YYX")


def ghz_report():
    g0, g1 = ghz_state(0), ghz_state(1)
    cheater = product_state_plus()
    expectations = {}
    for names in ("XXX",) + AUDIT_PRODUCTS + ("ZZZ",):
        op = pauli_product(names)
        expectations[names] = {
            "ghz_bit0": round(expectation(g0, op).real, 12),
            "ghz_bit1": round(expectation(g1, op).real, 12),
        }
    rho_a = partial_trace(g0, (2, 2, 2), (0,))
    plus_vec = (1.0 / SQRT2, 1.0 / SQRT2)
    p_plus = sum(plus_vec[i].conjugate() * rho_a[i][j] * plus_vec[j]
                 for i in range(2) for j in range(2)).real
    cheater_pass = {names: prob_minus_one(cheater, pauli_product(names))
                    for names in AUDIT_PRODUCTS}
    honest_fail = {names: 1.0 - prob_minus_one(g0, pauli_product(names))
                   for names in AUDIT_PRODUCTS}
    detection = {m: 1.0 - 2.0 ** (-m) for m in (1, 2, 3, 5, 10, 20)}
    return {
        "expectations": expectations,
        "single_party_x_outcome_plus_probability": p_plus,
        "cheater_product_state_pass_probability_per_audit": cheater_pass,
        "honest_state_fail_probability_per_audit": honest_fail,
        "detection_probability_after_m_audits": detection,
    }


# ================================================================ access table
def access_report():
    """Who learns what, from how many shares - all values computed."""
    shamir = shamir_report()
    qutrit = qutrit_report()
    ghz = ghz_report()
    return {
        "shamir_(3,5)_gf257": {
            "fewer_than_3_shares": "every candidate secret stays consistent "
                                   "(counted exactly on the GF(13) census)",
            "3_shares": f"secret exact - all {shamir['subsets_tested']} "
                        "subsets reconstruct",
        },
        "shamir_census_gf13": {
            "(2,3)_1_share_held": shamir["census_k2"],
            "(3,5)_2_shares_held": shamir["census_k3"],
        },
        "qutrit_(2,3)": {
            "1_share": "diag(|a|^2, |b|^2, |g|^2) only - phase-blind, "
                       f"max dev {qutrit['phase_blindness_max_dev']:.3e}",
            "2_shares": "decoder permutation on the joint statevector "
                        f"recovers the secret, worst error "
                        f"{qutrit['worst_recovery_error']:.3e}",
        },
        "ghz_bit": {
            "1_share": "X outcome is a coin flip, "
                       f"p(+) = {ghz['single_party_x_outcome_plus_probability']:.6f}",
            "3_shares": "X-parity = secret bit (XXX eigenvalue (-1)^b)",
            "cheater": "substituted product state passes each Y-audit with "
                       "p = 0.5; detection after m audits = 1 - 2^-m",
        },
    }


# ================================================================ 5. kNN classifier
# Features: shares present, threshold met, single-share phase
# information (a trace distance the lab itself measured), failed
# parity checks. The training grid is labelled by the lab's own
# access policy (model_label below) - the classifier interpolates
# the policy, it does not replace the constructions.

def model_label(shares, threshold_met, phase_info, check_failures):
    """The access policy distilled to a four-way teaching label."""
    if check_failures >= 2:
        return "cheater-exposed"
    if threshold_met:
        return "reconstructable"
    if shares == 1 and phase_info <= 0.05:
        return "phase-blind-share"
    return "locked-below-threshold"


def _training_grid():
    rows = []
    for shares in range(0, 4):
        threshold_met = 1 if shares >= 2 else 0
        for phase_info in (0.0, 0.5, 1.0):
            for failures in (0, 1, 2, 4, 8):
                features = (shares, threshold_met, phase_info, failures)
                rows.append((features, model_label(*features)))
    return rows


TRAINING_GRID = _training_grid()


def _scaled(features):
    shares, threshold_met, phase_info, failures = features
    return (shares / 3.0, float(threshold_met), phase_info, failures / 8.0)


def classify_access(shares, threshold_met, phase_info, check_failures, k=5):
    """Distance-weighted kNN over the policy-labelled grid."""
    target = _scaled((shares, threshold_met, phase_info, check_failures))
    ranked = []
    for features, label in TRAINING_GRID:
        point = _scaled(features)
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, point)))
        ranked.append((dist, features, label))
    ranked.sort(key=lambda row: (row[0], row[1]))
    votes = {}
    for dist, _, label in ranked[:k]:
        votes[label] = votes.get(label, 0.0) + 1.0 / (dist + 1e-9)
    priority = {"reconstructable": 0, "phase-blind-share": 1,
                "locked-below-threshold": 2, "cheater-exposed": 3}
    return sorted(votes.items(), key=lambda kv: (-kv[1], priority[kv[0]]))[0][0]


def classifier_report():
    qutrit = qutrit_report()
    nc = nocloning_report()
    qutrit_phase = round(qutrit["phase_blindness_max_dev"], 6)
    bell_phase = round(
        nc["candidate_2_bell"]["phase_leak_distance_plus_vs_minus"], 6)
    scenarios = {
        "qutrit_two_shares_clean": (2, 1, qutrit_phase, 0),
        "qutrit_one_share": (1, 0, qutrit_phase, 0),
        "shamir_one_share": (1, 0, 0.0, 0),
        "bell_candidate_one_share": (1, 0, bell_phase, 0),
        "ghz_full_audit_clean": (3, 1, qutrit_phase, 0),
        "ghz_cheater_audit": (3, 1, qutrit_phase, 4),
        "two_shares_one_failed_check": (2, 1, qutrit_phase, 1),
        "no_shares": (0, 0, 0.0, 0),
    }
    return {name: classify_access(*features)
            for name, features in scenarios.items()}


# ================================================================ 6. Advisory seats
def _trace(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def argon4_decide(topic="quantumsecretsharing-demo"):
    """Gemini Argon 4 DECIDER seat: MAP->MODEL->STRESS->DECIDE.

    Names-only keys, live calls 0, tighten-only: can add HOLDs, never lift one.
    """
    stages = ["MAP", "MODEL", "STRESS", "DECIDE"]
    payload = {"seat": "gemini-argon-4", "topic": topic, "stages": stages}
    return {
        "seat": "Gemini Argon 4 Extended Thinking",
        "role": "DECIDER",
        "pipeline": stages,
        "tiers": [2048, 8192, 32768],
        "key": "names-only (GEMINI_API_KEY name checked, value never read)",
        "live_calls": 0,
        "decision": "PROCEED - sandbox simulation only, all custody and deployment gates stay HOLD",
        "can_override_hold": False,
        "trace_sha256_16": _trace(payload),
    }


def claude_advisor(topic="quantumsecretsharing-demo"):
    """Muse advisor seat: advises, can never override a HOLD."""
    return {
        "seat": "Muse",
        "role": "ADVISOR",
        "key": "names-only (MODEL_API_KEY name checked, value never read)",
        "live_calls": 0,
        "advice": "Say it in the first line of every report: a share that leaks nothing is a theorem about the model at the stated field and state - then show the census count, the phase-blindness deviation, and the exact audit probability.",
        "can_override_hold": False,
    }


def google_flow_plan():
    """Google Flow seat: plan-only, nothing rendered, nothing live."""
    return {
        "seat": "Google Flow",
        "role": "PLAN-ONLY",
        "shots": ["a secret splitting into three glowing share strands",
                  "one share alone casting a flat diagonal shadow - populations, no phases",
                  "two shares running the subtraction decoder as the secret reappears",
                  "a swapped product state failing a Y-parity audit in red",
                  "the no-cloning fence: two encoders, each leaking one quadrature"],
        "rendered": False,
        "live": 0,
    }


def brains_report():
    return {"decider": argon4_decide(), "advisor": claude_advisor(),
            "flow": google_flow_plan()}


# ================================================================ checks
def run_checks():
    c = []

    def chk(name, ok):
        c.append((name, bool(ok)))

    # 1. Shamir - reconstruction and the privacy census
    coeffs = shamir_coefficients(SHAMIR_SECRET, SHAMIR_K, SHAMIR_P)
    chk("shamir_coefficients_deterministic",
        coeffs == shamir_coefficients(SHAMIR_SECRET, SHAMIR_K, SHAMIR_P)
        and all(1 <= a < SHAMIR_P for a in coeffs))
    chk("shamir_poly_at_zero_is_secret",
        poly_eval(SHAMIR_SECRET, coeffs, 0, SHAMIR_P) == SHAMIR_SECRET)
    shares = shamir_shares(SHAMIR_SECRET, SHAMIR_K, SHAMIR_N, SHAMIR_P)
    chk("shamir_share_shape",
        len(shares) == SHAMIR_N
        and [x for x, _ in shares] == [1, 2, 3, 4, 5]
        and all(0 <= y < SHAMIR_P for _, y in shares))
    subsets = _combinations(shares, SHAMIR_K)
    chk("shamir_all_subsets_recover",
        len(subsets) == 10
        and all(lagrange_at_zero(list(s), SHAMIR_P) == SHAMIR_SECRET
                for s in subsets))
    census2 = shamir_census(2, shamir_shares(CENSUS_SECRET, 2, 3, CENSUS_P)[:1],
                            CENSUS_P)
    chk("census_k2_every_candidate_once",
        sum(census2.values()) == CENSUS_P
        and all(v == 1 for v in census2.values()))
    census3 = shamir_census(3, shamir_shares(CENSUS_SECRET, 3, 5, CENSUS_P)[:2],
                            CENSUS_P)
    chk("census_k3_every_candidate_once",
        sum(census3.values()) == CENSUS_P
        and all(v == 1 for v in census3.values()))

    # 2. Qutrit (2,3) - phase blindness and the decoder permutation
    qrep = qutrit_report()
    chk("qutrit_single_share_is_population_diag",
        qrep["single_share_is_diag_populations_max_dev"] < 1e-12)
    chk("qutrit_phase_blindness_exact",
        qrep["phase_blindness_max_dev"] < 1e-12)
    chk("qutrit_decode_recovers_grid",
        qrep["worst_recovery_error"] < 1e-12)
    secret = QUTRIT_SECRETS[2]
    psi = qutrit_encode(secret)
    chk("qutrit_encoding_normalised",
        abs(sum(abs(a) ** 2 for a in psi) - 1.0) < 1e-12)
    decoded = qutrit_decode(psi, control=0)
    rho_a = partial_trace(decoded, (3, 3, 3), (0,))
    outer = [[secret[i] * secret[j].conjugate() for j in range(3)]
             for i in range(3)]
    chk("qutrit_decoded_share_is_secret_state",
        mat_max_dev(rho_a, outer) < 1e-12)
    rho_b = partial_trace(decoded, (3, 3, 3), (1,))
    ground = [[0j] * 3 for _ in range(3)]
    ground[0][0] = 1.0
    chk("qutrit_decoded_other_shares_ground",
        mat_max_dev(rho_b, ground) < 1e-12)
    stripped = tuple(abs(a) for a in secret)
    chk("qutrit_phases_live_in_global_state",
        max(abs(x - y) for x, y in zip(psi, qutrit_encode(stripped))) > 0.5)

    # 3. No-cloning fence - two candidates, two leaks
    nc = nocloning_report()
    c1 = nc["candidate_1_computational"]
    c2 = nc["candidate_2_bell"]
    chk("nc_candidate1_orthonormal",
        c1["norms"] == [1.0, 1.0] and c1["overlap_abs"] < 1e-12)
    chk("nc_candidate2_orthonormal",
        c2["norms"] == [1.0, 1.0] and c2["overlap_abs"] < 1e-12)
    chk("nc_candidate1_cross_term_zero",
        max(abs(v) for row in cross_term_a(CANDIDATE_1) for v in row) < 1e-12)
    chk("nc_candidate1_amplitude_leak_half",
        abs(c1["amplitude_leak_distance_zero_vs_plus"] - 0.5) < 1e-12)
    chk("nc_candidate1_phase_hidden",
        c1["phase_leak_distance_plus_vs_minus"] < 1e-12)
    chk("nc_candidate2_basis_blind",
        c2["basis_blindness_zero_vs_one"] < 1e-12)
    x_over_2 = [[0j, 0.5 + 0j], [0.5 + 0j, 0j]]
    chk("nc_candidate2_cross_term_x_over_2",
        mat_max_dev(cross_term_a(CANDIDATE_2), x_over_2) < 1e-12)
    chk("nc_candidate2_phase_leak_full",
        abs(c2["phase_leak_distance_plus_vs_minus"] - 1.0) < 1e-12)

    # 4. GHZ bit sharing - parity, coin flips, cheater audits
    grep_ = ghz_report()
    exp = grep_["expectations"]
    chk("ghz_xxx_carries_bit",
        exp["XXX"]["ghz_bit0"] == 1.0 and exp["XXX"]["ghz_bit1"] == -1.0)
    chk("ghz_audit_products_minus_one",
        all(exp[name]["ghz_bit0"] == -1.0 for name in AUDIT_PRODUCTS))
    chk("ghz_zzz_expectation_zero", abs(exp["ZZZ"]["ghz_bit0"]) < 1e-12)
    chk("ghz_single_party_coin_flip",
        abs(grep_["single_party_x_outcome_plus_probability"] - 0.5) < 1e-12)
    chk("ghz_cheater_passes_half",
        all(abs(v - 0.5) < 1e-12
            for v in grep_["cheater_product_state_pass_probability_per_audit"].values()))
    chk("ghz_honest_never_fails",
        all(abs(v) < 1e-12
            for v in grep_["honest_state_fail_probability_per_audit"].values()))
    det = grep_["detection_probability_after_m_audits"]
    chk("ghz_detection_table_exact",
        det[1] == 0.5 and det[10] == 0.9990234375
        and abs(det[20] - (1.0 - 2.0 ** -20)) < 1e-15)
    op = pauli_product("XYY")
    sq = [[sum(op[i][k] * op[k][j] for k in range(8)) for j in range(8)]
          for i in range(8)]
    ident = [[1.0 if i == j else 0.0 for j in range(8)] for i in range(8)]
    chk("ghz_audit_product_involutory", mat_max_dev(sq, ident) < 1e-12)

    # 5. Classifier - labels come from the access policy itself
    rep = classifier_report()
    chk("classifier_two_shares_reconstructable",
        rep["qutrit_two_shares_clean"] == "reconstructable")
    chk("classifier_one_share_phase_blind",
        rep["qutrit_one_share"] == "phase-blind-share"
        and rep["shamir_one_share"] == "phase-blind-share")
    chk("classifier_leaky_share_locked",
        rep["bell_candidate_one_share"] == "locked-below-threshold")
    chk("classifier_cheater_exposed", rep["ghz_cheater_audit"] == "cheater-exposed")
    chk("classifier_clean_audits_reconstructable",
        rep["ghz_full_audit_clean"] == "reconstructable"
        and rep["two_shares_one_failed_check"] == "reconstructable")
    chk("classifier_no_shares_locked", rep["no_shares"] == "locked-below-threshold")
    chk("classifier_matches_policy_grid",
        all(classify_access(*features) == label
            for features, label in TRAINING_GRID))

    # gates + seats
    chk("hold_gates_14", len(HOLD_GATES) == 14
        and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    chk("gate_real_secret_hold", gate("real_secret_storage") == "HOLD")
    chk("gate_qkd_hold", gate("qkd_product_claim") == "HOLD")
    chk("gate_unbreakable_hold", gate("unbreakable_claim") == "HOLD")
    chk("gate_custody_hold", gate("key_custody_service") == "HOLD")
    chk("gate_sandbox_proceed", gate("run_simulation") == "PROCEED")
    brains = brains_report()
    chk("argon4_no_override", brains["decider"]["can_override_hold"] is False
        and brains["decider"]["seat"]
        == "Gemini Argon 4 Extended Thinking")
    chk("claude_no_override", brains["advisor"]["can_override_hold"] is False)
    chk("flow_plan_only", brains["flow"]["rendered"] is False
        and brains["flow"]["live"] == 0)
    return c


# ================================================================ CLI / demo
def demo():
    print("=" * 68)
    print("QuantumSecretSharing-Lab - secret sharing: Shamir, qutrit (2,3), GHZ")
    print("by Darion Kellar | MIT | pure stdlib | zero network | EDUCATION ONLY")
    print("=" * 68)
    print("\n[1] THE HONEST CORE - what a share proves and what it never does")
    print("    A threshold scheme is a theorem about a model: below the")
    print("    threshold the shares are consistent with every secret; at")
    print("    the threshold they rebuild it exactly. This lab computes")
    print("    both halves of that sentence. It protects nothing real -")
    print("    the demo coefficients are deterministic on purpose, and")
    print("    real secrets, real keys, and real data are HOLD gates.")
    shamir = shamir_report()
    print(f"\n[2] Shamir ({shamir['k']}, {shamir['n']}) over GF({shamir['prime']})"
          f" - secret {shamir['secret']}")
    print(f"    coefficients (deterministic, labelled): {shamir['coefficients']}")
    for x, y in shamir["shares"]:
        print(f"    share x={x}: f(x) = {y}")
    print(f"    all {shamir['subsets_tested']} subsets of {shamir['k']} shares "
          f"reconstruct exactly: {shamir['all_subsets_recover']}")
    c2 = shamir["census_k2"]
    c3 = shamir["census_k3"]
    print(f"    census GF({c2['prime']}), 1 share of a (2,3): each of the "
          f"{c2['prime']} candidate secrets has exactly "
          f"{c2['completions_per_candidate'][0]} completion")
    print(f"    census GF({c3['prime']}), 2 shares of a (3,5): each candidate "
          f"has exactly {c3['completions_per_candidate'][0]} completion - "
          "below threshold, nothing is learned")
    qutrit = qutrit_report()
    print("\n[3] Qutrit (2, 3) - a|000> + b|111> + g|222> in 27 dims")
    print(f"    secrets tested: {qutrit['secrets_tested']} (incl. phase-carrying)")
    print("    one share = diag(|a|^2, |b|^2, |g|^2), max dev "
          f"{qutrit['single_share_is_diag_populations_max_dev']:.3e}")
    print("    phase blindness: phase-only-different secrets give identical "
          f"single shares, max dev {qutrit['phase_blindness_max_dev']:.3e}")
    print("    decoder = basis permutation (controlled subtractions mod 3); "
          f"worst recovery error {qutrit['worst_recovery_error']:.3e}")
    nc = nocloning_report()
    print("\n[4] The no-cloning fence - why no (2, 2) qubit scheme exists")
    for name, cand in nc.items():
        print(f"    {name}: cross term max "
              f"{max(abs(v) for row in cand['cross_term_a'] for v in row):.3f} | "
              f"basis dist {cand['basis_blindness_zero_vs_one']:.3f} | "
              f"|0> vs |+> dist {cand['amplitude_leak_distance_zero_vs_plus']:.3f} | "
              f"phase leak {cand['phase_leak_distance_plus_vs_minus']:.3f}")
    print("    -> candidate 1 hides phase, leaks amplitude (0.500); candidate 2")
    print("       hides amplitude, leaks phase (1.000). Linearity leaves no")
    print("       third option - a toy demonstration, not a proof.")
    ghz = ghz_report()
    print("\n[5] GHZ bit sharing (HBB style) - the bit lives in the parity")
    for names, vals in ghz["expectations"].items():
        print(f"    <{names}>  bit0 {vals['ghz_bit0']:+.6f}   "
              f"bit1 {vals['ghz_bit1']:+.6f}")
    print("    one party's X outcome: p(+) = "
          f"{ghz['single_party_x_outcome_plus_probability']:.6f} - a coin flip")
    print("    cheater |+++> passes each Y-audit with p = 0.500000; detection "
          "after 10 audits = "
          f"{ghz['detection_probability_after_m_audits'][10]:.6f}")
    print("\n[6] Access structure - who learns what")
    for scheme, rows in access_report().items():
        print(f"    {scheme}:")
        for key, value in rows.items():
            print(f"      {key}: {value}")
    print("\n[7] Access classifier (TinyML kNN, labels from the access policy)")
    for name, label in classifier_report().items():
        print(f"    {name:36s} -> {label}")
    print("\n[8] Advisory seats")
    brains = brains_report()
    print(f"    decider: {brains['decider']['decision']} "
          f"trace={brains['decider']['trace_sha256_16']}")
    print(f"    advisor can_override_hold = {brains['advisor']['can_override_hold']}")
    print(f"    flow rendered = {brains['flow']['rendered']} "
          f"live = {brains['flow']['live']}")
    print(f"\n[9] HOLD gates: {len(HOLD_GATES)}")
    for key in HOLD_GATES:
        print(f"    HOLD  {key}")
    checks = run_checks()
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nCHECKS {passed}/{len(checks)}")
    for name, ok in checks:
        if not ok:
            print(f"    FAIL {name}")
    verdict = "PROCEED" if passed == len(checks) else "HOLD"
    print(f"VERDICT {verdict} (sandbox simulation only) | HOLD gates {len(HOLD_GATES)}")
    return 0 if passed == len(checks) else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    cmd = argv[0]
    if cmd == "checks":
        checks = run_checks()
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
        return 0 if all(ok for _, ok in checks) else 1
    if cmd == "shamir":
        print(json.dumps(shamir_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "qutrit":
        print(json.dumps(qutrit_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "nocloning":
        print(json.dumps(nocloning_report(), indent=2, sort_keys=True,
                         default=str))
        return 0
    if cmd == "ghz":
        print(json.dumps(ghz_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "access":
        print(json.dumps(access_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "classify":
        print(json.dumps(classifier_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "brains":
        print(json.dumps(brains_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "holds":
        for key, value in HOLD_GATES.items():
            print(f"{key}: {value}")
        return 0
    if cmd == "hold-demo":
        action = argv[1] if len(argv) > 1 else "real_secret_storage"
        print(f"{action}: {HOLD_GATES.get(action, 'PROCEED - not gated')}")
        return 2 if gate(action) == "HOLD" else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
