from django.urls import path

from . import views


app_name = "resumes"


urlpatterns = [

    path(
        "",
        views.resume_list,
        name="resume_list"
    ),

    path(
        "upload/",
        views.upload_resume,
        name="upload_resume"
    ),

    path(
        "<int:pk>/",
        views.resume_detail,
        name="resume_detail"
    ),

    path(
        "<int:pk>/view/",
        views.view_resume,
        name="view_resume"
    ),

    path(
        "<int:pk>/download/",
        views.download_resume,
        name="download_resume"
    ),

    path(
        "<int:pk>/delete/",
        views.delete_resume,
        name="delete_resume"
    ),

    path(
        "<int:pk>/primary/",
        views.set_primary_resume,
        name="set_primary_resume"
    ),
]