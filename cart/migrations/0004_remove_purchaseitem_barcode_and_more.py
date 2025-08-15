from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0003_drop_category_from_purchaseitem"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE cart_purchaseitem DROP COLUMN IF EXISTS barcode;"
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE cart_purchaseitem DROP COLUMN IF EXISTS brand;"
                ),
                migrations.RunSQL(
                    sql="ALTER TABLE cart_purchaseitem DROP COLUMN IF EXISTS category;"
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="purchaseitem",
                    name="barcode",
                ),
                migrations.RemoveField(
                    model_name="purchaseitem",
                    name="brand",
                ),
                migrations.RemoveField(
                    model_name="purchaseitem",
                    name="category",
                ),
            ],
        ),
    ]
