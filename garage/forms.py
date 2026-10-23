from django import forms
from .models import Motorcycle, Maintenance


# Build the motorcycle form using the fields from its database model.
class MotorcycleForm(forms.ModelForm):
    class Meta:
        model = Motorcycle
        fields = ["make", "model", "year", "current_mileage", "nickname", "vin"]
        help_texts = {"vin": "Vehicle identification number, up to 17 characters."}
        widgets = {"vin": forms.TextInput(attrs={"autocapitalize": "characters"})}

    # Save the VIN in uppercase and remove spaces from its ends.
    def clean_vin(self):
        return self.cleaned_data["vin"].strip().upper()


# Build the service form with a date picker and a larger notes box.
class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = [
            "motorcycle",
            "service_type",
            "service_date",
            "mileage",
            "cost",
            "notes",
        ]
        widgets = {
            "service_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
