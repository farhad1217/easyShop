from django.db import models
from django.contrib.auth.models import User


def generate_list_id():
    """Legacy - kept for migration 0006. Actual list_id now uses pk in save()."""
    return ''


class FamilyProfile(models.Model):
    """Family profile - address, phone, delivery path etc. Linked to User."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='family_profile')
    avatar = models.ImageField(upload_to='profiles/avatars/', blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    extra_info = models.TextField(blank=True)
    area_name = models.CharField(max_length=100, blank=True)
    section_no = models.CharField(max_length=50, blank=True)
    building_name = models.CharField(max_length=100, blank=True)
    floor_no = models.CharField(max_length=50, blank=True)
    room_no = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.full_name or self.user.username

    @property
    def display_name(self):
        return self.full_name or self.user.username

    @property
    def delivery_path_display(self):
        """Full delivery path as single line: Area: X, Section: Y, Building: Z, Floor: A, Room: B"""
        parts = []
        if self.area_name:
            parts.append(f"Area: {self.area_name}")
        if self.section_no:
            parts.append(f"Section: {self.section_no}")
        if self.building_name:
            parts.append(f"Building: {self.building_name}")
        if self.floor_no:
            parts.append(f"Floor: {self.floor_no}")
        if self.room_no:
            parts.append(f"Room: {self.room_no}")
        return ", ".join(parts) if parts else ""


class MarketList(models.Model):
    """Market/Grocery list submitted by a family."""
    STATUS_CHOICES = [
        ('pending', 'পেন্ডিং'),
        ('approved', 'Approved'),
        ('delivered', 'Delivered'),
        ('declined', 'প্রত্যাখ্যান'),
    ]
    list_id = models.CharField(max_length=20, unique=True, blank=True, default='', editable=False)
    family = models.ForeignKey(User, on_delete=models.CASCADE, related_name='market_lists')
    content = models.TextField(blank=True)  # Main list text from user input
    ai_content = models.TextField(blank=True)  # AI-generated/organized list (saved after generate)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.list_id:
            super().save(*args, **kwargs)  # First save to get pk
            self.list_id = f'Pack-{self.pk}'
            super().save(update_fields=['list_id'])
        else:
            super().save(*args, **kwargs)


class SendStatusPreset(models.Model):
    """Saved admin presets for 'Send Order Status' messages."""
    text = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.text

    def __str__(self):
        return f"#{self.list_id} - {self.family.username}"


class MarketListItem(models.Model):
    """Individual item in a market list (optional structured storage)."""
    market_list = models.ForeignKey(MarketList, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=200)
    quantity = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.item_name} - {self.quantity}"


class Notice(models.Model):
    """Single notice from admin shown on all user profiles."""
    content = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Notices'

    @classmethod
    def get_latest(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create(content='')
        return obj


class Conversation(models.Model):
    """One conversation between a user and admin."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_conversation')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"Conv with {self.user.username}"


class Message(models.Model):
    """Message in user-admin conversation; supports text, image, file."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField(blank=True)
    image = models.FileField(upload_to='messages/images/', blank=True, null=True)
    file = models.FileField(upload_to='messages/files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"বার্তা #{self.id}"


class MarketListComment(models.Model):
    """Comment/thread on a market list - management and user can discuss."""
    market_list = models.ForeignKey(MarketList, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='list_comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on #{self.market_list.list_id}"


class Pathway(models.Model):
    """Pathway images for Area/Section/Building in delivery funnel."""
    area_name = models.CharField(max_length=100)
    section_no = models.CharField(max_length=50, blank=True)
    building_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('area_name', 'section_no', 'building_name')]
        ordering = ['area_name', 'section_no', 'building_name']

    def __str__(self):
        parts = [self.area_name]
        if self.section_no:
            parts.append(self.section_no)
        if self.building_name:
            parts.append(self.building_name)
        return ' > '.join(parts)


class PathwayImage(models.Model):
    """Single image in a pathway - ordered by position."""
    pathway = models.ForeignKey(Pathway, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='pathway_images/%Y/%m/')
    position = models.PositiveIntegerField(default=0)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['pathway', 'position']

    def __str__(self):
        return f"Pathway #{self.pathway_id} - Image #{self.position}"


class DeliveryFlow(models.Model):
    """Admin delivery time flow configuration for grouping Total Order Received lists."""
    name = models.CharField(max_length=100, blank=True)
    label = models.CharField(max_length=200)
    start_time = models.TimeField()
    end_time = models.TimeField()
    status_text = models.CharField(max_length=255, default='Approved', blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        base = self.label or self.name or 'Delivery Flow'
        return f"{base} ({self.start_time}–{self.end_time})"
