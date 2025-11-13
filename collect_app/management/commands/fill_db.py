import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from faker import Faker
from collect_app.models import Collect, Payment

class Command(BaseCommand):
    help = 'Generates mock data for the database'

    def handle(self, *args, **kwargs):
        self.stdout.write("Начинаю генерацию моковых данных...")
        self.stdout.write(self.style.WARNING("Сигналы на время заполнения отключены (если они были)."))

        fake = Faker('ru_RU')

        Payment.objects.all().delete()
        Collect.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write("Старые данные (пользователи, сборы, платежи) удалены.")

        users = []
        for _ in range(1000):
            username = fake.user_name()
            while User.objects.filter(username=username).exists():
                username = fake.user_name() + str(random.randint(1, 99))


            user = User.objects.create_user(
                username=username,
                email=fake.email(),
                password='password123',
                first_name=fake.first_name(),
                last_name=fake.last_name()
            )
            users.append(user)
        self.stdout.write(f"Создано {len(users)} пользователей.")

        collects = []
        occasions = [choice[0] for choice in Collect.Occasion.choices]
        for _ in range(500):
            collect = Collect.objects.create(
                author=random.choice(users),
                title=fake.sentence(nb_words=6).replace('.', ''),
                occasion=random.choice(occasions),
                description=fake.text(max_nb_chars=500),
                goal_amount=Decimal(random.randrange(10000, 500000, 1000)),
                end_at=fake.future_datetime(end_date='+90d'),
            )
            collects.append(collect)
        self.stdout.write(f"Создано {len(collects)} сборов.")

        payment_count = 0
        for collect in collects:
            num_payments = random.randint(5, 15)
            for _ in range(num_payments):
                Payment.objects.create(
                    collect=collect,
                    user=random.choice(users),
                    amount=Decimal(random.randrange(100, 2500, 50)),
                )
                payment_count += 1
        self.stdout.write(f"Создано {payment_count} платежей.")
        self.stdout.write(self.style.SUCCESS("Генерация моковых данных успешно завершена! ✅"))