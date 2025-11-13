from django.urls import path, include
from .views import (
    HomePageView,
    ArchiveCollectsView, # <-- Правильное имя класса
    CollectDetailView,
    CollectCreateView,
    PaymentDemoView,
    AdminUserListView,
    SignUpView,
    profile_view,
    CollectCloseView,
)

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('archive/', ArchiveCollectsView.as_view(), name='archive'), # <-- Правильное имя пути 'archive'
    path('collect/new/', CollectCreateView.as_view(), name='collect_create'),
    path('collect/<int:pk>/', CollectDetailView.as_view(), name='collect_detail'),
    path('collect/<int:pk>/donate/', PaymentDemoView.as_view(), name='payment_demo'),
    path('collect/<int:pk>/close/', CollectCloseView.as_view(), name='collect_close'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', profile_view, name='profile'),
    path('admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('accounts/', include('django.contrib.auth.urls')),
]