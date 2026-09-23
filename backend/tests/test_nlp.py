import pytest

from app.services.nlp import HAS_NLP, nlp_service

pytestmark = pytest.mark.skipif(not HAS_NLP, reason="NLP dependencies not installed")


def test_extract_skills_electrician() -> None:
    text = (
        "Seeking an Industrial Wireman with expertise in conduit wiring, "
        "panel wiring, three phase motor installation, and "
        "MCB circuit breaker testing. Must be proficient with multimeter and earthing."
    )
    result = nlp_service.extract_skills(text)
    assert "conduit wiring" in result["skills"]
    assert "panel wiring" in result["skills"]
    assert "three phase" in result["skills"]
    assert "mcb" in result["skills"]
    assert "multimeter" in result["skills"]
    assert "earthing" in result["skills"]
    assert result["trade_matches"]["Electrician"]
    assert result["confidence"] >= 0.80


def test_extract_skills_fitter() -> None:
    text = (
        "Required mechanical bench fitter for machine tooling. "
        "Candidate needs hands-on lathe operation, precision drilling, tapping, "
        "and tolerance measurement using vernier caliper and micrometer."
    )
    result = nlp_service.extract_skills(text)
    assert "lathe operation" in result["skills"]
    assert "drilling" in result["skills"]
    assert "tapping" in result["skills"]
    assert "tolerance" in result["skills"]
    assert "vernier caliper" in result["skills"]
    assert "micrometer" in result["skills"]
    assert result["trade_matches"]["Fitter"]
    assert result["confidence"] >= 0.80


def test_extract_skills_welder() -> None:
    text = (
        "Hiring certified Welder for structural fabrication. Must have "
        "proven experience in TIG welding, MIG welding, SMAW arc welding, "
        "and weld joint preparation with shielding gas."
    )
    result = nlp_service.extract_skills(text)
    assert "tig welding" in result["skills"]
    assert "mig welding" in result["skills"]
    assert "smaw" in result["skills"]
    assert "weld joint" in result["skills"]
    assert "shielding gas" in result["skills"]
    assert result["trade_matches"]["Welder"]
    assert result["confidence"] >= 0.80


def test_extract_skills_automobile_mechanic() -> None:
    text = (
        "Authorized dealership hiring Automobile Technician. "
        "Must be skilled in diesel engine maintenance, engine overhaul, "
        "CRDI fuel injector calibration, brake bleeding, and suspension."
    )
    result = nlp_service.extract_skills(text)
    assert "engine overhaul" in result["skills"]
    assert "diesel engine maintenance" in result["skills"]
    assert "crdi" in result["skills"]
    assert "fuel injector" in result["skills"]
    assert "brake bleeding" in result["skills"]
    assert "suspension" in result["skills"]
    assert result["trade_matches"]["Automobile/Diesel Mechanic"]
    assert result["confidence"] >= 0.80


def test_extract_skills_copa() -> None:
    text = (
        "Wanted Computer Operator with COPA qualification. "
        "Job responsibilities include MS Office data entry, Excel formulas, "
        "SQL database queries, basic Python scripts, and Tally accounting."
    )
    result = nlp_service.extract_skills(text)
    assert "ms office" in result["skills"]
    assert "excel formulas" in result["skills"]
    assert "sql" in result["skills"]
    assert "python" in result["skills"]
    assert "tally" in result["skills"]
    assert result["trade_matches"]["COPA"]
    assert result["confidence"] >= 0.80


def test_extract_skills_empty_or_irrelevant() -> None:
    assert nlp_service.extract_skills("")["confidence"] == 0.0
    assert nlp_service.extract_skills("   ")["skill_count"] == 0

    irrelevant = "Looking for a sales executive to sell credit cards on phone."
    res = nlp_service.extract_skills(irrelevant)
    assert res["skill_count"] == 0
    assert res["confidence"] == 0.0
