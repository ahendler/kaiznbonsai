import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_historicalstock_purchase_order_item_and_more'),
        ('orders', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('delta', models.DecimalField(decimal_places=3, max_digits=12)),
                ('reason', models.CharField(
                    choices=[
                        ('RECEIPT', 'Receipt'),
                        ('SALE', 'Sale'),
                        ('RETURN', 'Return'),
                        ('ADJUSTMENT', 'Adjustment'),
                    ],
                    max_length=20,
                )),
                ('purchase_order_item', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='stock_movements',
                    to='orders.purchaseorderitem',
                )),
                ('sales_order_item', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='stock_movements',
                    to='orders.salesorderitem',
                )),
                ('stock_batch', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='movements',
                    to='inventory.stock',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='%(class)ss',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'inventory_stock_movements',
                'ordering': ['created_at'],
            },
        ),
    ]
