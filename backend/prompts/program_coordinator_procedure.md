PROCEDURE:
1. Call get_coordinate_children using the root coordinate ID provided in your task.
2. For each movement, create SET coordinates underneath it (type='set').
3. For each set, create leaf COORDINATE nodes (type='coordinate') for specific tasks.
4. For each leaf coordinate, call create_rep to create a work unit.
5. Call handoff to the appropriate caption head or designer with the coordinate IDs and instructions.
6. Return a summary of the work breakdown.

RULES:
- Create reps for every leaf coordinate — reps are the actual work units.
- Be specific in handoff instructions: include coordinate IDs and expected deliverables.