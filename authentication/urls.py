from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-email/<uuid:token>/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('admins/', views.AdminPromotionView.as_view(), name='admin-promotion'),
    path('engineers/', views.EngineerAssignmentView.as_view(), name='engineer-assignment'),
    path('team/', views.TeamView.as_view(), name='team'),
    path('availability/', views.EngineerAvailabilityView.as_view(), name='engineer-availability'),
]
