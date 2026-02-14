# Model Strategy UI Gap Analysis

## 1. Where should corps model strategy be displayed?

**Already exists:** `frontend/src/components/StrategyPanel.tsx` is rendered inside `CorpsDetailV2.tsx` and `CorpsDeepDive.tsx`. It shows:
- Model policy, preferred provider, adaptation style
- Exploration rate slider, risk tolerance
- Section overrides (brass, percussion, etc.)
- Category performance cards (avg score, attempts, success rate)
- Strategy history from past seasons

**Gap:** StrategyPanel is read-only. There is no inline editing — `v1.updateCorpsStrategy()` exists in `v1.ts` but no UI calls it. A settings/edit mode should be added to StrategyPanel so users can tweak strategy without API calls.

**Recommendation:** Keep StrategyPanel where it is (corps detail pages). Add an edit toggle that enables inline editing of fields via `v1.updateCorpsStrategy()`.

---

## 2. Where should the model-spec leaderboard live?

**Best fit:** `frontend/src/pages/ScoreboardsPage.tsx`

ScoreboardsPage already has a tab architecture with "Corps" (13-column table) and "Agents" (7-column table). Adding a third **"Model Specs"** tab is the natural home for a model-spec leaderboard.

**Backend ready:** `GET /api/v1/model-specs` returns all specs. `GET /api/v1/leaderboard/{task_category}` returns ranked entries with `corps_id`, `spec_id`, `score`, `attempts`, `wins`, `rank`.

**Frontend ready:** `v1.listModelSpecs()` and `v1.getLeaderboard(category)` already exist in `v1.ts`. Types `V1ModelSpec` and `V1LeaderboardEntry` are defined.

**Implementation:** Add a "Model Specs" tab to ScoreboardsPage that:
1. Lists all model specs in a DataTable (spec_id, provider, model_name, tier, context_window, cost metrics)
2. Below the spec list, shows a leaderboard per task category using `v1.getLeaderboard()`
3. Clicking a spec row could expand to show per-corps performance

---

## 3. Where should model-spec performance over time be charted?

**Option A (recommended): New tab in PerformanceExplorer**

`frontend/src/pages/PerformanceExplorer.tsx` already supports 5 metric types with a `TrendChart` component. Adding a "Model Performance" metric type that charts spec scores over time fits naturally.

**Option B: Inline in ScoreboardsPage "Model Specs" tab**

Embed a `TrendChart` below the leaderboard table showing selected spec performance over rounds/seasons.

**Option C: StrategyPanel expansion**

Add a small sparkline/trend chart to each category performance card in StrategyPanel, showing how that corps's chosen model performs over time.

**Recommendation:** Do all three — they serve different audiences:
- PerformanceExplorer: cross-corps comparison of model specs over time
- ScoreboardsPage: global leaderboard with optional trend view
- StrategyPanel: corps-specific model performance context

---

## 4. What existing UI components can be reused?

| Component | Location | Reuse for |
|-----------|----------|-----------|
| `DataTable` | `frontend/src/ui/DataTable.tsx` | Model spec list, leaderboard table |
| `TrendChart` | `frontend/src/components/TrendChart.tsx` | Performance over time charts |
| `MetricsCard` | `frontend/src/components/MetricsCard.tsx` | Summary stats (total specs, avg score, top model) |
| `Badge` | `frontend/src/ui/Badge.tsx` | Tier badges, provider badges |
| `Panel` | `frontend/src/ui/Panel.tsx` | Section containers |
| `Leaderboard` | `frontend/src/components/Leaderboard.tsx` | Ranked model spec display |
| `Tabs` | `frontend/src/ui/Tabs.tsx` | ScoreboardsPage tab extension |
| `StrategyPanel` | `frontend/src/components/StrategyPanel.tsx` | Already handles strategy display |

All components are well-typed and support the needed props.

---

## 5. What new components are needed?

### 5a. `ModelSpecCard` (small)
Compact card showing a single model spec: provider logo/icon, model name, tier badge, key stats (context window, cost). Used in spec lists and leaderboard rows.

### 5b. `StrategyEditor` (medium)
Edit mode for StrategyPanel — form fields for model_policy, preferred_provider, adaptation_style, exploration_rate (slider), risk_tolerance (slider), section_overrides. Calls `v1.updateCorpsStrategy()` on save.

### 5c. `SpecComparisonChart` (medium)
Side-by-side comparison of 2-3 model specs showing performance metrics across task categories. Uses TrendChart internally.

### 5d. `ModelSpecsTab` (in ScoreboardsPage)
Not a standalone component — a new tab section within ScoreboardsPage that composes DataTable + Leaderboard + optional TrendChart for the "Model Specs" view.

---

## 6. Does the frontend type system need new types?

**No new types needed.** All required types already exist in `frontend/src/services/v1.ts`:

| Type | Fields |
|------|--------|
| `V1ModelSpec` | `spec_id`, `provider`, `model_name`, `tier`, `context_window`, `input_cost_per_1k`, `output_cost_per_1k`, `supports_tools`, `supports_vision` |
| `V1ModelSpecPerf` | `spec_id`, `provider`, `model_name`, `avg_score`, `total_attempts`, `by_category` |
| `V1SpecPerformanceDetail` | `category`, `avg_score`, `attempts`, `trend` |
| `V1CorpsStrategy` | `corps_id`, `model_policy`, `preferred_provider`, `adaptation_style`, `exploration_rate`, `risk_tolerance`, `section_overrides`, `category_performance` |
| `V1StrategyHistoryEntry` | `season_id`, `strategy`, `performance_summary` |
| `V1LeaderboardEntry` | `rank`, `corps_id`, `spec_id`, `score`, `attempts`, `wins` |

**API functions also exist:**
- `listModelSpecs()`, `getSpecPerformance(specId)`
- `getCorpsStrategy(corpsId)`, `getCorpsStrategyHistory(corpsId)`, `updateCorpsStrategy(corpsId, data)`
- `getLeaderboard(category)`

---

## Summary: Implementation Priority

| Priority | Task | Effort |
|----------|------|--------|
| 1 | Add "Model Specs" tab to ScoreboardsPage | Medium |
| 2 | Add edit mode to StrategyPanel | Small |
| 3 | Add model performance metric to PerformanceExplorer | Small |
| 4 | Build SpecComparisonChart component | Medium |
| 5 | Add sparklines to StrategyPanel category cards | Small |
