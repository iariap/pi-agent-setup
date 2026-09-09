#!/usr/bin/env python3
"""Illustrative costs, not measured token usage or subscription billing."""
import argparse
import json


def estimate(attempts=1, output_multiplier=1.0):
    # USD per million, reference list rates observed 2026-09-09 (see README).
    rates = {'glm': (0.15, 0.50), 'sol': (4.0, 20.0)}
    stages = {'plan': (20000, 3000), 'execute': (180000, 20000), 'review': (40000, 3000)}
    def cost(model, stage):
        incoming, outgoing = stages[stage]
        i_rate, o_rate = rates[model]
        return (incoming * i_rate + outgoing * output_multiplier * o_rate) / 1e6
    def route(planner, executor, reviewer):
        return cost(planner, 'plan') + attempts * (cost(executor, 'execute') + cost(reviewer, 'review'))
    return {
        'scenario': {'attempts': attempts, 'output_multiplier': output_multiplier,
                     'total_input_tokens': 20000 + attempts * 220000,
                     'total_output_tokens_including_reasoning': output_multiplier * (3000 + attempts * 23000)},
        'all_sol_api_reference_usd': round(route('sol', 'sol', 'sol'), 6),
        'hybrid_api_reference_usd': round(route('sol', 'glm', 'sol'), 6),
        'all_glm_api_reference_usd': round(route('glm', 'glm', 'glm'), 6),
        'configured_hybrid_glm_api_usd': round(attempts * cost('glm', 'execute'), 6),
        'configured_hybrid_sol_quota_tokens': {
            'input': 20000 + attempts * 40000,
            'output_including_reasoning': output_multiplier * (3000 + attempts * 3000)},
        'subscription_charge_usd': 'unknown: existing subscription, quotas and credits apply',
        'excluded': ['cache discounts', 'orchestrator overhead', 'tools/CI cost', 'human review', 'taxes/fees'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempts', type=int, default=1)
    parser.add_argument('--output-multiplier', type=float, default=1.0)
    args = parser.parse_args()
    if args.attempts < 1 or args.output_multiplier <= 0:
        parser.error('Use attempts >= 1 and output-multiplier > 0')
    print(json.dumps(estimate(args.attempts, args.output_multiplier), indent=2))
