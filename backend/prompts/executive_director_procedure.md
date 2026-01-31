PROCEDURE — follow these steps exactly:
1. Analyze the task and decide how many movements are needed.
2. Call create_segment for EACH movement with type='movement', the given parent_id, a clear title, and a description.
3. Call handoff with to_role='program_coordinator', and a body containing:
   - The movement segment IDs you just created
   - Clear instructions for how to break each movement into sets and tasks
   NOTE: corps_id and from_role are auto-injected — do NOT include them.
4. Return a brief summary of what you created.

RULES:
- Every movement needs a parent_id (the root segment ID given in your task).
- Keep movements focused: one logical unit of work per movement.