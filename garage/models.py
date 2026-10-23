from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# Store the basic details and current mileage for each motorcycle.
class Motorcycle(models.Model):
    make = models.CharField(max_length=80)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(1885), MaxValueValidator(2100)]
    )
    current_mileage = models.PositiveIntegerField(default=0)
    nickname = models.CharField(max_length=80, blank=True)
    vin = models.CharField("VIN", max_length=17, blank=True)

    class Meta:
        ordering = ["make", "model"]

    # Use the nickname when available so the bike is easy to find.
    def __str__(self):
        return self.nickname or f"{self.year} {self.make} {self.model}"


# Link each maintenance record to the motorcycle it belongs to.
class Maintenance(models.Model):
    motorcycle = models.ForeignKey(
        Motorcycle, on_delete=models.CASCADE, related_name="services"
    )
    service_type = models.CharField(max_length=100)
    service_date = models.DateField()
    mileage = models.PositiveIntegerField()
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-service_date", "-id"]
