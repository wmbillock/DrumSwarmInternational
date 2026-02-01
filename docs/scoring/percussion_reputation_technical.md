# Percussion Section Reputation: Technical Implementation Guide

**Target File:** `backend/services/reputation.py` (extend existing module)
**Test File:** `backend/tests/test_percussion_reputation.py` (new comprehensive test suite)
**Integration:** `backend/api/v1/router.py` and `backend/services/talent_pool.py`

---

## Implementation Checklist

### Phase 1: Extend Core Reputation Functions

```python
# backend/services/reputation.py additions

PERCUSSION_TECH_WEIGHTS = {
    'technique': 0.35,
    'general_effect': 0.25,
    'cohesion': 0.25,
    'marching': 0.15,
}

CENTER_SNARE_WEIGHTS = {
    'technique': 0.40,
    'general_effect': 0.30,
    'cohesion': 0.20,
    'marching': 0.10,
}

def compute_percussion_performance_score(
    technique: float,
    general_effect: float,
    cohesion: float,
    marching: float,
    agent_role: str = 'percussion_tech',
) -> float:
    """Compute weighted performance score for percussion agents.

    Args:
        technique: Precision, note accuracy, stick control (0-100)
        general_effect: Musicality, dynamics, visual impact (0-100)
        cohesion: Section synchronization, tempo stability (0-100)
        marching: Visual alignment, spacing, drill execution (0-100)
        agent_role: Either 'percussion_tech', 'center_snare', or 'front_ensemble_tech'

    Returns:
        float: Weighted performance score [0, 100]
    """
    all_scores = [technique, general_effect, cohesion, marching]
    for score in all_scores:
        _validate_score(score, name=f'{agent_role}_component')

    weights = CENTER_SNARE_WEIGHTS if agent_role == 'center_snare' else PERCUSSION_TECH_WEIGHTS

    performance = (
        technique * weights['technique'] +
        general_effect * weights['general_effect'] +
        cohesion * weights['cohesion'] +
        marching * weights['marching']
    )

    return round(_clamp(performance), 2)
```

### Phase 2: Performance Band Adjustments

```python
def apply_performance_band_adjustment(
    old_trust: float,
    performance_score: float,
) -> float:
    """Apply variable dampening based on performance band.

    Args:
        old_trust: Agent's current trust score
        performance_score: This performance's score [0, 100]

    Returns:
        float: Adjusted trust score
    """
    full_new_trust = (old_trust + performance_score) / 2  # Simplified for example

    if performance_score >= 95.0:
        return old_trust + 1.5 * (full_new_trust - old_trust)
    elif performance_score >= 85.0:
        return full_new_trust
    elif performance_score >= 75.0:
        return full_new_trust
    elif performance_score >= 65.0:
        return old_trust + 0.8 * (full_new_trust - old_trust)
    elif performance_score >= 55.0:
        return old_trust + 0.5 * (full_new_trust - old_trust)
    else:
        return old_trust - 2.0 * (old_trust - full_new_trust)
```

### Phase 3: Success Rate Calculations

```python
def calculate_success_rate(agent: dict) -> float:
    """Calculate success percentage for an agent.

    Args:
        agent: Loaded agent YAML dict

    Returns:
        float: Success rate [0.0, 1.0], or None if no sessions
    """
    total = agent.get('total_sessions', 0)
    if total == 0:
        return None

    successful = agent.get('successful_sessions', 0)
    return successful / total


def calculate_weighted_agent_importance(agent: dict) -> float:
    """Weight agent importance by sample size and consistency.

    Args:
        agent: Loaded agent YAML dict

    Returns:
        float: Importance weight [0.0, 1.0+]
    """
    total = agent.get('total_sessions', 0)
    success_rate = calculate_success_rate(agent)

    if success_rate is None:
        return 0.0

    # Emphasize consistency — extreme rates are weighted more
    consistency = abs(success_rate - 0.5) ** 2
    return total * consistency
```

### Phase 4: Probation/Retirement Logic

```python
def evaluate_agent_status(agent: dict) -> str:
    """Determine if agent should transition to probation or retirement.

    Args:
        agent: Loaded agent YAML dict

    Returns:
        str: Recommended status ('active', 'probation', 'retired')
    """
    trust = agent.get('trust_score', 50.0)
    total = agent.get('total_sessions', 0)
    successful = agent.get('successful_sessions', 0)
    failed = agent.get('failed_sessions', 0)

    # Probation thresholds
    if total >= 3 and trust < 40.0:
        return 'probation'

    success_rate = successful / total if total > 0 else None
    if success_rate is not None:
        if success_rate < 0.30 and total >= 5:
            return 'probation'

    # Retirement thresholds
    if total >= 10 and trust < 25.0:
        return 'retired'

    if failed >= 3:
        return 'retired'

    if success_rate is not None and success_rate < 0.20 and total >= 10:
        return 'retired'

    return 'active'
```

### Phase 5: Test Suite

```python
# backend/tests/test_percussion_reputation.py

import pytest
from backend.services.reputation import (
    compute_percussion_performance_score,
    apply_performance_band_adjustment,
    calculate_success_rate,
    calculate_weighted_agent_importance,
    evaluate_agent_status,
)

class TestPercussionPerformanceScoring:
    def test_percussion_tech_weighting(self):
        """Percussion tech: 35% technique, 25% GE, 25% cohesion, 15% marching."""
        score = compute_percussion_performance_score(
            technique=80.0,
            general_effect=70.0,
            cohesion=75.0,
            marching=85.0,
            agent_role='percussion_tech'
        )
        expected = 0.35*80 + 0.25*70 + 0.25*75 + 0.15*85
        assert abs(score - expected) < 0.01

    def test_center_snare_weighting(self):
        """Center snare: 40% technique, 30% GE, 20% cohesion, 10% marching."""
        score = compute_percussion_performance_score(
            technique=90.0,
            general_effect=80.0,
            cohesion=75.0,
            marching=70.0,
            agent_role='center_snare'
        )
        expected = 0.40*90 + 0.30*80 + 0.20*75 + 0.10*70
        assert abs(score - expected) < 0.01

    def test_performance_band_elite(self):
        """Elite performance (95+) accelerates trust growth."""
        old_trust = 70.0
        new_trust = apply_performance_band_adjustment(old_trust, 98.0)
        # Should grow faster than standard moving average
        assert new_trust > old_trust

    def test_performance_band_failure(self):
        """Poor performance (0-54) accelerates trust decay."""
        old_trust = 70.0
        new_trust = apply_performance_band_adjustment(old_trust, 45.0)
        # Should decay faster than standard moving average
        assert new_trust < old_trust

    def test_success_rate_calculation(self):
        """Success rate = successful / total."""
        agent = {
            'total_sessions': 20,
            'successful_sessions': 16,
            'failed_sessions': 4,
        }
        rate = calculate_success_rate(agent)
        assert abs(rate - 0.80) < 0.01

    def test_weighted_importance_consistency(self):
        """Agent with extreme success rate weighted higher."""
        agent_high = {
            'total_sessions': 10,
            'successful_sessions': 9,
            'failed_sessions': 1,
        }
        agent_marginal = {
            'total_sessions': 10,
            'successful_sessions': 5,
            'failed_sessions': 5,
        }

        w_high = calculate_weighted_agent_importance(agent_high)
        w_marginal = calculate_weighted_agent_importance(agent_marginal)

        # High-consistency agent weighted more
        assert w_high > w_marginal

    def test_probation_transition(self):
        """Agent with trust < 40 after 3+ sessions → probation."""
        agent = {
            'trust_score': 35.0,
            'total_sessions': 5,
            'successful_sessions': 2,
            'failed_sessions': 3,
        }
        status = evaluate_agent_status(agent)
        assert status == 'probation'

    def test_retirement_transition(self):
        """Agent with trust < 25 after 10+ sessions → retirement."""
        agent = {
            'trust_score': 20.0,
            'total_sessions': 10,
            'successful_sessions': 2,
            'failed_sessions': 8,
        }
        status = evaluate_agent_status(agent)
        assert status == 'retired'

    def test_retention_despite_low_trust(self):
        """Agent with low trust but <3 sessions stays active (dampening window)."""
        agent = {
            'trust_score': 40.0,
            'total_sessions': 2,
            'successful_sessions': 1,
            'failed_sessions': 1,
        }
        status = evaluate_agent_status(agent)
        assert status == 'active'
```

---

## API Integration Points

### V1 Router Addition

```python
# backend/api/v1/router.py addition

@router.post('/percussion/{agent_id}/evaluate')
async def evaluate_percussion_agent(
    agent_id: str,
    technique: float,
    general_effect: float,
    cohesion: float,
    marching: float,
    session_id: str,
):
    """Evaluate percussion agent on multi-dimensional performance."""
    db = get_db()
    pool_dir = Path('talent_pool')

    performance_score = compute_percussion_performance_score(
        technique=technique,
        general_effect=general_effect,
        cohesion=cohesion,
        marching=marching,
        agent_role='percussion_tech',
    )

    # Update reputation
    agent = _load_agent(pool_dir, agent_id)
    old_trust = agent.get('trust_score', 50.0)
    new_trust = apply_performance_band_adjustment(old_trust, performance_score)
    agent['trust_score'] = new_trust

    # Check status transition
    new_status = evaluate_agent_status(agent)
    if new_status != agent.get('availability', 'active'):
        agent['availability'] = new_status

    _save_agent(pool_dir, agent)

    return {'agent_id': agent_id, 'trust_score': new_trust, 'status': new_status}
```

---

## Monitoring Dashboard Metrics

Add to backend monitoring:

```python
def get_percussion_health_metrics(pool_dir: Path) -> dict:
    """Compute key metrics for percussion section."""
    pool = load_talent_pool(pool_dir)
    agents = pool['agents']

    # Filter to percussion agents
    perc_agents = [a for a in agents if 'perc' in a.get('primary_instrument', '').lower()]

    if not perc_agents:
        return {}

    trust_scores = [a['trust_score'] for a in perc_agents]
    success_rates = [calculate_success_rate(a) for a in perc_agents if calculate_success_rate(a) is not None]
    probation_count = sum(1 for a in perc_agents if a.get('availability') == 'probation')
    retired_count = sum(1 for a in perc_agents if a.get('availability') == 'retired')

    return {
        'mean_trust': sum(trust_scores) / len(trust_scores),
        'min_trust': min(trust_scores),
        'max_trust': max(trust_scores),
        'mean_success_rate': sum(success_rates) / len(success_rates) if success_rates else None,
        'probation_count': probation_count,
        'retired_count': retired_count,
        'total_agents': len(perc_agents),
    }
```

---

## Database Sync Workflow

After reputation updates via YAML, sync back to DB:

```python
def sync_percussion_reputations_to_db(db: Session, pool_dir: Path):
    """Sync YAML reputation changes back to Performer DB table."""
    pool = load_talent_pool(pool_dir)

    for agent_yaml in pool['agents']:
        if 'perc' not in agent_yaml.get('primary_instrument', '').lower():
            continue

        performer = db.query(Performer).filter(
            Performer.id == agent_yaml['agent_id']
        ).first()

        if not performer:
            continue

        # Update all reputation fields
        performer.trust_score = agent_yaml.get('trust_score', 50.0)
        performer.total_sessions = agent_yaml.get('total_sessions', 0)
        performer.successful_sessions = agent_yaml.get('successful_sessions', 0)
        performer.failed_sessions = agent_yaml.get('failed_sessions', 0)
        performer.status = PerformerStatus(agent_yaml.get('availability', 'active'))

    db.commit()
```

---

## Deployment Checklist

- [ ] Extend `backend/services/reputation.py` with percussion-specific functions
- [ ] Create `backend/tests/test_percussion_reputation.py` with full test coverage
- [ ] Add API endpoints to `backend/api/v1/router.py`
- [ ] Update `docs/api/openapi.md` with new endpoints
- [ ] Implement monitoring in `backend/services/metrics.py`
- [ ] Add DB sync workflow to metronome or post-scoring handler
- [ ] Run full test suite: `pytest backend/tests/test_*reputation*.py -v`
- [ ] Load test with 100+ agents, 50+ competitions
- [ ] Deploy to staging, verify YAML file atomicity
- [ ] Monitor probation/retirement transitions
- [ ] Document in CLAUDE.md completion section
