PROCEDURE:
1. Call get_segment_children using the root segment ID provided in your task.
2. For each movement, create SET segments underneath it (type='set').
3. For each set, create leaf COORDINATE nodes (type='segment') for specific tasks.
4. For each leaf segment, call create_rep to create a work unit.
5. Call handoff to the appropriate caption head or designer with the segment IDs and instructions.
6. Return a summary of the work breakdown.

RULES:
- Create reps for every leaf segment — reps are the actual work units.
- Be specific in handoff instructions: include segment IDs and expected deliverables.