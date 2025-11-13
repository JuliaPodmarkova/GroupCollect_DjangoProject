from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from .models import Collect, Payment, Comment, Profile
from django.core.mail import send_mail
from django.conf import settings


class CommentInline(admin.TabularInline):
    """
    Позволяет отображать и удалять комментарии прямо на странице сбора.
    """
    model = Comment
    extra = 0
    readonly_fields = ('author', 'text', 'created_at')
    can_delete = True

    fields = ('author', 'text', 'created_at')

@admin.action(description='Активировать выбранные сборы')
def make_collects_active(modeladmin, request, queryset):
    """Массово делает сборы активными."""
    queryset.update(is_active=True)

@admin.register(Collect)
class CollectAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'author', 'title', 'goal_amount',
        'raised_amount', 'end_at', 'is_active', 'end_collect_button'
    )
    list_filter = ('is_active', 'author', 'closure_requested')
    search_fields = ('title', 'author__username', 'description')
    readonly_fields = ('raised_amount', 'created_at')
    actions = [make_collects_active]
    inlines = [CommentInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('author', 'title', 'occasion', 'description', 'cover_image')
        }),
        ('Финансы', {
            'fields': ('goal_amount', 'raised_amount')
        }),
        ('Реквизиты', {
            'fields': ('payment_type', 'recipient_name', 'card_number', 'bank_account_number', 'bank_name', 'bank_bik', 'bank_inn')
        }),
        ('Статус и даты', {
            'fields': ('end_at', 'is_active', 'closure_requested', 'close_reason')
        }),
    )

    def end_collect_button(self, obj):
        if obj.is_active:
            url = reverse('admin:collect_end', args=[obj.pk])
            return format_html('<a class="button" href="{}">Завершить сбор</a>', url)
        return "Сбор завершён"

    end_collect_button.short_description = 'Действие'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'collect/<int:pk>/end/',
                self.admin_site.admin_view(self.end_collect_view),
                name='collect_end'
            )
        ]
        return custom_urls + urls

    def end_collect_view(self, request, pk):
        collect = get_object_or_404(Collect, pk=pk)
        collect.is_active = False
        collect.end_at = timezone.now()
        if not collect.close_reason:
            collect.close_reason = "Завершено администратором."
        collect.save()

        if collect.author.email:
            send_mail(
                f'Ваш сбор "{collect.title}" завершён',
                f'Здравствуйте, {collect.author.username}!\n\n'
                f'Ваш сбор "{collect.title}" был завершён администратором.\n'
                f'Причина: {collect.close_reason}',
                settings.DEFAULT_FROM_EMAIL,
                [collect.author.email]
            )

        self.message_user(request, f"Сбор '{collect.title}' был успешно завершён.")
        return HttpResponseRedirect(reverse('admin:collect_app_collect_changelist'))

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('collect', 'user', 'amount', 'created_at')
    list_filter = ('collect', 'user')
    search_fields = ('collect__title', 'user__username')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_full_name')

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    get_full_name.short_description = 'ФИО'