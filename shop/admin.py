from django.contrib import admin
from .models import FamilyProfile, MarketList, MarketListItem, Notice, Conversation, Message, MarketListComment, Pathway, PathwayImage


class MarketListItemInline(admin.TabularInline):
    model = MarketListItem
    extra = 0


@admin.register(MarketList)
class MarketListAdmin(admin.ModelAdmin):
    list_display = ['list_id', 'family', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    inlines = [MarketListItemInline]


@admin.register(FamilyProfile)
class FamilyProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'phone', 'address']


admin.site.register(MarketListItem)


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['id', 'content_preview', 'updated_at']

    def content_preview(self, obj):
        return (obj.content or '')[:60] + '...' if len(obj.content or '') > 60 else (obj.content or '-')
    content_preview.short_description = 'Content'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'message_count']

    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'body_preview', 'created_at', 'read_at']

    def body_preview(self, obj):
        return (obj.body or '')[:40] + '...' if len(obj.body or '') > 40 else (obj.body or '-')
    body_preview.short_description = 'Body'


@admin.register(MarketListComment)
class MarketListCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'market_list', 'author', 'body_preview', 'created_at']

    def body_preview(self, obj):
        return (obj.body or '')[:40] + '...' if len(obj.body or '') > 40 else (obj.body or '-')
    body_preview.short_description = 'Body'


class PathwayImageInline(admin.TabularInline):
    model = PathwayImage
    extra = 0


@admin.register(Pathway)
class PathwayAdmin(admin.ModelAdmin):
    list_display = ['area_name', 'section_no', 'building_name', 'created_at']
    inlines = [PathwayImageInline]
