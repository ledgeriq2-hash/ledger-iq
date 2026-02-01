# Sprint UI Invoice Report 1

## Summary
- Rebuilt the dashboard invoices page with a premium hero, status summary cards, search + segmented status filters, and a refreshed table that surfaces friendly invoice IDs and better total/status columns.
- Added reusable UI helpers (`ToggleGroup`, `DropdownMenu`, `Dialog`) plus shared layout styles so the new filters, actions, and confirmation flows stay consistent.
- Simplified actions into a contextual primary button plus a safer kebab menu, introduced delete confirmations, loading skeletons, and an empty state with a “New Invoice” CTA.
- Wrapped the invoice “Post” flow in a try/catch so backend 422s no longer log uncaught promise errors and now show a dialog guiding users to the Settings page when `account_mapping_missing` prevents posting, while other errors surface via toast.
- Ensured the “Post” button’s click handler now `await`s the async helper (which already awaits the mutation) so the rejection is captured and no longer surfaces as “Uncaught (in promise)” in the console.

## Testing
1. `cd frontend`
2. `npm install` (if dependencies are missing)
3. `npm run lint`
4. `npm run build`
5. Simulate `POST /api/v1/invoices/:id/post` returning `422` with `{ code: "account_mapping_missing" }`, then click any invoice’s Post button to confirm the Account Mapping dialog appears and “Open Settings” navigates to `/settings`.
