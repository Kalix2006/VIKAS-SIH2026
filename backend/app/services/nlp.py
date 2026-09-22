"""NLP Service for trade-specific skill and tool extraction using spaCy.

Uses spaCy's en_core_web_sm pipeline augmented with an EntityRuler
seeded for the five locked trades:
- Electrician
- Fitter
- Welder
- Automobile/Diesel Mechanic
- COPA

Never calls the LLM for extraction or scoring.
"""

import logging
from typing import Any, cast

try:
    import spacy
    from spacy.pipeline import EntityRuler

    HAS_NLP = True
except ImportError:
    HAS_NLP = False

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_posting import JobPosting

logger = logging.getLogger("vikas.nlp")

# Seed patterns for the 5 locked trades.
# Designed for clean modular extension by adding new trade keys and patterns.
TRADE_SKILL_PATTERNS: dict[str, list[str]] = {
    "Electrician": [
        "conduit wiring",
        "multimeter",
        "mcb",
        "circuit breaker",
        "single phase",
        "three phase",
        "earthing",
        "transformer",
        "relay",
        "plc",
        "panel wiring",
        "electrical maintenance",
        "megger testing",
        "cable jointing",
        "solar panel installation",
        "distribution board",
        "wireman",
    ],
    "Fitter": [
        "lathe operation",
        "lathe",
        "drilling",
        "tapping",
        "micrometer",
        "vernier caliper",
        "filing",
        "assembly",
        "tolerance",
        "milling",
        "cnc machine",
        "bench fitting",
        "grinding",
        "sheet metal work",
        "pipe fitting",
        "blueprint reading",
    ],
    "Welder": [
        "smaw",
        "tig welding",
        "mig welding",
        "arc welding",
        "gas cutting",
        "weld joint",
        "shielding gas",
        "electrode",
        "flux cored welding",
        "spot welding",
        "brazing",
        "weld inspection",
        "torch brazing",
    ],
    "Automobile/Diesel Mechanic": [
        "engine overhaul",
        "diesel engine maintenance",
        "brake bleeding",
        "crdi",
        "fuel injector",
        "clutch adjustment",
        "transmission",
        "diagnostic scan",
        "suspension",
        "wheel alignment",
        "radiator repair",
        "turbocharger",
    ],
    "COPA": [
        "python",
        "javascript",
        "sql",
        "html/css",
        "ms office",
        "excel formulas",
        "tally",
        "accounting",
        "operating systems",
        "networking basics",
        "cybersecurity basics",
        "web design",
        "database management",
    ],
}


class NLPService:
    """Extracts vocational skills and tools from raw job descriptions."""

    def __init__(self) -> None:
        self.nlp: Any = None

    def _get_nlp(self) -> Any:
        if self.nlp is None:
            if not HAS_NLP:
                raise RuntimeError(
                    "NLP dependencies not installed. Install with `pip install .[nlp]`"
                )
            self.nlp = spacy.load("en_core_web_sm")
            self._setup_entity_ruler()
        return self.nlp

    def _setup_entity_ruler(self) -> None:
        """Add custom EntityRuler to spaCy pipeline with trade patterns."""
        if "entity_ruler" in self.nlp.pipe_names:
            self.nlp.remove_pipe("entity_ruler")

        ruler = cast(EntityRuler, self.nlp.add_pipe("entity_ruler", before="ner"))
        patterns: list[dict[str, Any]] = []

        for trade_name, skills in TRADE_SKILL_PATTERNS.items():
            for skill in skills:
                # Add lowercase phrase pattern
                patterns.append(
                    {
                        "label": "SKILL",
                        "pattern": [{"LOWER": token} for token in skill.split()],
                        "id": trade_name,
                    }
                )

        ruler.add_patterns(patterns)

    def extract_skills(self, text: str) -> dict[str, Any]:
        """Extract trade-specific skills from raw text.

        Returns structured dictionary containing extracted skills,
        trade groupings, total count, and algorithmic extraction confidence.
        """
        if not text or not text.strip():
            return {
                "skills": [],
                "trade_matches": {},
                "skill_count": 0,
                "confidence": 0.0,
            }

        nlp = self._get_nlp()
        doc = nlp(text)
        extracted: dict[str, list[str]] = {}
        unique_skills: set[str] = set()

        for ent in doc.ents:
            if ent.label_ == "SKILL":
                skill_text = ent.text.lower()
                trade_id = ent.ent_id_
                unique_skills.add(skill_text)
                if trade_id not in extracted:
                    extracted[trade_id] = []
                if skill_text not in extracted[trade_id]:
                    extracted[trade_id].append(skill_text)

        skill_count = len(unique_skills)

        # Non-blackbox confidence calculation based on match saturation:
        # 0 skills -> 0.0
        # 1 skill  -> 0.50
        # 2 skills -> 0.65
        # 3 skills -> 0.78
        # 4+ skills -> 0.85 - 1.0 (saturates smoothly)
        if skill_count == 0:
            confidence = 0.0
        elif skill_count == 1:
            confidence = 0.50
        elif skill_count == 2:
            confidence = 0.65
        elif skill_count == 3:
            confidence = 0.78
        else:
            confidence = min(1.0, 0.80 + (skill_count - 3) * 0.04)

        return {
            "skills": sorted(list(unique_skills)),
            "trade_matches": extracted,
            "skill_count": skill_count,
            "confidence": round(confidence, 4),
        }

    async def process_unparsed_postings(
        self, db: AsyncSession, limit: int = 100
    ) -> int:
        """Fetch job postings without extracted skills, parse and update them."""
        query = (
            select(JobPosting).where(JobPosting.extracted_skills.is_(None)).limit(limit)
        )
        postings = list((await db.execute(query)).scalars().all())

        for posting in postings:
            extracted = self.extract_skills(posting.raw_description)
            posting.extracted_skills = extracted

        await db.commit()
        return len(postings)


# Singleton instance
nlp_service = NLPService()
