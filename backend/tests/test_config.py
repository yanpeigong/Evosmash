import os

import config


def test_runtime_description_masks_secret(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "sk-test-secret-1234")

    payload = config.describe_runtime_config()

    assert payload["llm"]["api_key_preview"] == "sk-t...1234"


def test_load_env_files_reads_env_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("EVOSMASH_TEST_FLAG=enabled\n", encoding="utf-8")
    monkeypatch.delenv("EVOSMASH_TEST_FLAG", raising=False)

    loaded_path = config.load_env_files([str(env_file)])

    assert loaded_path == str(env_file)
    assert os.getenv("EVOSMASH_TEST_FLAG") == "enabled"


def test_runtime_description_contains_expected_keys():
    payload = config.describe_runtime_config()

    assert "max_upload_size_mb" in payload
    assert "llm" in payload
    assert "loaded_env_file" in payload
