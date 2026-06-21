from rest_framework.routers import DefaultRouter
from .views import PurchaseOrderViewSet, SalesOrderViewSet

router = DefaultRouter()
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'sales-orders', SalesOrderViewSet, basename='sales-order')

urlpatterns = router.urls
