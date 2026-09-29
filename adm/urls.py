from django.urls import path
from . import views


urlpatterns = [
    path("", views.admin_dashboard, name="admin_dashboard"),
    path("companies/<int:pk>/status/", views.update_company_status, name="update_company_status"),
]