# classrooms/urls.py
from django.urls import path
from . import views
from .views import (ClassroomCreateView, ClassroomDetailView, ClassroomListView, assignment_create_for_classroom,
                    upload_attachments_for_assignment, delete_attachment, AssignmentUpdateView)


app_name = "classroom_and_grading"

urlpatterns = [
     path("", ClassroomListView.as_view(), name="classroom_list"),
     path("create/", ClassroomCreateView.as_view(), name="classroom_create"),
     path("<int:pk>/", ClassroomDetailView.as_view(), name="classroom_detail"),
     path("<int:pk>/assignments/create/", assignment_create_for_classroom, name="assignment_create_for_classroom"),
     path("assignments/<int:assignment_id>/attachments/upload/",
         upload_attachments_for_assignment, name="upload_attachments_for_assignment"),
     path("attachments/<int:att_id>/delete/",
         delete_attachment, name="delete_attachment"),
     path("<int:classroom_pk>/assignments/<int:pk>/edit/",
         AssignmentUpdateView.as_view(),
         name="assignment_edit_for_classroom"),
     path(
         "classrooms/<int:pk>/assignments/<int:assignment_id>/delete/",
         views.delete_assignment_for_classroom,
         name="assignment_delete_for_classroom",
         ),
     path("classrooms/<int:pk>/delete/",
     views.delete_classroom,
     name="classroom_delete"),
]
