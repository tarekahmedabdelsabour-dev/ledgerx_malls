"""Rent and charge arithmetic for mall leases. Pure functions (no database) so every rule is unit tested."""
import calendar
from datetime import date, timedelta


def r2(x):
	return round(float(x) + (1e-9 if x >= 0 else -1e-9), 2)


def month_start(d):
	return date(d.year, d.month, 1)


def month_end(d):
	return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def add_months(d, n):
	m = d.month - 1 + n
	y = d.year + m // 12
	return date(y, m % 12 + 1, 1)


def lease_years(start, d):
	"""Whole lease years elapsed on day d (0 in the first year, 1 from the first anniversary...)."""
	if d < start:
		return 0
	n = d.year - start.year
	if (d.month, d.day) < (start.month, start.day):
		n -= 1
	return max(n, 0)


def _free(d, free_periods, kind):
	for f in free_periods or []:
		if f["from"] <= d <= f["to"] and f.get("applies", "All") in ("All", kind):
			return True
	return False


def monthly_charge(base, escalation_pct, start, end, month, free_periods=(), kind="Rent"):
	"""Amount due for one calendar month, computed day by day: a day counts when the lease is in force and not rent-free,
	and is worth base * (1 + escalation) ^ (lease years elapsed) / days in the month. A full month of a lease without escalation
	or free days is exactly `base`; a part month is pro-rated by days, including a lease that ends or is terminated mid-month."""
	first, last = month_start(month), month_end(month)
	n = (last - first).days + 1
	total = 0.0
	esc = float(escalation_pct or 0) / 100.0
	d = max(first, start)
	stop = min(last, end) if end else last
	while d <= stop:
		if not _free(d, free_periods, kind):
			total += float(base) * (1 + esc) ** lease_years(start, d) / n
		d += timedelta(days=1)
	return r2(total)


def percentage_rent(model, pct, sales, base_rent_billed):
	"""Turnover rent for a month of sales.
	Fixed: none. Percentage of Sales: pct of sales. Higher of Fixed and Percentage: only what pct of sales exceeds the base rent billed."""
	if not sales or sales <= 0 or not pct:
		return 0.0
	due = float(sales) * float(pct) / 100.0
	if model == "Percentage of Sales":
		return r2(due)
	if model == "Higher of Fixed and Percentage":
		return r2(max(0.0, due - float(base_rent_billed or 0)))
	return 0.0


def base_rent_applies(model):
	"""A pure turnover lease has no fixed rent."""
	return model != "Percentage of Sales"


def late_fee(outstanding, due_date, grace_days, through, monthly_pct, already_through=None):
	"""Simple daily late fee: outstanding * monthly% / 30 for each day past the due date plus the grace days.
	`already_through` is the date up to which fees were charged before, so a fee is never charged twice for the same day."""
	if outstanding <= 0 or not monthly_pct:
		return 0.0, None
	begin = due_date + timedelta(days=int(grace_days or 0))
	if already_through and already_through > begin:
		begin = already_through
	days = (through - begin).days
	if days <= 0:
		return 0.0, None
	return r2(outstanding * float(monthly_pct) / 100.0 / 30.0 * days), through
