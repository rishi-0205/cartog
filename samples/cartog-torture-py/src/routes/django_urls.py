"""Django URLconf + class-based view — API-S4. PATTERN: ROUTE-DJANGO-01."""
from django.urls import path
from django.views.generic import View

class MatchView(View):
    """Class-based view for match data."""
    def get(self, request):
        """Handle GET."""
        return None
    def dispatch_request(self):
        """Dispatch to the right method."""
        return self.get()

urlpatterns = [path("api/v1/match/", MatchView.as_view())]
