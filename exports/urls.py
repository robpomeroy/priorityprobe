from django.urls import path
from exports import views

app_name = "exports"

urlpatterns = [
    path("framework/<int:framework_id>/", views.export_framework_view, name="export_framework"),
    path("decision/<int:decision_id>/", views.export_decision_view, name="export_decision"),
]
