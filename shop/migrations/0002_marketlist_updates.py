# Generated manually

import secrets
import string
from django.db import migrations, models


def generate_list_id():
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(6))


def populate_list_ids(apps, schema_editor):
    MarketList = apps.get_model('shop', 'MarketList')
    used = set()
    for ml in MarketList.objects.all():
        while True:
            lid = generate_list_id()
            if lid not in used:
                used.add(lid)
                ml.list_id = lid
                ml.save()
                break


def migrate_verified_to_approved(apps, schema_editor):
    MarketList = apps.get_model('shop', 'MarketList')
    MarketList.objects.filter(status='verified').update(status='approved')


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketlist',
            name='list_id',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.RunPython(populate_list_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='marketlist',
            name='list_id',
            field=models.CharField(max_length=10, unique=True),
        ),
        migrations.AddField(
            model_name='marketlist',
            name='content',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='marketlist',
            name='approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='familyprofile',
            name='full_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name='marketlist',
            name='status',
            field=models.CharField(
                choices=[('pending', 'পেন্ডিং'), ('approved', 'অনুমোদিত'), ('delivered', 'পৌঁছানো')],
                default='pending',
                max_length=20
            ),
        ),
        migrations.RunPython(migrate_verified_to_approved, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='marketlist',
            name='verified_at',
        ),
    ]
