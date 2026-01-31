PROCEDURE:
1. Call get_segment_children using the root segment ID provided in your task.
2. For each segment, call get_reps_for_segment to check rep statuses.
3. If reps are stuck (assigned but not progressing), send_message to the assigned role.
4. If reps are in review, transition them to completed or failed based on quality.
5. Report status summary.

RULES:
- You MUST call tools to check status. Do not guess.
- Send escalation messages for blocked work.