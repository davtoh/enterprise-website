import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView

from erp.filters import StockMovementFilter
from erp.forms import StockMovementForm
from erp.models import StockMovement, StockMovementType

logger = logging.getLogger(__name__)


class StockMovementListView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = "erp/movement_list.html"
    partial_template_name = "erp/partials/movement_table.html"
    context_object_name = "movements"
    paginate_by = 20

    def get_template_names(self):
        if getattr(self.request, "htmx", False):
            return [self.partial_template_name]
        return [self.template_name]

    def get_queryset(self):
        base_qs = StockMovement.objects.select_related(
            "product", "location", "created_by"
        ).order_by("-created_at")
        self.filterset = StockMovementFilter(self.request.GET, queryset=base_qs)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = getattr(self, "filterset", None)
        ctx["movement_types"] = StockMovementType.choices
        ctx["selected_type"] = self.request.GET.get("type", "")
        ctx["search_query"] = self.request.GET.get("q", "")
        return ctx


class StockMovementCreateView(LoginRequiredMixin, View):
    """Record a stock movement and auto-update inventory on-hand balance."""

    def get(self, request):
        initial_product = request.GET.get("product")
        form = StockMovementForm(initial={"product": initial_product} if initial_product else None)
        return render(request, "erp/movement_form.html", {"form": form})

    def post(self, request):
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.created_by = request.user
            movement.save()
            messages.success(
                request,
                _("Stock movement recorded: %(type)s %(qty)s for %(product)s.")
                % {
                    "type": movement.get_movement_type_display(),
                    "qty": movement.quantity,
                    "product": movement.product.name,
                },
            )
            return redirect("erp:inventory_dashboard")
        return render(request, "erp/movement_form.html", {"form": form})

