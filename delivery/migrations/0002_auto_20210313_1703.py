# Generated by Django 3.1.7 on 2021-03-13 14:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='orders',
            field=models.ManyToManyField(db_index=True, related_name='invoices', to='delivery.Order', verbose_name='Заказы'),
        ),
        migrations.AddField(
            model_name='order',
            name='complete_time',
            field=models.DateTimeField(null=True, verbose_name='Время завершения заказа'),
        ),
        migrations.DeleteModel(
            name='Delivery',
        ),
    ]