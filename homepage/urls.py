from django.urls import path

from . import views

urlpatterns = [
    path('book-inspection/', views.BookInspectionView.as_view(), name='book-inspection'),
    path('inspections/', views.InspectionListView.as_view(), name='inspection-list'),
    path('inspections/<int:inspection_id>/assign-admin/', views.AssignInspectionAdminView.as_view(), name='assign-inspection-admin'),
    path('inspections/<int:inspection_id>/assign-engineer/', views.AssignInspectionEngineerView.as_view(), name='assign-inspection-engineer'),
]
