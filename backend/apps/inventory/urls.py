from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.inventory.views import (
    ProductViewSet,
    StockViewSet,
    OverallFinancialsView,
    ProductFinancialsView,
    StockMovementListView,
)

app_name = 'inventory'

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'stocks', StockViewSet, basename='stock')

urlpatterns = [
    path('financials/', OverallFinancialsView.as_view(), name='overall-financials'),
    path('financials/products/', ProductFinancialsView.as_view(), name='product-financials'),
    path('movements/', StockMovementListView.as_view(), name='stock-movement-list'),
    path('', include(router.urls)),
]
