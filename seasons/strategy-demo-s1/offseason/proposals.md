# Offseason Proposals


## Proposal 1: Decrease exploration_rate from 0.15 to 0.05 (top performer — lock in winning configuration)

```yaml
proposal_type: strategy_change
corps_id: pit-happens
description: Decrease exploration_rate from 0.15 to 0.05 (top performer — lock in
  winning configuration)
changes:
  exploration_rate: 0.04999999999999999
```


## Proposal 2: Switch to section_specialized: use deepseek-coder-v2 for frontend (outperforms current provider)

```yaml
proposal_type: strategy_change
corps_id: quiet-trumpets
description: 'Switch to section_specialized: use deepseek-coder-v2 for frontend (outperforms
  current provider)'
changes:
  model_policy: section_specialized
  section_overrides: '{"frontend": "82179fec-c666-4c0e-abc3-9c7590c5ec2f"}'
```


## Proposal 3: Increase exploration_rate from 0.40 to 0.50 (underperforming in 1 categories)

```yaml
proposal_type: strategy_change
corps_id: toss-and-pray
description: Increase exploration_rate from 0.40 to 0.50 (underperforming in 1 categories)
changes:
  exploration_rate: 0.5
```
