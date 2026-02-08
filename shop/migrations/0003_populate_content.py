# Populate content from items for existing MarketLists

from django.db import migrations


def populate_content_from_items(apps, schema_editor):
    MarketList = apps.get_model('shop', 'MarketList')
    MarketListItem = apps.get_model('shop', 'MarketListItem')
    for ml in MarketList.objects.all():
        if not ml.content:
            items = MarketListItem.objects.filter(market_list=ml)
            lines = [f"{i.item_name} {i.quantity}".strip() for i in items if i.item_name]
            ml.content = '\n'.join(lines) if lines else ''
            ml.save()


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0002_marketlist_updates'),
    ]

    operations = [
        migrations.RunPython(populate_content_from_items, migrations.RunPython.noop),
    ]
