"""Measures managers read: occupancy, weighted lease expiry, occupancy cost, overlapping leases."""
from datetime import date


def occupancy_pct(occupied_area, total_area):
	return round(occupied_area / total_area * 100.0, 2) if total_area else 0.0


def wale_years(leases, today):
	"""Weighted average lease expiry in years. leases: list of (end_date, weight) - weight is the rent or the area. Expired leases count as 0 years left."""
	tw = sum(w for _e, w in leases if w > 0)
	if tw <= 0:
		return 0.0
	return round(sum(w * max((e - today).days, 0) / 365.25 for e, w in leases if w > 0) / tw, 2)


def occupancy_cost_ratio(rent, service, sales):
	"""What the tenant pays the mall as a percentage of its sales. None when there are no sales."""
	if not sales or sales <= 0:
		return None
	return round((rent + service) / sales * 100.0, 2)


def sales_per_sqm(sales, area):
	return round(sales / area, 2) if area else 0.0


def overlaps(a_start, a_end, b_start, b_end):
	"""Two date ranges (an empty end means open-ended) share at least one day."""
	far = date.max
	return a_start <= (b_end or far) and b_start <= (a_end or far)


def bucket_of(days_overdue, edges=(30, 60, 90)):
	if days_overdue <= 0:
		return "Not Due"
	for e in edges:
		if days_overdue <= e:
			return f"1-{e}" if e == edges[0] else f"{edges[edges.index(e) - 1] + 1}-{e}"
	return f"Over {edges[-1]}"
