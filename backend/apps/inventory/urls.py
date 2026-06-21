from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.inventory.views import ProductViewSet, StockViewSet

app_name = 'inventory'

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'stocks', StockViewSet, basename='stock')

urlpatterns = [
    path('', include(router.urls)),
]
