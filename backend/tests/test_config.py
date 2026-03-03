from backend.config import Settings


def test_api_keys_are_stripped():
    settings = Settings(
        openai_api_key="  sk-test\n\n",
        qdrant_api_key="  qdrant-key\n",
    )
    assert settings.openai_api_key == "sk-test"
    assert settings.qdrant_api_key == "qdrant-key"


def test_missing_qdrant_api_key_is_allowed():
    settings = Settings(qdrant_api_key="")
    assert settings.qdrant_api_key == ""
