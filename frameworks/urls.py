from django.urls import path
from frameworks import views

app_name = "frameworks"

urlpatterns = [
    path("", views.workspace_view, name="workspace"),
    path("framework/<int:framework_id>/", views.workspace_view, name="workspace_detail"),
    path("sample/seed/", views.seed_sample_view, name="seed_sample"),
    path("sample/remove/", views.remove_sample_view, name="remove_sample"),
    
    path("framework/<int:framework_id>/domain/create/", views.domain_create_view, name="domain_create"),
    path("domain/<int:domain_id>/edit/", views.domain_edit_view, name="domain_edit"),
    path("domain/<int:domain_id>/delete/", views.domain_delete_view, name="domain_delete"),
    path("domain/<int:domain_id>/move/<str:direction>/", views.domain_move_view, name="domain_move"),

    path("domain/<int:domain_id>/why/create/", views.why_create_view, name="why_create"),
    path("why/<int:why_id>/edit/", views.why_edit_view, name="why_edit"),
    path("why/<int:why_id>/delete/", views.why_delete_view, name="why_delete"),
    path("why/<int:why_id>/move/<str:direction>/", views.why_move_view, name="why_move"),

    path("framework/<int:framework_id>/objective/create/", views.objective_create_view, name="objective_create"),
    path("objective/<int:objective_id>/edit/", views.objective_edit_view, name="objective_edit"),
    path("objective/<int:objective_id>/delete/", views.objective_delete_view, name="objective_delete"),
    path("objective/<int:objective_id>/status/", views.objective_status_view, name="objective_status"),

    path("framework/<int:framework_id>/goal/create/", views.goal_create_view, name="goal_create"),
    path("goal/<int:goal_id>/edit/", views.goal_edit_view, name="goal_edit"),
    path("goal/<int:goal_id>/delete/", views.goal_delete_view, name="goal_delete"),
    path("goal/<int:goal_id>/status/", views.goal_status_view, name="goal_status"),

    path("review/", views.review_view, name="review"),
    path("review/<int:framework_id>/", views.review_view, name="review_detail"),
    path("review/mark/<str:item_type>/<int:item_id>/", views.mark_reviewed_view, name="mark_reviewed"),
    path("review/<int:framework_id>/mark-all/", views.mark_all_reviewed_view, name="mark_all_reviewed"),
]
