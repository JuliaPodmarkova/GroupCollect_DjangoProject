from django.db import models
from django.contrib.auth.models import User
from .utils import censor
from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import RegexValidator, MinLengthValidator
from django.utils import timezone


class Profile(models.Model):
    """
    Расширение стандартной модели пользователя для хранения дополнительной информации,
    например, аватара.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Аватар")

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f'Профиль {self.user.username}'

    @property
    def full_name(self):
        return self.user.get_full_name()


class Collect(models.Model):
    """
    Основная модель для группового денежного сбора.
    """

    class Occasion(models.TextChoices):
        BIRTHDAY = 'birthday', 'День рождения'
        WEDDING = 'wedding', 'Свадьба'
        CHARITY = 'charity', 'Благотворительность'
        TRAVEL = 'travel', 'Путешествие'
        PROJECT = 'project', 'Проект'
        OTHER = 'other', 'Другое'

    class PaymentType(models.TextChoices):
        CARD = 'card', 'Карта'
        ACCOUNT = 'account', 'Банковский счёт'

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections', verbose_name="Автор")
    title = models.CharField(max_length=200, verbose_name="Название сбора")
    occasion = models.CharField(max_length=20, choices=Occasion.choices, verbose_name="Повод")
    occasion_other_text = models.CharField(max_length=255, null=True, blank=True, verbose_name="Уточните повод")
    description = models.TextField(verbose_name="Описание")
    goal_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                      verbose_name="Сумма для сбора")
    raised_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Собрано")
    cover_image = models.ImageField(upload_to='covers/', null=True, blank=True, verbose_name="Обложка сбора")
    end_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время окончания сбора')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    is_active = models.BooleanField(default=False, verbose_name="Сбор активен")
    closure_requested = models.BooleanField(default=False, verbose_name="Запрошено закрытие")
    close_reason = models.TextField(blank=True, null=True, verbose_name="Причина завершения сбора")

    payment_type = models.CharField(
        max_length=10,
        choices=PaymentType.choices,
        verbose_name="Тип реквизитов",
        default=PaymentType.CARD
    )
    recipient_name = models.CharField(
        max_length=255,
        verbose_name="ФИО получателя / Название организации",
        default='Не указано'
    )

    card_number = models.CharField(
        max_length=16, null=True, blank=True,
        validators=[
            RegexValidator(r'^[245]\d{15}$', 'Номер карты должен состоять из 16 цифр и начинаться с 2, 4 или 5.')],
        verbose_name="Номер карты"
    )

    bank_account_number = models.CharField(
        max_length=20, null=True, blank=True,
        validators=[MinLengthValidator(20)],
        verbose_name="Номер счёта"
    )
    bank_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Наименование банка")
    bank_bik = models.CharField(
        max_length=9, null=True, blank=True,
        validators=[MinLengthValidator(9)],
        verbose_name="БИК банка"
    )
    bank_inn = models.CharField(
        max_length=10, null=True, blank=True,
        validators=[MinLengthValidator(10)],
        verbose_name="ИНН банка"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_is_active = self.is_active

    @property
    def payment_purpose(self):
        return f"Групповой сбор: {self.title}"

    @property
    def get_full_occasion_display(self):
        """Возвращает кастомный повод, если он есть, иначе стандартный."""
        if self.occasion == self.Occasion.OTHER and self.occasion_other_text:
            return self.occasion_other_text
        return self.get_occasion_display()

    class Meta:
        verbose_name = "Сбор"
        verbose_name_plural = "Сборы"
        ordering = ['-created_at']

    def get_raised_percentage(self):
        if self.goal_amount and self.goal_amount > 0:
            return min(int((self.raised_amount / self.goal_amount) * 100), 100)
        return 0

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.title: self.title = censor(self.title)
        if self.description: self.description = censor(self.description)
        if self.close_reason: self.close_reason = censor(self.close_reason)
        if self.occasion_other_text: self.occasion_other_text = censor(self.occasion_other_text)
        is_new = self.pk is None

        if not is_new and self.is_active and not self.__original_is_active and self.author.email:
            subject = f'✅ Ваш сбор "{self.title}" одобрен!'
            message = (
                f'Здравствуйте, {self.author.username}!\n\n'
                f'Ваш сбор "{self.title}" успешно прошёл модерацию и теперь активен.\n'
                f'Вы можете посмотреть его на сайте.'
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.author.email], fail_silently=False)

        if not is_new and not self.is_active and self.__original_is_active and self.author.email:
            subject = f'ℹ️ Ваш сбор "{self.title}" завершён'
            message = (
                f'Здравствуйте, {self.author.username}!\n\n'
                f'Ваш сбор "{self.title}" был завершён и перенесён в архив.\n'
                f'Причина: {self.close_reason or "Завершён администратором"}\n\n'
                f'Спасибо за вашу инициативу!'
            )
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.author.email], fail_silently=False)


        super().save(*args, **kwargs)
        self.__original_is_active = self.is_active


class Payment(models.Model):
    """
    Модель для хранения информации о каждом отдельном пожертвовании.
    Автоматически обновляет сумму в связанном сборе при создании.
    """
    collect = models.ForeignKey(Collect, on_delete=models.CASCADE, related_name='payments', verbose_name="Сбор")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations', verbose_name="Участник")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма платежа")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата платежа")

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ['-created_at']

    def __str__(self):
        return f'Платёж от {self.user.username} на {self.amount} ₽'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            collect = self.collect
            collect.raised_amount += self.amount
            collect.save(update_fields=['raised_amount'])

            if self.user.email:
                subject = f'✅ Спасибо за ваше пожертвование!'
                message = (f'Здравствуйте, {self.user.username}!\n\n'
                           f'Вы успешно пожертвовали {self.amount} ₽ на сбор "{collect.title}".\n\n'
                           f'Спасибо за вашу поддержку!')
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.user.email], fail_silently=False)

            if collect.author.email and collect.author != self.user:
                remaining_amount = (
                            collect.goal_amount - collect.raised_amount) if collect.goal_amount else 'бесконечности'
                subject = f'💰 Новый донат в вашем сборе "{collect.title}"!'
                message = (f'Здравствуйте, {collect.author.username}!\n\n'
                           f'Пользователь {self.user.username} поддержал ваш сбор "{collect.title}" на сумму {self.amount} ₽.\n'
                           f'Всего собрано: {collect.raised_amount} ₽.\n'
                           f'Осталось собрать: {remaining_amount} ₽.\n\n'
                           'Так держать!')
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [collect.author.email], fail_silently=False)

            if collect.is_active and collect.goal_amount and collect.raised_amount >= collect.goal_amount:
                collect.is_active = False
                collect.end_at = timezone.now()
                collect.close_reason = "Сбор автоматически завершён, так как цель достигнута."
                collect.save()

                admin_users = User.objects.filter(is_superuser=True)
                admin_emails = [user.email for user in admin_users if user.email]
                if admin_emails:
                    subject = f'🎯 Сбор "{collect.title}" автоматически завершён'
                    message = (f'Сбор "{collect.title}" был автоматически завершён.\n\n'
                               f'Причина: 100% необходимой суммы ({collect.goal_amount} ₽) было собрано.')
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, admin_emails, fail_silently=False)


class Comment(models.Model):
    """Модель для комментариев, оставленных к сбору."""
    collect = models.ForeignKey(Collect, on_delete=models.CASCADE, related_name='comments', verbose_name="Сбор")
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Автор")
    text = models.TextField(verbose_name="Текст комментария")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['-created_at']

    def __str__(self):
        return f'Комментарий от {self.author} к сбору "{self.collect.title}"'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if self.text: self.text = censor(self.text)
        super().save(*args, **kwargs)

        if is_new and self.collect.author.email and self.collect.author != self.author:
            subject = f'💬 Новый комментарий к вашему сбору "{self.collect.title}"'
            message = (f'Здравствуйте, {self.collect.author.username}!\n\n'
                       f'Пользователь {self.author.username} оставил комментарий к вашему сбору:\n'
                       f'"{self.text}"\n\n')
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.collect.author.email], fail_silently=False)