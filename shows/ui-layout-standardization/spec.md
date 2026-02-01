# UI Layout Standardization

## Goal
Establish consistent page layout patterns across all frontend pages.

## Deliverables

### 1. Page Container Pattern
- Every page uses a consistent outer wrapper class (`page-content`)
- Standard max-width and padding applied via CSS, not inline styles
- Remove ad-hoc `style={{ marginTop, padding }}` from page roots

### 2. Page Headers
- Every page gets a `<div className="page-header">` with:
  - Back button (where applicable — detail pages)
  - `<h1 className="page-title">` or `<h2>` for detail views
  - Optional status badge inline with title
- Remove inconsistent header patterns (some use h1, some h2, some divs)

### 3. Back Navigation
- All detail pages (CorpsDetailV2, SeasonWorkshop detail, RunDetail, etc.) have a back button
- Back button navigates to the parent list page
- Consistent placement: top-left of page header

### 4. Summary Bar
- Pages with aggregate stats use the `summary-bar` pattern (see SeasonWorkshop, CommandCenter)
- Standardize: stat value + label, horizontal flex layout, consistent sizing

## Pages to Update
- CommandCenter (already mostly correct — baseline reference)
- CorpsList, CorpsDetailV2
- ShowLibrary
- SeasonWorkshop (already has good patterns)
- TourDashboard, CompetitionLive
- Finals, SeasonReview
- Performers, StaffMarketplace
- ScoreboardsPage
- MessageInbox, MessageArchive
- SystemHealth

## Acceptance Criteria
- All pages follow the same header → content → footer structure
- No inline style for layout concerns that should be in CSS
- Visual consistency when navigating between pages
