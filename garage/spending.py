from calendar import month_name, month_abbr, monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import ExtractMonth
from django.utils.timezone import localdate

from .models import Maintenance, Motorcycle


# Add up each month's service costs for the selected year and motorcycle.
def get_spending_data(year_value="", motorcycle_id=""):
    current_year = localdate().year
    record_dates = Maintenance.objects.dates("service_date", "year")
    years = sorted({current_year, *(day.year for day in record_dates)}, reverse=True)

    year = current_year
    if year_value.isascii() and year_value.isdigit() and len(year_value) <= 4:
        requested_year = int(year_value)
        if requested_year in years:
            year = requested_year

    selected_bike = ""
    if motorcycle_id.isascii() and motorcycle_id.isdigit() and len(motorcycle_id) <= 18:
        if Motorcycle.objects.filter(pk=int(motorcycle_id)).exists():
            selected_bike = str(int(motorcycle_id))

    services = Maintenance.objects.filter(service_date__year=year)
    if selected_bike:
        services = services.filter(motorcycle_id=selected_bike)

    # Group the database records by month instead of adding them in the browser.
    monthly_totals = (
        services.order_by()
        .annotate(month=ExtractMonth("service_date"))
        .values("month")
        .annotate(total=Sum("cost"), count=Count("id"))
        .order_by("month")
    )
    totals_by_month = {record["month"]: record for record in monthly_totals}

    # Include empty months so the chart always shows the full year.
    months = []
    for number in range(1, 13):
        record = totals_by_month.get(number, {})
        months.append(
            {
                "name": month_name[number],
                "label": month_abbr[number],
                "total": record.get("total", Decimal("0.00")),
                "count": record.get("count", 0),
                "start": date(year, number, 1).isoformat(),
                "end": date(year, number, monthrange(year, number)[1]).isoformat(),
            }
        )

    total = sum((month["total"] for month in months), Decimal("0.00"))
    highest = max(month["total"] for month in months)
    for month in months:
        # Scale each bar to the highest cost and keep zero-cost months flat.
        height = month["total"] / highest * 100 if highest else 0
        month["height"] = f"{height:.4f}"

    peak_months = [month["name"] for month in months if month["total"] == highest]
    peak_label = "No spending yet"
    if highest:
        peak_label = peak_months[0] if len(peak_months) == 1 else "Multiple months tied"

    return {
        "year": year,
        "years": years,
        "selected_bike": selected_bike,
        "months": months,
        "total": total,
        "average": total / 12,
        "highest": highest,
        "midpoint": highest / 2,
        "peak_label": peak_label,
        "count": sum(month["count"] for month in months),
    }
