# preflight_local — tech-b53-t4-store-rating-claim-verification

Verdict: **NEEDS_REVIEW**  (NEEDS_REVIEW 4, NOT_APPLICABLE 14, PASS 25)

| criterion | outcome | evidence |
|---|---|---|
| **layer1_clarity_scope** | NEEDS_REVIEW | interface-vs-method judgement: no auto-signals; review round confirms |
| layer1_clarity_scope__output_surface_contract | PASS | submission_format.md shipped in environment/input/ |
| layer1_clarity_scope__representation_contract | PASS | 3 rendering-tolerant checks (in_array/approx/compound with abs<=1e-3 numeric cells) against 0 exact numeric pins (leading-zero transcription class) |
| layer1_clarity_scope__process_requirement_disclosure | NOT_APPLICABLE | no process requirements in this schema — grading is on delivered files only |
| layer1_clarity_scope__redaction_readability | NOT_APPLICABLE | no redacted fixtures in this schema |
| **layer1_realism_leakage** | NEEDS_REVIEW | judgement children await the review round |
| layer1_realism_leakage__domain_correctness | NEEDS_REVIEW | challenger question: are the domain figures fictional or exactly cited? (the client resolved h564's against PubMed) |
| layer1_realism_leakage__authoritative_reference_validity | NOT_APPLICABLE | no citations in the instruction |
| layer1_realism_leakage__workflow_realism | NEEDS_REVIEW | human judgement: would a professional recognise this ask? |
| layer1_realism_leakage__golden_isolation | PASS | Dockerfile copies input/ only; tests and solution never enter the task image |
| **layer1_package_consistency** | PASS | all applicable children pass |
| layer1_package_consistency__manifest_environment_consistency | NOT_APPLICABLE | no manifest in the harbor-cli layout (P2) |
| layer1_package_consistency__declared_executed_verifier_consistency | PASS | all 14 declared checks executed by the real engine against the shipped gold |
| layer1_package_consistency__cross_artifact_consistency | PASS | requirement table names only shipped checks; census consistent with tests/verifier.json |
| layer1_package_consistency__instruction_verifier_consistency | PASS | every deliverable carries content checks, every surface is paired, and the hollow/incomplete lanes prove the requirement->check direction executably |
| layer1_package_consistency__solution_instruction_consistency | PASS | gold conforms to the contract and the page (gold_conformance) |
| layer1_package_consistency__solution_verifier_consistency | PASS | gold scores 1.0 and every hollow/incomplete variant of it fails — accepted for the right reasons |
| layer1_package_consistency__artifact_contract_consistency | PASS | every graded surface is a contracted deliverable |
| **layer5_verifier_fairness_static** | PASS | all applicable children pass |
| layer5_verifier_fairness_static__score_bucket_activation | NOT_APPLICABLE | no score buckets — file_check core gate + weights |
| layer5_verifier_fairness_static__aggregation_normalization | PASS | two-tier scoring: 8 core / 6 incidental; partial-pass verified: one failed incidental costs 0.071, reward 0.929; any core failure zeroes |
| layer5_verifier_fairness_static__evidence_routing | PASS | all checks read workspace-relative deliverables |
| layer5_verifier_fairness_static__verifier_execution_completeness | PASS | every check executes and passes on gold (real engine) |
| layer5_verifier_fairness_static__semantic_equivalence | PASS | 10 cosmetic renderings all still score 1.0 (no prose figure surface to reword) |
| layer5_verifier_fairness_static__surface_form_brittleness | PASS | 10 cosmetic renderings all still score 1.0 (no prose figure surface to reword) |
| layer5_verifier_fairness_static__coverage_depth | PASS | every deliverable carries content checks, every surface is paired, and the hollow/incomplete lanes prove the requirement->check direction executably |
| layer5_verifier_fairness_static__scoring_proportionality | PASS | every declared deliverable scores 0 when ABSENT and 0 when HOLLOW (mutations.json: 3 incomplete + 2 hollow replays, all reward 0); weight share by deliverable: verification_note.md 57%, claim_register.csv 29%, results.json 14% |
| layer5_verifier_fairness_static__check_independence | PASS | 2 figure(s) paid more than once, all disclosed in requirements.json with a single CORE payer (results.json); the artifact copies are incidental and cannot zero the task: 3 (results_figures+note_miscounted), 6 (results_figures+note_confirmed) |
| layer5_verifier_fairness_static__counterfactual_strength | PASS | positive + negative + incomplete + adversarial cases ship (test_outputs.py lanes) with mutation evidence in consistency/mutations.json |
| layer5_verifier_fairness_static__requirement_traceability | PASS | check->requirement direction closed (no orphan checks) |
| layer5_verifier_fairness_static__process_grading_justification | NOT_APPLICABLE | no process grading — files only |
| **layer5_reward_hacking_static** | PASS | all applicable children pass |
| layer5_reward_hacking_static__rollout_legitimacy | PASS | grading is deterministic file inspection only — no network, no state, no judge |
| layer5_reward_hacking_static__sanctioned_interface_use | PASS | every graded surface is a contracted deliverable |
| layer5_reward_hacking_static__state_spoofing | NOT_APPLICABLE | no gym/connector state to spoof — static file grading |
| layer5_reward_hacking_static__golden_or_internal_access | PASS | Dockerfile copies input/ only; tests and solution never enter the task image |
| **layer5_llm_judge_design** | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__judge_context_completeness | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__judge_context_truncation | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__judge_failure_handling | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__artifact_grounding | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__judge_execution_validity | NOT_APPLICABLE | no LLM judge in the verifier |
| layer5_llm_judge_design__repeat_stability | NOT_APPLICABLE | no LLM judge in the verifier |
