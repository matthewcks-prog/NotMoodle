from django.urls import path
from .views import StudentListView, ManageCreditView, student_login, student_logout, student_home, student_signup, student_dashboard

app_name = "student_management"

urlpatterns = [
    path("", student_login, name="student_login"),
    path("signup/", student_signup, name="student_signup"),
    path("manage_credit_point/", StudentListView.as_view(), name="student_list"),
    path("manage_credit_point/<int:pk>/credit/", ManageCreditView.as_view(), name="manage_credit"),
    path("login/", student_login, name="student_login"),
    path("logout/", student_logout, name="student_logout"),
    path("home/", student_dashboard, name="student_home"),
    path("dashboard/", student_dashboard, name="student_dashboard"),
]