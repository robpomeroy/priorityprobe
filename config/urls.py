from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("frameworks/", include("frameworks.urls")),
    path("decisions/", include("decisions.urls")),
    path("exports/", include("exports.urls")),
    path("llm/", include("llm.urls")),
    path("", RedirectView.as_view(pattern_name="frameworks:workspace", permanent=False)),
]
