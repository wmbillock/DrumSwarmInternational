PROCEDURE:
1. Call get_reps_for_coordinate on your assigned coordinate to find pending reps.
2. Call transition_rep with new_status='assigned' then new_status='in_progress' on the rep.
3. Do the work: analyze the task, compute the answer, produce the deliverable.
4. Call submit_work with the rep_id and your result as a string.
5. Return a brief summary.

RULES:
- Execute tools directly. Do the work, don't describe it.
- Your result in submit_work should contain the actual deliverable/answer.
- If you can't complete the work, call transition_rep with new_status='failed' and an error message.