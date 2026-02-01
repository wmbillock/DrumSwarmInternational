I need to clarify which show you'd like me to update. I can see from the conversation context that you've been designing the **divisions-and-competition-classes architecture**, but I don't see a specific show slug mentioned.

**Which show slug should I update the Brief for?**

Once you provide it, I'll integrate all the architectural decisions from your conversation:
- **Data Model**: divisions list in season metadata dict (key: `divisions`)
- **Default divisions**: World Class, Open Class, Div 3
- **Corps-season registration**: Optional division field at registration, mutable via PUT
- **Standings UI**: TABS (each tab shows one division, plus "All" tab with division column)
- **API contract**: Full endpoints for division management and corps registration
- **Unassigned corps**: Appear in "All" tab but not in any division tab

Then I'll write the complete spec markdown with all mandatory sections and update it via the API.

**What's the show slug?**