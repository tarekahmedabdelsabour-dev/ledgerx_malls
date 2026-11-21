"""Common-area expense recovery: split a total between tenants by leased area."""


def split_exact(total, weights):
	"""Splits `total` in proportion to `weights` in whole cents. The parts always add up to the total (largest remainder)."""
	cents = int(round(total * 100))
	w = [max(float(x), 0.0) for x in weights]
	s = sum(w)
	if s <= 0 or not w:
		return [0.0] * len(w)
	raw = [cents * x / s for x in w]
	base = [int(r) for r in raw]
	left = cents - sum(base)
	order = sorted(range(len(w)), key=lambda i: (-(raw[i] - base[i]), i))
	for i in order[:left]:
		base[i] += 1
	return [b / 100.0 for b in base]


def cam_shares(total, areas, vacant_area=0.0, landlord_bears_vacant=True):
	"""areas: leased areas of the tenants. Returns (tenant_amounts, landlord_amount).
	When the landlord bears the vacant space, the total is split over the whole lettable area and the vacant share stays with the landlord;
	otherwise tenants carry everything."""
	if landlord_bears_vacant and vacant_area > 0:
		parts = split_exact(total, list(areas) + [vacant_area])
		return parts[:-1], round(parts[-1], 2)
	return split_exact(total, areas), 0.0
