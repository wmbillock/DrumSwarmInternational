"""V1 API — Metrics routes (scoreboards, bottlenecks, trends, timeseries)."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter

from backend.api.v1.helpers import _get_db_session

router = APIRouter(prefix="/api/v1")


@router.get("/metrics/scoreboard/corps")
def api_metrics_corps_scoreboard(
    period_days: int = 7,
    limit: int = 20,
):
    """Corps scoreboard: rank corps by composite score."""
    from backend.models.corps import Corps, CorpsStatus
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.rep import Rep, RepStatus
    from backend.models.segment import Segment
    from backend.models.show import Show

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=period_days)

        corps_list = (
            db.query(Corps)
            .filter(Corps.status.in_([CorpsStatus.WINTER_CAMPS, CorpsStatus.ON_TOUR]))
            .all()
        )

        scores = []
        for corps in corps_list:
            sessions = (
                db.query(AgentSession)
                .filter(
                    AgentSession.corps_id == corps.id,
                    AgentSession.started_at >= cutoff,
                )
                .all()
            )
            total_sessions = len(sessions)
            completed_sessions = sum(1 for s in sessions if s.status == SessionStatus.COMPLETED)
            failed_sessions = sum(1 for s in sessions if s.status == SessionStatus.FAILED)

            show = db.query(Show).filter(Show.corps_id == corps.id).first()
            total_reps = 0
            completed_reps = 0
            failed_reps = 0
            if show and show.segment_root_id:
                all_reps = (
                    db.query(Rep)
                    .join(Segment)
                    .filter(Rep.created_at >= cutoff)
                    .all()
                )
                total_reps = len(all_reps)
                completed_reps = sum(1 for r in all_reps if r.status == RepStatus.COMPLETED)
                failed_reps = sum(1 for r in all_reps if r.status == RepStatus.FAILED)

            completion = (completed_reps / max(total_reps, 1)) * 100
            throughput = min(completed_sessions / max(1, period_days), 100)
            efficiency = (completed_sessions / max(total_sessions, 1)) * 100
            error_penalty = (1 - (failed_sessions + failed_reps) / max(total_sessions + total_reps, 1)) * 100

            composite = (
                0.40 * completion
                + 0.30 * throughput
                + 0.20 * efficiency
                + 0.10 * error_penalty
            )

            scores.append({
                "corps_id": corps.id,
                "corps_name": corps.name,
                "corps_status": corps.status.value,
                "composite_score": round(composite, 2),
                "completion_score": round(completion, 2),
                "throughput_score": round(throughput, 2),
                "efficiency_score": round(efficiency, 2),
                "error_penalty_score": round(error_penalty, 2),
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "failed_sessions": failed_sessions,
                "total_reps": total_reps,
                "completed_reps": completed_reps,
                "failed_reps": failed_reps,
                "period_days": period_days,
            })

        scores.sort(key=lambda x: x["composite_score"], reverse=True)
        for rank, s in enumerate(scores[:limit], 1):
            s["rank"] = rank

        return {
            "period_days": period_days,
            "generated_at": now.isoformat(),
            "scoreboard": scores[:limit],
        }
    finally:
        db.close()


@router.get("/metrics/scoreboard/agents")
def api_metrics_agent_leaderboard(
    corps_id: Optional[str] = None,
    period_days: int = 7,
    limit: int = 30,
):
    """Agent leaderboard: rank agents by session count and success rate."""
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=period_days)

        query = (
            db.query(AgentSession, AgentDefinition.role, AgentDefinition.nickname)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(AgentSession.started_at >= cutoff)
        )
        if corps_id:
            query = query.filter(AgentSession.corps_id == corps_id)

        buckets: dict[tuple, dict] = {}
        for session, role, nickname in query.all():
            key = (role, nickname, session.corps_id)
            if key not in buckets:
                buckets[key] = {"total": 0, "completed": 0, "failed": 0}
            buckets[key]["total"] += 1
            if session.status == SessionStatus.COMPLETED:
                buckets[key]["completed"] += 1
            elif session.status == SessionStatus.FAILED:
                buckets[key]["failed"] += 1

        leaders = []
        for (role, nickname, cid), counts in buckets.items():
            total = counts["total"]
            completed = counts["completed"]
            failed = counts["failed"]
            success_rate = (completed / max(total, 1)) * 100

            leaders.append({
                "role": role,
                "nickname": nickname,
                "corps_id": cid,
                "total_sessions": total,
                "completed_sessions": completed,
                "failed_sessions": failed,
                "success_rate": round(success_rate, 1),
                "period_days": period_days,
            })

        leaders.sort(key=lambda x: (-x["completed_sessions"], -x["success_rate"]))
        for rank, l in enumerate(leaders[:limit], 1):
            l["rank"] = rank

        return {
            "period_days": period_days,
            "corps_id": corps_id,
            "generated_at": now.isoformat(),
            "leaderboard": leaders[:limit],
        }
    finally:
        db.close()


@router.get("/metrics/bottlenecks")
def api_metrics_bottlenecks(
    corps_id: Optional[str] = None,
    period_days: int = 7,
):
    """Detect bottlenecks: roles and operations exceeding p95 latency thresholds."""
    from backend.services.metrics import MetricsCollector, MetricType
    from backend.models.agent_session import AgentSession, SessionStatus
    from backend.models.agent_definition import AgentDefinition

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=period_days)

        latency_bottlenecks = []
        try:
            collector = MetricsCollector(db)
            latency_types = [MetricType.QUERY_LATENCY, MetricType.TASK_LATENCY]
            for lt in latency_types:
                percs = collector.get_latency_percentiles(lt, start_time=cutoff, corps_id=corps_id)
                if percs["count"] > 0:
                    latency_bottlenecks.append({
                        "metric": lt.value,
                        "count": percs["count"],
                        "p50_ms": round(percs["p50"] or 0, 2),
                        "p95_ms": round(percs["p95"] or 0, 2),
                        "p99_ms": round(percs["p99"] or 0, 2),
                        "max_ms": round(percs["max"] or 0, 2),
                    })
        except Exception:
            pass

        sessions = (
            db.query(AgentSession, AgentDefinition.role)
            .join(AgentDefinition, AgentSession.definition_id == AgentDefinition.id)
            .filter(
                AgentSession.started_at >= cutoff,
                AgentSession.ended_at.isnot(None),
            )
        )
        if corps_id:
            sessions = sessions.filter(AgentSession.corps_id == corps_id)

        role_durations: dict[str, list[float]] = {}
        for session, role in sessions.all():
            if session.started_at and session.ended_at:
                dur = (session.ended_at - session.started_at).total_seconds()
                role_durations.setdefault(role, []).append(dur)

        role_bottlenecks = []
        for role, durations in role_durations.items():
            durations.sort()
            n = len(durations)
            if n < 3:
                continue
            p50_idx = int(0.5 * (n - 1))
            p95_idx = int(0.95 * (n - 1))
            role_bottlenecks.append({
                "role": role,
                "session_count": n,
                "p50_duration_s": round(durations[p50_idx], 1),
                "p95_duration_s": round(durations[p95_idx], 1),
                "max_duration_s": round(durations[-1], 1),
                "mean_duration_s": round(sum(durations) / n, 1),
            })

        role_bottlenecks.sort(key=lambda x: x["p95_duration_s"], reverse=True)

        return {
            "period_days": period_days,
            "corps_id": corps_id,
            "generated_at": now.isoformat(),
            "latency_bottlenecks": latency_bottlenecks,
            "role_bottlenecks": role_bottlenecks,
        }
    finally:
        db.close()


@router.get("/metrics/trends")
def api_metrics_trends(
    metric_type: Optional[str] = None,
    corps_id: Optional[str] = None,
    period_days: int = 7,
):
    """Get velocity trends for metrics over time."""
    from backend.services.metrics import MetricType
    from backend.services.metrics_aggregation import MetricsAggregator

    db = _get_db_session()
    try:
        aggregator = MetricsAggregator(db)
        types_to_query = [metric_type] if metric_type else [mt.value for mt in MetricType]

        trends = []
        try:
            for mt in types_to_query:
                trend = aggregator.calculate_trends(
                    metric_type=mt,
                    period_days=period_days,
                    corps_id=corps_id,
                )
                if trend:
                    trends.append({
                        "metric_type": trend.metric_type,
                        "period_days": trend.period_days,
                        "avg_value": round(trend.avg_value, 4) if trend.avg_value else None,
                        "prev_period_avg": round(trend.prev_period_avg, 4) if trend.prev_period_avg else None,
                        "rate_of_change": round(trend.rate_of_change, 2) if trend.rate_of_change else None,
                        "direction": trend.trend_direction,
                        "corps_id": trend.corps_id,
                    })
        except Exception:
            pass

        return {
            "period_days": period_days,
            "corps_id": corps_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "trends": trends,
        }
    finally:
        db.close()


@router.get("/metrics/timeseries")
def api_metrics_timeseries(
    metric_types: Optional[str] = None,
    corps_id: Optional[str] = None,
    period_days: int = 7,
    granularity: str = "1h",
):
    """Get time-series metrics data for charting."""
    from backend.services.metrics import MetricType

    db = _get_db_session()
    try:
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(days=period_days)

        requested_types = []
        if metric_types:
            for mt_str in metric_types.split(","):
                mt_str = mt_str.strip().upper()
                try:
                    requested_types.append(mt_str)
                except ValueError:
                    pass

        if not requested_types:
            requested_types = [mt.value for mt in MetricType]

        granularity_map = {"1m": 60, "5m": 300, "1h": 3600, "1d": 86400}
        bucket_seconds = granularity_map.get(granularity, 3600)

        timeseries_data = []
        try:
            from backend.models.metrics import MetricsEvent

            query = db.query(MetricsEvent).filter(
                MetricsEvent.recorded_at >= start_time,
                MetricsEvent.metric_type.in_(requested_types),
            )
            if corps_id:
                query = query.filter(MetricsEvent.corps_id == corps_id)

            events = query.all()

            buckets = {}
            for event in events:
                timestamp_seconds = int(event.recorded_at.timestamp())
                bucket_key = (timestamp_seconds // bucket_seconds) * bucket_seconds
                bucket_ts = datetime.fromtimestamp(bucket_key, tz=timezone.utc).isoformat()

                if bucket_ts not in buckets:
                    buckets[bucket_ts] = {"timestamp": bucket_ts}

                metric_key = event.metric_type
                if metric_key not in buckets[bucket_ts]:
                    buckets[bucket_ts][metric_key] = 0
                buckets[bucket_ts][metric_key] += 1

            timeseries_data = sorted(buckets.values(), key=lambda x: x["timestamp"])

        except Exception:
            pass

        return {
            "period_days": period_days,
            "granularity": granularity,
            "corps_id": corps_id,
            "metric_types": requested_types,
            "generated_at": now.isoformat(),
            "data": timeseries_data,
        }
    finally:
        db.close()
