# /collect_app/views.py

from .forms import SignUpForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Sum, Count
from django.contrib import messages
from .models import Collect, Payment, User, Profile
from .forms import CollectCreationForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth.decorators import login_required
from .forms import CloseCollectForm
from django.shortcuts import render, get_object_or_404, redirect
from .forms import CommentForm
from profanity import profanity
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets
from .serializers import CollectSerializer, PaymentSerializer, UserSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

@method_decorator(vary_on_cookie, name='dispatch')
@method_decorator(cache_page(60 * 2), name='dispatch')
class HomePageView(ListView):
    model = Collect
    template_name = 'home.html'
    context_object_name = 'collects'
    paginate_by = 9
    def get_queryset(self):
        return Collect.objects.filter(is_active=True).order_by('-created_at')

@method_decorator(vary_on_cookie, name='dispatch')
@method_decorator(cache_page(60 * 2), name='dispatch')
class ArchiveCollectsView(ListView):
    model = Collect
    template_name = 'home.html'
    context_object_name = 'collects'
    paginate_by = 9
    def get_queryset(self):
        return Collect.objects.filter(is_active=False).order_by('-end_at', '-created_at')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_archive_page'] = True
        return context

class CollectDetailView(DetailView):
    def get(self, request, pk):
        collect = get_object_or_404(Collect, pk=pk)
        comments = collect.comments.all()
        comment_form = CommentForm()
        context = {
            'collect': collect,
            'comments': comments,
            'comment_form': comment_form
        }
        return render(request, 'collect_detail.html', context)
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect('login')
        collect = get_object_or_404(Collect, pk=pk)
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.collect = collect
            new_comment.author = request.user
            censored_text = profanity.censor(new_comment.text)
            new_comment.text = censored_text
            new_comment.save()
            return redirect('collect_detail', pk=collect.pk)
        comments = collect.comments.all()
        context = {
            'collect': collect,
            'comments': comments,
            'comment_form': comment_form
        }
        return render(request, 'collect_detail.html', context)

class CollectCreateView(LoginRequiredMixin, CreateView):
    model = Collect
    form_class = CollectCreationForm
    template_name = 'collect_form.html'
    success_url = reverse_lazy('home')
    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        messages.success(self, 'Ваш сбор успешно создан и отправлен на модерацию!')
        new_collect = self.object
        admin_users = User.objects.filter(is_superuser=True)
        admin_emails = [user.email for user in admin_users if user.email]
        if admin_emails:
            subject = f'Новый сбор на модерацию: "{new_collect.title}"'
            admin_url = self.request.build_absolute_uri(
                reverse('admin:collect_app_collect_change', args=[new_collect.pk])
            )
            message = (
                f'Пользователь {new_collect.author.username} создал новый сбор.\n'
                f'Название: {new_collect.title}\n\n'
                f'Пожалуйста, проверьте и активируйте его в админ-панели:\n'
                f'{admin_url}'
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=False,
            )
        return response

class ProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    template_name = 'profile.html'
    fields = []
    def get_object(self):
        return self.request.user.profile
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collect'] = get_object_or_404(Collect, pk=self.kwargs.get('pk'))
        if self.request.POST:
            context['user_form'] = UserUpdateForm(self.request.POST, instance=self.request.user)
            context['profile_form'] = ProfileUpdateForm(self.request.POST, self.request.FILES, instance=self.request.user.profile)
        else:
            context['user_form'] = UserUpdateForm(instance=self.request.user)
            context['profile_form'] = ProfileUpdateForm(instance=self.request.user.profile)
        messages.info(
            self.request,
            '🚧 Это демонстрационная страница. Функционал тестовый, реальные платежи не проводятся.'
        )
        return context
    def post(self, request, *args, **kwargs):
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Ваш профиль успешно обновлен!')
            return redirect('profile')
        else:
            return self.render_to_response(self.get_context_data())

class PaymentDemoView(LoginRequiredMixin, TemplateView):
    template_name = 'payment_demo.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collect_pk = self.kwargs.get('pk')
        context['collect'] = get_object_or_404(Collect, pk=collect_pk)
        messages.info(
            self.request,
            '🚧 Это демонстрационная страница. Функционал тестовый, реальные платежи не проводятся.'
        )
        return context
    def post(self, request, *args, **kwargs):
        collect_pk = self.kwargs.get('pk')
        collect = get_object_or_404(Collect, pk=collect_pk)
        try:
            amount = int(request.POST.get('amount'))
            if amount <= 0:
                raise ValueError("Сумма должна быть положительной.")
        except (ValueError, TypeError):
            messages.error(request, 'Пожалуйста, введите корректную сумму.')
            return redirect('payment_demo', pk=collect.pk)
        Payment.objects.create(
            user=request.user,
            collect=collect,
            amount=amount
        )
        messages.success(request, f'Спасибо! Вы успешно пожертвовали {amount} ₽.')
        return redirect('collect_detail', pk=collect.pk)

class AdminUserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User
    template_name = 'admin_user_list.html'
    context_object_name = 'users'
    def test_func(self):
        return self.request.user.is_superuser
    def get_queryset(self):
        return User.objects.annotate(
            collections_created=Count('collections'),
            total_donated=Sum('donations__amount')
        ).order_by('-date_joined')

def end_collect(request, pk):
    if not request.user.is_superuser:
        return redirect('home')
    collect = get_object_or_404(Collect, pk=pk)
    collect.is_active = False
    collect.save()
    messages.info(request, f'Сбор "{collect.title}" был успешно завершен.')
    return redirect('home')

class CollectViewSet(viewsets.ModelViewSet):
    queryset = Collect.objects.all()
    serializer_class = CollectSerializer
    @method_decorator(cache_page(60 * 2))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    @method_decorator(cache_page(60 * 2))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

@login_required
def profile_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'profile.html', context)

class CollectCloseView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Collect
    form_class = CloseCollectForm
    template_name = 'collect_close_form.html'
    def test_func(self):
        collect = self.get_object()
        return collect.is_active and (self.request.user == collect.author or self.request.user.is_superuser)
    def form_valid(self, form):
        collect = form.save(commit=False)
        if self.request.user.is_superuser:
            collect.is_active = False
            collect.end_at = timezone.now()
            collect.save()
            messages.success(self, f'Сбор "{collect.title}" был успешно завершен.')
        else:
            collect.closure_requested = True
            collect.save()
            messages.info(self, 'Ваш запрос на досрочное завершение сбора отправлен администратору.')
            admin_users = User.objects.filter(is_superuser=True)
            admin_emails = [user.email for user in admin_users if user.email]
            if admin_emails:
                subject = f'⚠️ Запрос на закрытие сбора: "{collect.title}"'
                admin_url = self.request.build_absolute_uri(
                    reverse('admin:collect_app_collect_change', args=[collect.pk])
                )
                message = (
                    f'Пользователь {collect.author.username} запросил досрочное завершение сбора "{collect.title}".\n\n'
                    f'Причина: {collect.close_reason}\n\n'
                    f'Пожалуйста, рассмотрите запрос и при необходимости завершите сбор в админ-панели:\n'
                    f'{admin_url}'
                )
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, admin_emails, fail_silently=False)
        return redirect(self.get_success_url())
    def get_success_url(self):
        return reverse_lazy('collect_detail', kwargs={'pk': self.object.pk})