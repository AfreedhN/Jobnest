from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.ats_analyzer,
        name="ats_analyzer"
    ),
]