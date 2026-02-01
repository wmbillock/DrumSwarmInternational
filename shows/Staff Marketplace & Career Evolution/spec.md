# Staff Marketplace & Career Evolution

## Overview

Build the staff marketplace UI and career tracking system for hiring, firing, and monitoring staff agent careers across corps.

## Acceptance Criteria

1. **Marketplace page**: List available staff with roles, skills, experience, and hiring controls.
2. **Staff profile view**: Detailed career history, performance metrics, and corps assignments.
3. **Hire/release flows**: Corps can hire available staff and release current staff back to the marketplace.
4. **Career tracking**: Display career progression, corps history, and accumulated experience for each staff member.
5. **Integration**: Connect to existing v1 endpoints (listMarketplace, getStaffProfile, hireStaff, releaseStaff).

## Constraints

- Use v1.ts API client exclusively
- Staff hiring/release must respect corps lifecycle (only in WINTER_CAMPS or ON_TOUR)
- Follow existing frontend component patterns

## Deliverables

- StaffMarketplace.tsx page with search/filter
- StaffProfile.tsx detail view
- Hire/release action modals
- Career timeline visualization
