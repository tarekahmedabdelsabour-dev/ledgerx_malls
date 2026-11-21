# Install

```bash
cd ~/frappe-bench-v16
git clone <repo-url> apps/ledgerx_malls
printf '\nledgerx_malls\n' >> sites/apps.txt
./env/bin/pip install -e apps/ledgerx_malls
ln -sfn ~/frappe-bench-v16/apps/ledgerx_malls/ledgerx_malls/public sites/assets/ledgerx_malls
bench --site mysite.localhost install-app ledgerx_malls
bench --site mysite.localhost migrate
bench --site mysite.localhost clear-cache
```
Then restart and hard-refresh (Ctrl+Shift+R).

## First day
1. Mall Settings: company, billing items, due days, late fee.
2. Create the Mall, Floors, Units.
3. Create a Mall Tenant, then a Mall Lease and submit it.
4. Enter meter readings and Tenant Sales (verify them).
5. Mall Billing Run: Prepare, Create Invoices, Submit Invoices.
