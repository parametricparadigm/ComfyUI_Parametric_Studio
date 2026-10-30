"""Tests for psn_nodes.gen.psn_lora_train_config."""

import json
import pytest

from psn_nodes.gen.psn_lora_train_config import (
    PSN_LoRA_Param_Set,
    PSN_LoRA_Train_HunYuan,
    _is_power_of_two,
    _validate_params,
)


def test_psn_lora_param_set_valid_config():
    node = PSN_LoRA_Param_Set()
    config, status = node.run(
        learning_rate=1e-4,
        batch_size=2,
        steps=1000,
        rank=16,
        alpha=16.0,
        network_module="lora",
    )
    assert status == "ok"
    assert config["rank"] == 16
    assert config["batch_size"] == 2
    assert config["learning_rate"] == pytest.approx(1e-4)
    assert config["network_module"] == "lora"
    assert config["model"] == "hunyuan"


def test_psn_lora_param_set_rejects_invalid_rank():
    node = PSN_LoRA_Param_Set()
    config, status = node.run(
        learning_rate=1e-4,
        batch_size=1,
        steps=100,
        rank=3,  # not a power of two
        alpha=8.0,
        network_module="lora",
    )
    assert status != "ok"
    assert "power of two" in status
    assert config == {}


def test_psn_lora_param_set_rejects_batch_size_too_large():
    node = PSN_LoRA_Param_Set()
    config, status = node.run(
        learning_rate=1e-4,
        batch_size=8,  # exceeds max of 4
        steps=100,
        rank=8,
        alpha=8.0,
        network_module="lora",
    )
    assert status != "ok"
    assert "at most 4" in status


def test_psn_lora_param_set_rejects_negative_learning_rate():
    node = PSN_LoRA_Param_Set()
    config, status = node.run(
        learning_rate=-1e-4,
        batch_size=1,
        steps=100,
        rank=8,
        alpha=8.0,
        network_module="lora",
    )
    assert status != "ok"
    assert "positive" in status


def test_psn_lora_param_set_rejects_invalid_network_module():
    node = PSN_LoRA_Param_Set()
    config, status = node.run(
        learning_rate=1e-4,
        batch_size=1,
        steps=100,
        rank=8,
        alpha=8.0,
        network_module="invalid_module",
    )
    assert status != "ok"
    assert "network_module" in status


def test_psn_lora_train_hunyuan_valid_payload():
    param_node = PSN_LoRA_Param_Set()
    config, _ = param_node.run(
        learning_rate=1e-4,
        batch_size=1,
        steps=500,
        rank=32,
        alpha=32.0,
        network_module="lora",
    )
    train_node = PSN_LoRA_Train_HunYuan()
    lora_path, loss_curve, status = train_node.run(
        config=config,
        base_model_path="/models/hunyuan",
        output_dir="/outputs",
    )
    assert status == "payload_ready"
    assert lora_path == "/outputs/hunyuan_lora_rank32_step500.safetensors"
    loss_data = json.loads(loss_curve)
    assert loss_data["type"] == "synthetic"
    assert loss_data["steps"] == 500


def test_psn_lora_train_hunyuan_rejects_missing_config_keys():
    train_node = PSN_LoRA_Train_HunYuan()
    bad_config = {"learning_rate": 1e-4}  # missing many keys
    lora_path, loss_curve, status = train_node.run(
        config=bad_config,
        base_model_path="/models/hunyuan",
        output_dir="/outputs",
    )
    assert status.startswith("error")
    assert "missing keys" in status
    assert lora_path == ""


def test_psn_lora_train_hunyuan_rejects_non_dict_config():
    train_node = PSN_LoRA_Train_HunYuan()
    lora_path, loss_curve, status = train_node.run(
        config="not a dict",
        base_model_path="/models/hunyuan",
        output_dir="/outputs",
    )
    assert status.startswith("error")
    assert "dict" in status


def test_is_power_of_two_edge_cases():
    assert _is_power_of_two(1) is True
    assert _is_power_of_two(2) is True
    assert _is_power_of_two(4) is True
    assert _is_power_of_two(8) is True
    assert _is_power_of_two(16) is True
    assert _is_power_of_two(3) is False
    assert _is_power_of_two(0) is False
    assert _is_power_of_two(-4) is False
    assert _is_power_of_two(3.0) is False
    assert _is_power_of_two(True) is False  # bool is subclass of int


def test_validate_params_zero_steps():
    ok, result = _validate_params(1e-4, 1, 0, 8, 8.0, "lora")
    assert ok is False
    assert "steps" in result
