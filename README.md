# LedgerX Malls

Commercial mall management: units, tenants, leases, rent billing and collection, service charges and utilities, tenant sales and footfall.

## What it covers
- **Property**: Mall, Floors, Units (status follows the lease), categories.
- **Tenants and leases**: auto customer account, submittable Mall Lease with fixed rent, percentage of sales, or the higher of both; yearly escalation; rent-free periods; deposit; terminate and renew; overlap protection.
- **Billing**: Mall Billing Run prepares lines (rent, service charge, marketing fund, turnover rent from verified sales, utilities, CAM reconciliation, late fees) then creates draft Sales Invoices per lease.
- **Service charges**: CAM Allocation splits common-area expenses by area x days.
- **Utilities**: meters and readings billed once.
- **Tenant sales and footfall**: Declared / Verified sales, sales per sqm, occupancy cost ratio.
- **Reports**: Rent Roll, Occupancy, Tenant Aging, Tenant Sales Performance, Lease Expiry, Footfall and Sales, Billing and Collection.
- **Roles**: Mall Manager, Leasing Officer, Mall Accountant, Mall Operations.

## Status
Calculation engines are unit tested (17 tests). Database code was written against the v16 source but has not yet been run on a live site: test on a copy first.

See `docs/INSTALL.md`.
