# Strategy Evolution Demo
Generated: 2026-02-14T04:44:19.255537+00:00

## Model Specs
- claude-sonnet-4-5 (anthropic)
- deepseek-coder-v2 (ollama)
- gpt-4o (openai)

## Season Setup
- Season: strategy-demo-s1
- Show: strategy-demo-show
- Corps: The Quiet Trumpets, Pit Happens, Toss And Pray

## Standings
- #1 pit-happens: 87.62
- #2 quiet-trumpets: 69.78
- #3 toss-and-pray: 59.48

## Strategy Proposals
- [pit-happens] Decrease exploration_rate from 0.15 to 0.05 (top performer — lock in winning configuration)
- [quiet-trumpets] Switch to section_specialized: use deepseek-coder-v2 for frontend (outperforms current provider)
- [toss-and-pray] Increase exploration_rate from 0.40 to 0.50 (underperforming in 1 categories)

- Proposal 0: applied
- Proposal 1: applied
- Proposal 2: applied

## Strategy Changes

### The Quiet Trumpets
- Before: policy=single_provider, exploration=0.05
- After: policy=section_specialized, exploration=0.05
- Changed: Yes

### Pit Happens
- Before: policy=best_of_breed, exploration=0.15
- After: policy=best_of_breed, exploration=0.05
- Changed: Yes

### Toss And Pray
- Before: policy=random_exploration, exploration=0.40
- After: policy=random_exploration, exploration=0.50
- Changed: Yes

## Model Spec Leaderboard

### frontend
- #1 deepseek-coder-v2: avg=93.0
- #2 gpt-4o: avg=81.4
- #3 claude-sonnet-4-5: avg=72.6

### backend
- #1 claude-sonnet-4-5: avg=91.1
- #2 gpt-4o: avg=79.4
- #3 deepseek-coder-v2: avg=65.1

### testing
- #1 gpt-4o: avg=86.2
- #2 claude-sonnet-4-5: avg=84.4
- #3 deepseek-coder-v2: avg=79.0

## Improvement Analysis
- The Quiet Trumpets: Improved (single_provider -> section_specialized)
- Pit Happens: Improved (best_of_breed -> best_of_breed)
- Toss And Pray: Improved (random_exploration -> random_exploration)