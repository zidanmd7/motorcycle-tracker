from django.test import TestCase, Client
from .models import Motorcycle, Maintenance


class GarageTests(TestCase):
    # Check that services can be saved, searched, edited, and deleted.
    def test_service_search_edit_delete(self):
        bike = Motorcycle.objects.create(
            make="Honda", model="CB500F", year=2022, current_mileage=100
        )
        data = {
            "motorcycle": bike.pk,
            "service_type": "Oil change",
            "service_date": "2026-10-22",
            "mileage": 500,
            "cost": "45.50",
            "notes": "Filter replaced",
        }
        self.assertEqual(self.client.post("/service/new/", data).status_code, 302)
        bike.refresh_from_db()
        self.assertEqual(bike.current_mileage, 500)
        self.assertContains(self.client.get("/?q=oil"), "Oil change")
        self.assertNotContains(self.client.get("/?start=2026-10-23"), "Oil change")
        record = Maintenance.objects.get()
        data["service_type"] = "Brakes"
        self.client.post(f"/service/{record.pk}/edit/", data)
        record.refresh_from_db()
        self.assertEqual(record.service_type, "Brakes")
        self.client.get(f"/service/{record.pk}/delete/")
        self.assertEqual(Maintenance.objects.count(), 1)
        self.client.post(f"/service/{record.pk}/delete/")
        self.assertEqual(Maintenance.objects.count(), 0)

    # Check motorcycle changes, invalid inputs, and form security.
    def test_validation_csrf_and_bike_crud(self):
        self.assertEqual(
            Client(enforce_csrf_checks=True).post("/bike/new/", {}).status_code, 403
        )
        data = {
            "make": "Yamaha",
            "model": "MT-07",
            "year": 2024,
            "current_mileage": 300,
            "nickname": "Blue",
        }
        self.client.post("/bike/new/", data)
        bike = Motorcycle.objects.get()
        data["current_mileage"] = 400
        self.client.post(f"/bike/{bike.pk}/edit/", data)
        bike.refresh_from_db()
        self.assertEqual(bike.current_mileage, 400)
        self.client.post(
            "/service/new/",
            {
                "motorcycle": bike.pk,
                "service_type": "Oil",
                "service_date": "bad",
                "mileage": -1,
                "cost": "-5",
            },
        )
        self.assertEqual(Maintenance.objects.count(), 0)
        self.assertEqual(
            self.client.get("/?start=invalid&bike=invalid").status_code, 200
        )
        self.client.post(f"/bike/{bike.pk}/delete/")
        self.assertEqual(Motorcycle.objects.count(), 0)
