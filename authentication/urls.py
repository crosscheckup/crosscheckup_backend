from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-email/<uuid:token>/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('admins/', views.AdminPromotionView.as_view(), name='admin-promotion'),
    path('admins/list/', views.AdminListView.as_view(), name='admin-list'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/role/', views.UserRoleUpdateView.as_view(), name='user-role-update'),
    path('users/<int:user_id>/', views.UserDeleteView.as_view(), name='user-delete'),
    path('engineers/', views.EngineerAssignmentView.as_view(), name='engineer-assignment'),
    path('team/', views.TeamView.as_view(), name='team'),
    path('availability/', views.EngineerAvailabilityView.as_view(), name='engineer-availability'),
]
