from django.urls import path
from decisions import views

app_name = "decisions"

urlpatterns = [
    path("", views.decision_list_view, name="decision_list"),
    path("compare/", views.decision_compare_view, name="compare"),
    path("compare/<int:framework_id>/", views.decision_compare_view, name="compare_detail"),
    path("create/", views.decision_create_view, name="decision_create"),
    path("<int:decision_id>/", views.decision_detail_view, name="decision_detail"),
    path("<int:decision_id>/edit/", views.decision_edit_view, name="decision_edit"),
    path("<int:decision_id>/delete/", views.decision_delete_view, name="decision_delete"),
    path("<int:decision_id>/reflect/", views.decision_reflect_view, name="decision_reflect"),
]
