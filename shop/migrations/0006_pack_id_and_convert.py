# Generated manually
from django.db import migrations, models
from shop.models import generate_list_id


def convert_to_pack_ids(apps, schema_editor):
    """Convert existing list_ids to Pack-1, Pack-2, Pack-3..."""
    MarketList = apps.get_model('shop', 'MarketList')
    for i, ml in enumerate(MarketList.objects.order_by('created_at', 'id'), 1):
        ml.list_id = f'Pack-{i}'
        ml.save()


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0005_add_declined_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketlist',
            name='list_id',
            field=models.CharField(default=generate_list_id, editable=False, max_length=20, unique=True),
        ),
        migrations.RunPython(convert_to_pack_ids, migrations.RunPython.noop),
    ]
