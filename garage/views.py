from datetime import date

from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MaintenanceForm, MotorcycleForm
from .models import Maintenance, Motorcycle
from .spending import get_spending_data


# Convert the date filter to a date, or ignore it if it is not valid.
def read_date_filter(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# Show the motorcycles, filtered service history, and maintenance totals.
def dashboard(request):
    bikes = Motorcycle.objects.all()
    services = Maintenance.objects.select_related("motorcycle")

    search_query = request.GET.get("q", "").strip()
    motorcycle_id = request.GET.get("bike", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")

    # Search both the service name and the notes entered by the user.
    if search_query:
        services = services.filter(
            Q(service_type__icontains=search_query) | Q(notes__icontains=search_query)
        )

    if motorcycle_id.isdigit():
        services = services.filter(motorcycle_id=motorcycle_id)

    start_date = read_date_filter(start)
    end_date = read_date_filter(end)
    if start_date:
        services = services.filter(service_date__gte=start_date)
    if end_date:
        services = services.filter(service_date__lte=end_date)

    # Keep the overview totals based on all records, even when filters are used.
    total_cost = Maintenance.objects.aggregate(total=Sum("cost"))["total"] or 0
    context = {
        "bikes": bikes,
        "services": services,
        "total": total_cost,
        "count": Maintenance.objects.count(),
        "q": search_query,
        "selected": motorcycle_id,
        "start": start,
        "end": end,
        "spending": get_spending_data(
            request.GET.get("chart_year", ""),
            request.GET.get("chart_bike", ""),
        ),
    }
    return render(request, "garage/dashboard.html", context)


# Use the same page to add a new record or edit an existing one.
def edit(request, kind, pk=None):
    if kind == "bike":
        model = Motorcycle
        form_class = MotorcycleForm
        record_name = "motorcycle"
    else:
        model = Maintenance
        form_class = MaintenanceForm
        record_name = "maintenance record"

    instance = None
    if pk:
        instance = get_object_or_404(model, pk=pk)

    initial_data = {}
    if kind == "service" and not pk:
        initial_data = {
            "motorcycle": request.GET.get("bike"),
            "service_date": date.today(),
        }

    form = form_class(
        request.POST or None,
        instance=instance,
        initial=initial_data,
    )

    if request.method == "POST" and form.is_valid():
        # Save the service and its mileage update together in the database.
        with transaction.atomic():
            item = form.save()
            if kind == "service":
                # Raise the bike's mileage only when the new reading is higher.
                Motorcycle.objects.filter(
                    pk=item.motorcycle_id,
                    current_mileage__lt=item.mileage,
                ).update(current_mileage=item.mileage)
        return redirect("dashboard")

    action = "Edit" if pk else "Add"
    context = {"form": form, "title": f"{action} {record_name}"}
    return render(request, "garage/form.html", context)


# Show a confirmation page and delete the record when its form is submitted.
def delete(request, kind, pk):
    model = Motorcycle if kind == "bike" else Maintenance
    item = get_object_or_404(model, pk=pk)

    if request.method == "POST":
        item.delete()
        return redirect("dashboard")

    context = {"item": item, "kind": kind}
    return render(request, "garage/delete.html", context)
