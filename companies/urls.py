from django.urls import path

from . import views


app_name = "companies"


urlpatterns = [

    path(
        "",
        views.company_list,
        name="company_list"
    ),

    path(
        "add/",
        views.add_company,
        name="add_company"
    ),

    path(
        "<int:pk>/",
        views.company_detail,
        name="company_detail"
    ),

    path(
        "<int:pk>/edit/",
        views.edit_company,
        name="edit_company"
    ),

    path(
        "<int:pk>/delete/",
        views.delete_company,
        name="delete_company"
    ),
]