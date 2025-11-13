from django.contrib.auth.models import User
from django import forms
from .models import Collect, Profile, User, Comment
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

class CollectCreationForm(forms.ModelForm):
    class Meta:
        model = Collect
        fields = [
            'title', 'occasion', 'occasion_other_text', 'description', 'goal_amount', 'cover_image', 'end_at',
            'payment_type', 'recipient_name', 'card_number',
            'bank_account_number', 'bank_name', 'bank_bik', 'bank_inn'
        ]
        widgets = {
            'end_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('payment_type')
        occasion = cleaned_data.get('occasion')
        occasion_other_text = cleaned_data.get('occasion_other_text')

        if occasion == 'other' and not occasion_other_text:
            self.add_error('occasion_other_text', 'Пожалуйста, укажите свой повод, так как вы выбрали "Другое".')

        if payment_type == 'card':
            card_number = cleaned_data.get('card_number')
            if not card_number:
                self.add_error('card_number', 'Это поле обязательно для типа "Карта".')
            elif len(card_number) != 16 or not card_number.isdigit():
                self.add_error('card_number', 'Номер карты должен состоять из 16 цифр.')
            elif card_number[0] not in ['2', '4', '5']:
                self.add_error('card_number', 'Неверный формат карты. Допустимы карты МИР (первая цифра 2), Visa (первая цифра 4), MasterCard (первая цифра 5).')

        elif payment_type == 'account':
            required_fields = {
                'bank_account_number': ('Номер счёта', 20),
                'bank_bik': ('БИК банка', 9),
                'bank_inn': ('ИНН банка', 10),
                'bank_name': ('Наименование банка', None)
            }
            for field, (label, length) in required_fields.items():
                value = cleaned_data.get(field)
                if not value:
                    self.add_error(field, f'Поле "{label}" обязательно для банковского счёта.')
                elif length and (len(value) != length or not value.isdigit()):
                     self.add_error(field, f'Поле "{label}" должно состоять из {length} цифр.')

        return cleaned_data

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Обязательное поле. Введите корректный email.')

    class Meta:
        model = User
        fields = ('username', 'email')

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar']

class CloseCollectForm(forms.ModelForm):
    class Meta:
        model = Collect
        fields = ['close_reason']
        widgets = {
            'close_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Укажите причину, по которой сбор завершается досрочно...'
            }),
        }
        labels = {
            'close_reason': 'Причина завершения'
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Напишите ваш комментарий...'
            }),
        }
        labels = {
            'text': ''
        }