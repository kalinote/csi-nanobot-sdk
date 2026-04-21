from nanobot.config.schema import DreamConfig


def test_dream_config_defaults_to_interval_hours() -> None:
    cfg = DreamConfig()

    assert cfg.model_override is None
    assert cfg.max_batch_size == 20
    assert cfg.max_iterations == 15


def test_dream_config_dump_has_expected_keys() -> None:
    cfg = DreamConfig.model_validate({"maxBatchSize": 7})

    dumped = cfg.model_dump(by_alias=True)

    assert dumped["maxBatchSize"] == 7
    assert "modelOverride" in dumped


def test_dream_config_uses_model_override_name_and_accepts_legacy_model() -> None:
    cfg = DreamConfig.model_validate({"model": "anthropic/claude-sonnet-4-6"})

    dumped = cfg.model_dump(by_alias=True)

    assert cfg.model_override == "anthropic/claude-sonnet-4-6"
    assert dumped["modelOverride"] == "anthropic/claude-sonnet-4-6"
    assert "model" not in dumped
