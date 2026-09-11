from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Category, Expense, Budget


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text='Optional.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ExpenseForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    class Meta:
        model = Expense
        fields = ('amount', 'category', 'date', 'note')
        widgets = {
            'note': forms.TextInput(attrs={'placeholder': 'Optional note…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['category'].empty_label = '— Select category —'


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name',)
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Food, Transport…'}),
        }


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ('category', 'monthly_limit')

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        # When creating, exclude categories the user already has a budget for
        if self.user and not self.instance.pk:
            used_ids = Budget.objects.filter(user=self.user).values_list('category_id', flat=True)
            self.fields['category'].queryset = Category.objects.exclude(id__in=used_ids).order_by('name')
        else:
            self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['category'].empty_label = '— Select category —'
