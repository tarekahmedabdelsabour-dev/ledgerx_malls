from frappe import _


def _group(data, label, items, fields=None):
	data.setdefault("transactions", []).append({"label": _(label), "items": items})
	if fields:
		data.setdefault("non_standard_fieldnames", {}).update(fields)
	return data


def customer(data=None):
	return _group(data or {}, "Mall", ["Mall Tenant"], {"Mall Tenant": "customer"})


def employee(data=None):
	return _group(data or {}, "Mall", ["Mall"], {"Mall": "manager"})

