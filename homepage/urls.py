from django.urls import path

from . import views

urlpatterns = [
    path('book-inspection/', views.BookInspectionView.as_view(), name='book-inspection'),
    path('inspections/', views.InspectionListView.as_view(), name='inspection-list'),
    path('inspections/active/', views.ActiveInspectionListView.as_view(), name='active-inspection-list'),
    path('inspections/assigned/', views.AssignedInspectionListView.as_view(), name='assigned-inspection-list'),
    path('inspections/<int:inspection_id>/assign-admin/', views.AssignInspectionAdminView.as_view(), name='assign-inspection-admin'),
    path('inspections/<int:inspection_id>/assign-engineer/', views.AssignInspectionEngineerView.as_view(), name='assign-inspection-engineer'),
    path('inspections/<int:inspection_id>/start/', views.StartInspectionView.as_view(), name='start-inspection'),
    path('inspections/<int:inspection_id>/register-customer/', views.RegisterInspectionCustomerView.as_view(), name='register-inspection-customer'),
    path('inspections/<int:inspection_id>/document/', views.InspectionDocumentView.as_view(), name='inspection-document'),
    path('inspections/<int:inspection_id>/document/download/', views.InspectionDocumentDownloadView.as_view(), name='inspection-document-download'),
    path('inspections/<int:inspection_id>/complete/', views.CompleteInspectionView.as_view(), name='complete-inspection'),
]
