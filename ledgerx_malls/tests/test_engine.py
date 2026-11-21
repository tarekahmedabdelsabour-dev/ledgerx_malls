import random
import unittest
from datetime import date, timedelta

from ledgerx_malls.engine import billing as b
from ledgerx_malls.engine import cam, stats


class TestRent(unittest.TestCase):
	def test_full_month_is_exact(self):
		for m in (date(2026, 2, 1), date(2026, 3, 1), date(2026, 11, 1)):
			self.assertEqual(b.monthly_charge(10000, 0, date(2025, 1, 1), date(2030, 1, 1), m), 10000.0)

	def test_part_month_start(self):
		# lease starts the 16th of a 30-day month: 15 of 30 days
		self.assertEqual(b.monthly_charge(3000, 0, date(2026, 11, 16), date(2030, 1, 1), date(2026, 11, 1)), 1500.0)

	def test_end_mid_month(self):
		self.assertEqual(b.monthly_charge(3000, 0, date(2025, 1, 1), date(2026, 11, 10), date(2026, 11, 1)), 1000.0)
		self.assertEqual(b.monthly_charge(3000, 0, date(2025, 1, 1), date(2026, 11, 10), date(2026, 12, 1)), 0.0)

	def test_free_period_applies_by_kind(self):
		free = [{"from": date(2026, 11, 1), "to": date(2026, 11, 15), "applies": "Rent"}]
		self.assertEqual(b.monthly_charge(3000, 0, date(2026, 11, 1), None, date(2026, 11, 1), free, "Rent"), 1500.0)
		self.assertEqual(b.monthly_charge(3000, 0, date(2026, 11, 1), None, date(2026, 11, 1), free, "Service Charge"), 3000.0)
		free_all = [{"from": date(2026, 11, 1), "to": date(2026, 11, 30), "applies": "All"}]
		self.assertEqual(b.monthly_charge(3000, 0, date(2026, 11, 1), None, date(2026, 11, 1), free_all, "Service Charge"), 0.0)

	def test_escalation_on_anniversary(self):
		start = date(2025, 1, 1)
		self.assertEqual(b.monthly_charge(1000, 10, start, None, date(2025, 12, 1)), 1000.0)
		self.assertEqual(b.monthly_charge(1000, 10, start, None, date(2026, 1, 1)), 1100.0)
		self.assertEqual(b.monthly_charge(1000, 10, start, None, date(2027, 1, 1)), 1210.0)
		# anniversary in the middle of a 30-day month (15 Nov): 14 days at old rate, 16 at new
		s2 = date(2025, 11, 15)
		self.assertEqual(b.monthly_charge(3000, 10, s2, None, date(2026, 11, 1)), round(3000 * 14 / 30 + 3300 * 16 / 30, 2))

	def test_no_negative_and_monotonic(self):
		rnd = random.Random(4)
		for _ in range(300):
			start = date(2025, 1, 1) + timedelta(days=rnd.randint(0, 800))
			end = start + timedelta(days=rnd.randint(30, 1500))
			m = b.month_start(start + timedelta(days=rnd.randint(0, 1500)))
			base = rnd.randint(500, 9000)
			v = b.monthly_charge(base, rnd.choice([0, 5, 10]), start, end, m)
			self.assertGreaterEqual(v, 0)
			self.assertLessEqual(v, base * 1.6)
			no_free = b.monthly_charge(base, 0, start, end, m)
			free = b.monthly_charge(base, 0, start, end, m, [{"from": start, "to": end, "applies": "All"}])
			self.assertEqual(free, 0.0)
			self.assertLessEqual(no_free, base)

	def test_months_cover_lease_total(self):
		# a lease over whole months with a mid-month start bills exactly the days it is in force
		start, end = date(2026, 1, 10), date(2026, 6, 20)
		tot, m = 0.0, date(2026, 1, 1)
		while m <= end:
			tot += b.monthly_charge(3100, 0, start, end, m)
			m = b.add_months(m, 1)
		self.assertAlmostEqual(tot, sum(3100 / 31 if d.month in (1, 3, 5) else 3100 / (30 if d.month in (4, 6) else 28) for d in (start + timedelta(days=i) for i in range((end - start).days + 1))), delta=0.1)


class TestPercentage(unittest.TestCase):
	def test_models(self):
		self.assertEqual(b.percentage_rent("Fixed", 8, 100000, 5000), 0.0)
		self.assertEqual(b.percentage_rent("Percentage of Sales", 8, 100000, 0), 8000.0)
		self.assertEqual(b.percentage_rent("Higher of Fixed and Percentage", 8, 100000, 5000), 3000.0)
		self.assertEqual(b.percentage_rent("Higher of Fixed and Percentage", 8, 50000, 5000), 0.0)
		self.assertEqual(b.percentage_rent("Higher of Fixed and Percentage", 8, 0, 5000), 0.0)
		self.assertFalse(b.base_rent_applies("Percentage of Sales"))
		self.assertTrue(b.base_rent_applies("Fixed"))

	def test_higher_of_total_is_max(self):
		rnd = random.Random(9)
		for _ in range(300):
			base, pct, s = rnd.randint(1000, 9000), rnd.choice([5, 8, 12]), rnd.randint(0, 300000)
			top = b.percentage_rent("Higher of Fixed and Percentage", pct, s, base)
			self.assertAlmostEqual(base + top, max(base, s * pct / 100), delta=0.02)


class TestLateFee(unittest.TestCase):
	def test_fee(self):
		f, thr = b.late_fee(1000, date(2026, 11, 1), 5, date(2026, 11, 26), 3)
		self.assertEqual((f, thr), (round(1000 * 3 / 100 / 30 * 20, 2), date(2026, 11, 26)))
		self.assertEqual(b.late_fee(1000, date(2026, 11, 1), 5, date(2026, 11, 5), 3)[0], 0.0)
		self.assertEqual(b.late_fee(0, date(2026, 11, 1), 5, date(2026, 12, 5), 3)[0], 0.0)

	def test_never_twice(self):
		f1, t1 = b.late_fee(1000, date(2026, 11, 1), 0, date(2026, 11, 11), 3)
		f2, _t = b.late_fee(1000, date(2026, 11, 1), 0, date(2026, 11, 21), 3, already_through=t1)
		full, _ = b.late_fee(1000, date(2026, 11, 1), 0, date(2026, 11, 21), 3)
		self.assertAlmostEqual(f1 + f2, full, delta=0.02)


class TestCam(unittest.TestCase):
	def test_exact(self):
		rnd = random.Random(1)
		for _ in range(300):
			total = round(rnd.uniform(0, 90000), 2)
			areas = [rnd.choice([20, 35, 80.5, 120]) for _i in range(rnd.randint(1, 9))]
			parts = cam.split_exact(total, areas)
			self.assertAlmostEqual(sum(parts), total, places=2)
			self.assertTrue(all(p >= 0 for p in parts))
			vac = rnd.choice([0, 50, 300])
			t, l = cam.cam_shares(total, areas, vac, True)
			self.assertAlmostEqual(sum(t) + l, total, places=2)
			if not vac:
				self.assertEqual(l, 0.0)

	def test_vacant_bears(self):
		t, l = cam.cam_shares(1000, [100, 100], 200, True)
		self.assertEqual((t, l), ([250.0, 250.0], 500.0))
		t, l = cam.cam_shares(1000, [100, 100], 200, False)
		self.assertEqual((t, l), ([500.0, 500.0], 0.0))

	def test_proportional(self):
		self.assertEqual(cam.split_exact(100, [1, 1, 1]), [33.34, 33.33, 33.33])


class TestStats(unittest.TestCase):
	def test_all(self):
		T = date(2026, 11, 20)
		self.assertEqual(stats.occupancy_pct(850, 1000), 85.0)
		self.assertEqual(stats.occupancy_pct(0, 0), 0.0)
		self.assertEqual(stats.wale_years([(T + timedelta(days=365), 100), (T - timedelta(days=5), 100)], T), 0.5)
		self.assertEqual(stats.occupancy_cost_ratio(8000, 2000, 100000), 10.0)
		self.assertIsNone(stats.occupancy_cost_ratio(8000, 2000, 0))
		self.assertEqual(stats.sales_per_sqm(50000, 100), 500.0)

	def test_overlaps(self):
		d = date
		self.assertTrue(stats.overlaps(d(2026, 1, 1), d(2026, 12, 31), d(2026, 12, 31), None))
		self.assertFalse(stats.overlaps(d(2026, 1, 1), d(2026, 12, 30), d(2026, 12, 31), None))
		self.assertTrue(stats.overlaps(d(2026, 1, 1), None, d(2030, 1, 1), d(2031, 1, 1)))

	def test_bucket(self):
		self.assertEqual(stats.bucket_of(0), "Not Due")
		self.assertEqual(stats.bucket_of(10), "1-30")
		self.assertEqual(stats.bucket_of(45), "31-60")
		self.assertEqual(stats.bucket_of(75), "61-90")
		self.assertEqual(stats.bucket_of(200), "Over 90")


if __name__ == "__main__":
	unittest.main()
