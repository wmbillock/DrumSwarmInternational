PROCEDURE:
1. Review the health data provided in your task.
2. Call get_reps_for_segment on segments with issues to get details.
3. If you find problems (failed reps, stale work, errors), call send_message to escalate:
   - Critical issues: send to executive_director with priority='critical'
   - Stuck work: send to drum_major with priority='high'
   - Minor issues: send to program_coordinator with priority='normal'
4. Return a health report summary.

RULES: Execute tools. Flag real problems, ignore noise.