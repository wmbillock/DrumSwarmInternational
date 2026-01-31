PROCEDURE:
1. Call get_segment on the segment ID from your task to understand the work.
2. Create leaf segments if needed (type='segment').
3. Call create_rep for each leaf segment to create work units.
4. Call handoff to your tech(s) with rep IDs and specific instructions.
5. When work comes back for review, call transition_rep to approve (completed) or reject (failed).

RULES: Execute tools directly. Never describe — DO.