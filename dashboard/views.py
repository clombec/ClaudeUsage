"""
views.py

HTTP layer for the dashboard.
"""

from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .services import (
    EXTRA_USAGE,
    FIVE_HOUR,
    SEVEN_DAY,
    get_usage_series,
    trigger_collection,
)

# Query value -> (label shown to the user, number of days or None for all)
PERIODS = {
    "1": ("24 h", 1),
    "7": ("7 jours", 7),
    "30": ("30 jours", 30),
    "all": ("Tout", None),
}
DEFAULT_PERIOD = "7"

WINDOW_LABELS = {
    FIVE_HOUR: "5 heures",
    SEVEN_DAY: "Semaine",
    EXTRA_USAGE: "Supplément",
}

DATETIME_FORMAT = "%d/%m %H:%M"

# Banner shown after a manual refresh: query value -> (css class, French text)
REFRESH_BANNERS = {
    "ok": ("ok", "Relevé effectué."),
    "error": ("error", "Échec du relevé. Détails dans logs/collector.log (et sur Discord)."),
}


def _selected_period(value: str | None) -> str:
    """Return a valid period key, falling back to the default."""
    return value if value in PERIODS else DEFAULT_PERIOD


def _format_local(value) -> str:
    """Format an aware datetime in local time, or return a dash."""
    if value is None:
        return "—"
    return timezone.localtime(value).strftime(DATETIME_FORMAT)


@require_GET
def index(request: HttpRequest) -> HttpResponse:
    """Render the usage chart for the selected period.

    Args:
        request: Incoming request; optional "period" query parameter
            (one of PERIODS keys, defaults to 7 days).

    Returns:
        The rendered dashboard page.
    """
    period = _selected_period(request.GET.get("period"))
    _, days = PERIODS[period]
    banner = REFRESH_BANNERS.get(request.GET.get("refresh", ""))

    data = get_usage_series(days)

    periods = [
        {"key": key, "label": label, "active": key == period}
        for key, (label, _) in PERIODS.items()
    ]

    summary = []
    for window in (FIVE_HOUR, SEVEN_DAY, EXTRA_USAGE):
        info = data["latest"].get(window)
        if info is None or (window == EXTRA_USAGE and not data["show_extra"]):
            continue
        summary.append(
            {
                "css_class": window,
                "label": WINDOW_LABELS[window],
                "utilization": f"{info['utilization']:.0f} %",
                "resets_at": _format_local(info["resets_at"]),
            }
        )

    last_fetch = None
    if data["latest"]:
        last_fetch = max(i["fetched_at"] for i in data["latest"].values() if i["fetched_at"])

    chart_data = {
        "fiveHour": {"label": WINDOW_LABELS[FIVE_HOUR], "points": data["series"][FIVE_HOUR]},
        "sevenDay": {"label": WINDOW_LABELS[SEVEN_DAY], "points": data["series"][SEVEN_DAY]},
        "extra": (
            {"label": WINDOW_LABELS[EXTRA_USAGE], "points": data["series"][EXTRA_USAGE]}
            if data["show_extra"]
            else None
        ),
    }

    context = {
        "period": period,
        "banner_class": banner[0] if banner else "",
        "banner_text": banner[1] if banner else "",
        "periods": periods,
        "summary": summary,
        "last_fetch": _format_local(last_fetch),
        "has_data": bool(data["series"][FIVE_HOUR] or data["series"][SEVEN_DAY]),
        "chart_data": chart_data,
    }
    return render(request, "dashboard/index.html", context)


@require_POST
def refresh(request: HttpRequest) -> HttpResponseRedirect:
    """Run an immediate collection, then redirect back to the dashboard.

    The hourly scheduled task is independent and is not affected.

    Args:
        request: POST request; optional "period" field to keep the current view.

    Returns:
        A redirect to the dashboard with the refresh outcome in the query string.
    """
    period = _selected_period(request.POST.get("period"))
    result = trigger_collection()
    query = urlencode({"period": period, "refresh": "ok" if result.ok else "error"})
    return HttpResponseRedirect(f"{reverse('index')}?{query}")
