import re
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]


def _dotenv_names(path: Path) -> set[str]:
    return {
        match.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"^([A-Z][A-Z0-9_]*)=", line))
    }


def test_env_example_documents_every_compose_substitution():
    compose = (REPOSITORY / "docker-compose.yml").read_text(encoding="utf-8")
    documented = _dotenv_names(REPOSITORY / ".env.example")
    referenced = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", compose))

    assert referenced <= documented


def test_provider_secrets_are_not_configured_as_public_frontend_values():
    dotenv = (REPOSITORY / ".env.example").read_text(encoding="utf-8")

    assert "NEXT_PUBLIC_API_KEY" not in dotenv
    assert "NEXT_PUBLIC_REQUIRE_API_KEY" in dotenv
    assert "COHERE_API_KEY" in dotenv
    assert "GEMINI_API_KEY" in dotenv
