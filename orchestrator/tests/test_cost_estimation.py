"""Tests for ForgeAgent._estimate_cost()."""

from __future__ import annotations

import pytest

from forge.agents.base import ForgeAgent


class TestEstimateCost:
    def test_sonnet_known_rate(self):
        # 1M in + 1M out = $3.00 + $15.00 = $18.00
        cost = ForgeAgent._estimate_cost(1_000_000, 1_000_000, "claude-sonnet-4-6")
        assert cost == pytest.approx(18.0)

    def test_haiku_known_rate(self):
        # 1M in + 1M out = $0.80 + $4.00 = $4.80
        cost = ForgeAgent._estimate_cost(1_000_000, 1_000_000, "claude-haiku-4-5")
        assert cost == pytest.approx(4.80)

    def test_opus_known_rate(self):
        # 1M in + 1M out = $15.00 + $75.00 = $90.00
        cost = ForgeAgent._estimate_cost(1_000_000, 1_000_000, "claude-opus-4-6")
        assert cost == pytest.approx(90.0)

    def test_gpt4o_known_rate(self):
        # 1M in + 1M out = $2.50 + $10.00 = $12.50
        cost = ForgeAgent._estimate_cost(1_000_000, 1_000_000, "gpt-4o")
        assert cost == pytest.approx(12.50)

    def test_zero_tokens(self):
        cost = ForgeAgent._estimate_cost(0, 0, "claude-sonnet-4-6")
        assert cost == 0.0

    def test_unknown_model_uses_default_rate(self):
        # Unknown model should fall back to sonnet rates: $3/$15 per 1M
        cost_unknown = ForgeAgent._estimate_cost(100_000, 50_000, "some-future-model")
        cost_sonnet = ForgeAgent._estimate_cost(100_000, 50_000, "claude-sonnet-4-6")
        assert cost_unknown == cost_sonnet

    def test_realistic_token_counts(self):
        # 2000 in, 500 out with haiku
        # = 2000 * 0.80/1e6 + 500 * 4.0/1e6
        # = 0.0000016 + 0.000002 = 0.0000036
        cost = ForgeAgent._estimate_cost(2000, 500, "claude-haiku-4-5")
        assert cost == pytest.approx(0.0016 / 1000 + 0.002 / 1000, rel=1e-5)

    def test_only_input_tokens(self):
        cost = ForgeAgent._estimate_cost(1_000_000, 0, "claude-sonnet-4-6")
        assert cost == pytest.approx(3.0)

    def test_only_output_tokens(self):
        cost = ForgeAgent._estimate_cost(0, 1_000_000, "claude-sonnet-4-6")
        assert cost == pytest.approx(15.0)
