from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile, Collect, Payment
from django.core.cache import cache

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

@receiver([post_save, post_delete], sender=Collect)
@receiver([post_save, post_delete], sender=Payment)
def clear_cache(sender, instance, **kwargs):
    """
    Очищает весь кэш при обновлении/создании/удалении
    сборов или платежей.
    """
    cache.clear()