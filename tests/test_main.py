"""Tests for QuantumSecretSharing-Lab: Shamir, qutrit (2,3), GHZ, gates."""
import json
import math

import main


# ---------------------------------------------------------------- Shamir
def test_coefficients_deterministic_and_in_field():
    a = main.shamir_coefficients(42, 3, 257)
    b = main.shamir_coefficients(42, 3, 257)
    assert a == b and len(a) == 2 and all(1 <= v < 257 for v in a)


def test_shares_match_labelled_demo_values():
    shares = main.shamir_shares(42, 3, 5, 257)
    assert shares == [(1, 135), (2, 170), (3, 147), (4, 66), (5, 184)]


def test_every_subset_reconstructs():
    shares = main.shamir_shares(42, 3, 5, 257)
    subsets = main._combinations(shares, 3)
    assert len(subsets) == 10
    for sub in subsets:
        assert main.lagrange_at_zero(list(sub), 257) == 42


def test_reconstruction_other_secret_and_params():
    shares = main.shamir_shares(200, 4, 6, 257)
    for sub in main._combinations(shares, 4):
        assert main.lagrange_at_zero(list(sub), 257) == 200


def test_census_k2_flat():
    held = main.shamir_shares(7, 2, 3, 13)[:1]
    tally = main.shamir_census(2, held, 13)
    assert sum(tally.values()) == 13
    assert all(v == 1 for v in tally.values())


def test_census_k3_flat():
    held = main.shamir_shares(7, 3, 5, 13)[:2]
    tally = main.shamir_census(3, held, 13)
    assert sum(tally.values()) == 13
    assert all(v == 1 for v in tally.values())


# ---------------------------------------------------------------- Qutrit
def test_qutrit_single_share_is_population_diag():
    for secret in main.QUTRIT_SECRETS:
        psi = main.qutrit_encode(secret)
        expected = [[0j] * 3 for _ in range(3)]
        for j in range(3):
            expected[j][j] = abs(secret[j]) ** 2
        for party in range(3):
            rho = main.qutrit_single_share(psi, party)
            assert main.mat_max_dev(rho, expected) < 1e-12


def test_qutrit_phase_blindness():
    phased = main.QUTRIT_SECRETS[2]
    stripped = tuple(abs(a) for a in phased)
    for party in range(3):
        dev = main.mat_max_dev(
            main.qutrit_single_share(main.qutrit_encode(phased), party),
            main.qutrit_single_share(main.qutrit_encode(stripped), party))
        assert dev < 1e-12


def test_qutrit_decode_recovers_grid_both_controls():
    for secret in main.QUTRIT_SECRETS:
        psi = main.qutrit_encode(secret)
        for control in (0, 1, 2):
            rec = main.qutrit_recovered(main.qutrit_decode(psi, control),
                                         control)
            assert max(abs(r - s) for r, s in zip(rec, secret)) < 1e-12


def test_qutrit_decoded_other_shares_are_ground():
    secret = main.QUTRIT_SECRETS[3]
    decoded = main.qutrit_decode(main.qutrit_encode(secret), control=0)
    ground = [[0j] * 3 for _ in range(3)]
    ground[0][0] = 1.0
    for party in (1, 2):
        rho = main.partial_trace(decoded, (3, 3, 3), (party,))
        assert main.mat_max_dev(rho, ground) < 1e-12


# ---------------------------------------------------------------- No-cloning
def test_candidate1_leaks_amplitude_hides_phase():
    rep = main.nocloning_report()["candidate_1_computational"]
    assert abs(rep["amplitude_leak_distance_zero_vs_plus"] - 0.5) < 1e-12
    assert rep["phase_leak_distance_plus_vs_minus"] < 1e-12
    cross = main.cross_term_a(main.CANDIDATE_1)
    assert max(abs(v) for row in cross for v in row) < 1e-12


def test_candidate2_hides_amplitude_leaks_phase():
    rep = main.nocloning_report()["candidate_2_bell"]
    assert rep["basis_blindness_zero_vs_one"] < 1e-12
    assert abs(rep["phase_leak_distance_plus_vs_minus"] - 1.0) < 1e-12
    x_over_2 = [[0j, 0.5 + 0j], [0.5 + 0j, 0j]]
    assert main.mat_max_dev(main.cross_term_a(main.CANDIDATE_2),
                            x_over_2) < 1e-12


def test_both_candidates_are_isometries():
    rep = main.nocloning_report()
    for cand in rep.values():
        assert cand["norms"] == [1.0, 1.0]
        assert cand["overlap_abs"] < 1e-12


# ---------------------------------------------------------------- GHZ
def test_ghz_parity_carries_bit():
    exp = main.ghz_report()["expectations"]
    assert exp["XXX"]["ghz_bit0"] == 1.0
    assert exp["XXX"]["ghz_bit1"] == -1.0
    for name in main.AUDIT_PRODUCTS:
        assert exp[name]["ghz_bit0"] == -1.0
    assert abs(exp["ZZZ"]["ghz_bit0"]) < 1e-12


def test_ghz_single_party_is_coin_flip():
    rep = main.ghz_report()
    assert abs(rep["single_party_x_outcome_plus_probability"] - 0.5) < 1e-12


def test_ghz_cheater_passes_half_and_detection_table():
    rep = main.ghz_report()
    for v in rep["cheater_product_state_pass_probability_per_audit"].values():
        assert abs(v - 0.5) < 1e-12
    for v in rep["honest_state_fail_probability_per_audit"].values():
        assert abs(v) < 1e-12
    det = rep["detection_probability_after_m_audits"]
    assert det[1] == 0.5 and det[10] == 0.9990234375


# ---------------------------------------------------------------- Classifier
def test_classifier_scenarios():
    rep = main.classifier_report()
    assert rep["qutrit_two_shares_clean"] == "reconstructable"
    assert rep["qutrit_one_share"] == "phase-blind-share"
    assert rep["shamir_one_share"] == "phase-blind-share"
    assert rep["bell_candidate_one_share"] == "locked-below-threshold"
    assert rep["ghz_cheater_audit"] == "cheater-exposed"
    assert rep["no_shares"] == "locked-below-threshold"


def test_classifier_matches_policy_on_grid():
    for features, label in main.TRAINING_GRID:
        assert main.classify_access(*features) == label
        assert main.model_label(*features) == label


# ---------------------------------------------------------------- Gates/seats
def test_hold_gates():
    assert len(main.HOLD_GATES) == 14
    assert main.gate("real_secret_storage") == "HOLD"
    assert main.gate("qkd_product_claim") == "HOLD"
    assert main.gate("unbreakable_claim") == "HOLD"
    assert main.gate("key_custody_service") == "HOLD"
    assert main.gate("run_simulation") == "PROCEED"


def test_seats_never_override():
    brains = main.brains_report()
    assert brains["decider"]["can_override_hold"] is False
    assert brains["decider"]["seat"] == "Gemini Argon 4 Extended Thinking"
    assert brains["advisor"]["can_override_hold"] is False
    assert brains["flow"]["rendered"] is False and brains["flow"]["live"] == 0


def test_checks_all_pass():
    checks = main.run_checks()
    assert all(ok for _, ok in checks)
    assert len(checks) == 45


# ---------------------------------------------------------------- CLI
def test_cli_exit_codes():
    assert main.main(["checks"]) == 0
    assert main.main(["demo"]) == 0
    assert main.main(["hold-demo"]) == 2
    assert main.main(["hold-demo", "qkd_product_claim"]) == 2
    assert main.main(["hold-demo", "run_simulation"]) == 0


def test_cli_topic_commands_emit_json(capsys):
    for cmd in ("shamir", "qutrit", "ghz", "access", "classify", "brains"):
        assert main.main([cmd]) == 0
        out = capsys.readouterr().out
        json.loads(out)
    assert main.main(["nocloning"]) == 0
    capsys.readouterr()


def test_demo_is_deterministic(capsys):
    main.main(["demo"])
    first = capsys.readouterr().out
    main.main(["demo"])
    second = capsys.readouterr().out
    assert first == second
    assert "CHECKS 45/45" in first
