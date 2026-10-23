from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils.timezone import localdate

from .models import Maintenance, Motorcycle
from .spending import get_spending_data


class SpendingTests(TestCase):
    # Create a motorcycle for the spending tests without using the real database.
    def setUp(self):
        self.bike = Motorcycle.objects.create(make="Honda", model="CB500F", year=2022)

    # Add a service record with the date and cost needed by a test.
    def add_service(self, cost, service_date, motorcycle=None):
        return Maintenance.objects.create(
            motorcycle=motorcycle or self.bike,
            service_type="Oil change",
            service_date=service_date,
            mileage=500,
            cost=cost,
        )

    # Check monthly sums, empty months, and records outside the chosen year.
    def test_monthly_totals_and_date_boundaries(self):
        self.add_service("10.10", date(2024, 1, 1))
        self.add_service("20.20", date(2024, 1, 31))
        self.add_service("90.00", date(2024, 3, 12))
        self.add_service("800.00", date(2023, 12, 31))
        self.add_service("900.00", date(2025, 1, 1))

        data = get_spending_data("2024")
        self.assertEqual(data["total"], Decimal("120.30"))
        self.assertEqual(data["average"], Decimal("10.025"))
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["months"]), 12)
        self.assertEqual(data["months"][0]["total"], Decimal("30.30"))
        self.assertEqual(data["months"][1]["total"], Decimal("0.00"))
        self.assertEqual(data["months"][1]["end"], "2024-02-29")
        self.assertEqual(data["months"][11]["end"], "2024-12-31")
        self.assertEqual(data["months"][2]["height"], "100.0000")
        self.assertEqual(data["peak_label"], "March")

    # Keep spending filters separate from the journal search and filter by bike.
    def test_motorcycle_filter_and_month_links(self):
        other_bike = Motorcycle.objects.create(make="Yamaha", model="MT-07", year=2024)
        self.add_service("11.00", date(2024, 1, 4))
        self.add_service("80.00", date(2024, 1, 5), motorcycle=other_bike)
        response = self.client.get(
            "/", {"chart_year": "2024", "chart_bike": self.bike.pk, "q": "tires"}
        )
        self.assertEqual(response.context["spending"]["total"], Decimal("11.00"))
        self.assertEqual(response.context["spending"]["count"], 1)
        self.assertEqual(len(response.context["services"]), 0)
        self.assertContains(response, "start=2024-01-01&amp;end=2024-01-31#journal")
        self.assertEqual(get_spending_data("2024")["total"], Decimal("91.00"))

    # Handle empty data, free services, and invalid filter values without errors.
    def test_empty_chart_and_invalid_filters(self):
        data = get_spending_data("invalid", "999999999999999999999999")
        self.assertEqual(data["year"], localdate().year)
        self.assertEqual(data["selected_bike"], "")
        self.assertEqual(data["total"], 0)
        self.assertTrue(all(month["height"] == "0.0000" for month in data["months"]))
        self.assertContains(self.client.get("/"), "No spending recorded")

        self.add_service("0.00", localdate())
        response = self.client.get("/", {"chart_year": "9" * 200, "chart_bike": "²"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["spending"]["count"], 1)
        self.assertContains(
            response, "All recorded services for this selection cost $0.00."
        )

    # Refresh the totals after a service is edited or deleted.
    def test_chart_updates_with_service_changes(self):
        record = self.add_service("11.00", localdate())
        response = self.client.post(
            f"/service/{record.pk}/edit/",
            {
                "motorcycle": self.bike.pk,
                "service_type": "Oil change",
                "service_date": localdate().isoformat(),
                "mileage": 600,
                "cost": "36.50",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.client.get("/").context["spending"]["total"], Decimal("36.50")
        )
        self.client.post(f"/service/{record.pk}/delete/")
        self.assertEqual(self.client.get("/").context["spending"]["total"], 0)


class MotorcycleVinTests(TestCase):
    # Check that the optional VIN saves, displays, edits, and clears correctly.
    def test_optional_vin(self):
        data = {
            "make": "Honda",
            "model": "CB500F",
            "year": 2022,
            "current_mileage": 100,
        }
        self.assertEqual(self.client.post("/bike/new/", data).status_code, 302)
        bike = Motorcycle.objects.get()
        self.assertEqual(bike.vin, "")

        data["vin"] = " jh2sc5904ak000001 "
        self.client.post(f"/bike/{bike.pk}/edit/", data)
        bike.refresh_from_db()
        self.assertEqual(bike.vin, "JH2SC5904AK000001")
        self.assertContains(self.client.get("/"), bike.vin)
        self.assertContains(self.client.get(f"/bike/{bike.pk}/edit/"), bike.vin)

        data["vin"] = "A" * 18
        response = self.client.post(f"/bike/{bike.pk}/edit/", data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("vin", response.context["form"].errors)
        bike.refresh_from_db()
        self.assertEqual(bike.vin, "JH2SC5904AK000001")

        data["vin"] = ""
        self.assertEqual(
            self.client.post(f"/bike/{bike.pk}/edit/", data).status_code, 302
        )
        bike.refresh_from_db()
        self.assertEqual(bike.vin, "")
