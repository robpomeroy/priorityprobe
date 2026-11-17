from django.urls import path
from llm import views

app_name = "llm"

urlpatterns = [
    path("framework/<int:framework_id>/chat/", views.chat_view, name="chat"),
    path("reflection/<int:reflection_id>/delete/", views.reflection_delete_view, name="reflection_delete"),
]
