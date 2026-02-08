import secrets
import string
from django.db import models
from django.contrib.auth.models import User


def generate_list_id():
    """Generate unique 6-char alphanumeric ID."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(6))


class FamilyProfile(models.Model):
    """Family profile - address, phone etc. Linked to User."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='family_profile')
    full_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name or self.user.username

    @property
    def display_name(self):
        return self.full_name or self.user.username


class MarketList(models.Model):
    """Market/Grocery list submitted by a family."""
    STATUS_CHOICES = [
        ('pending', 'পেন্ডিং'),
        ('approved', 'অনুমোদিত'),
        ('delivered', 'পৌঁছানো'),
    ]
    list_id = models.CharField(max_length=10, unique=True, default=generate_list_id, editable=False)
    family = models.ForeignKey(User, on_delete=models.CASCADE, related_name='market_lists')
    content = models.TextField(blank=True)  # Main list text from user input
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.list_id:
            self.list_id = generate_list_id()
            while MarketList.objects.filter(list_id=self.list_id).exists():
                self.list_id = generate_list_id()
        super().save(*args, **kwargs)

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
