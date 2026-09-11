import json
from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, ListView, TemplateView, UpdateView,
)

from .forms import BudgetForm, CategoryForm, ExpenseForm, SignUpForm
from .models import Budget, Category, Expense


# ─── Auth ────────────────────────────────────────────────────────────────────

class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f'Welcome, {user.username}! Your account has been created.')
        return redirect('dashboard')


# ─── Dashboard ───────────────────────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'expenses/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()
        year, month = today.year, today.month

        # Current month expenses
        monthly_qs = Expense.objects.filter(
            user=user, date__year=year, date__month=month
        )
        total_this_month = monthly_qs.aggregate(total=Sum('amount'))['total'] or 0

        # Category breakdown for current month
        breakdown = list(
            monthly_qs
            .values('category__name', 'category__id')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        # Budget map {category_id: monthly_limit}
        budgets = {
            b.category_id: b.monthly_limit
            for b in Budget.objects.filter(user=user)
        }

        # Annotate breakdown rows with budget status
        for row in breakdown:
            cat_id = row['category__id']
            limit = budgets.get(cat_id)
            row['limit'] = limit
            if limit:
                row['over_budget'] = row['total'] > limit
                row['pct'] = min(int((row['total'] / limit) * 100), 100)
            else:
                row['over_budget'] = False
                row['pct'] = None

        # Chart data
        chart_labels = [r['category__name'] or 'Uncategorised' for r in breakdown]
        chart_data = [float(r['total']) for r in breakdown]

        # Recent 5 expenses
        recent_expenses = Expense.objects.filter(user=user).select_related('category')[:5]

        ctx.update({
            'today': today,
            'total_this_month': total_this_month,
            'breakdown': breakdown,
            'over_budget_count': sum(1 for r in breakdown if r['over_budget']),
            'chart_labels': json.dumps(chart_labels),
            'chart_data': json.dumps(chart_data),
            'recent_expenses': recent_expenses,
            'month_name': today.strftime('%B %Y'),
        })
        return ctx


# ─── Expenses ────────────────────────────────────────────────────────────────

class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 20

    def get_queryset(self):
        qs = Expense.objects.filter(user=self.request.user).select_related('category')
        cat = self.request.GET.get('category')
        start = self.request.GET.get('start')
        end = self.request.GET.get('end')
        if cat:
            qs = qs.filter(category_id=cat)
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all().order_by('name')
        ctx['selected_cat'] = self.request.GET.get('category', '')
        ctx['start'] = self.request.GET.get('start', '')
        ctx['end'] = self.request.GET.get('end', '')
        ctx['total'] = self.get_queryset().aggregate(t=Sum('amount'))['t'] or 0
        return ctx


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expense_list')

    def get_initial(self):
        return {'date': date.today()}

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Expense added.')
        return super().form_valid(form)


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expense_list')

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Expense updated.')
        return super().form_valid(form)


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expense_list')

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Expense deleted.')
        return super().form_valid(form)


# ─── Categories ──────────────────────────────────────────────────────────────

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'expenses/category_list.html'
    context_object_name = 'categories'


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, f'Category "{form.instance.name}" created.')
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, f'Category "{form.instance.name}" updated.')
        return super().form_valid(form)


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'expenses/category_confirm_delete.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Category deleted.')
        return super().form_valid(form)


# ─── Budgets ─────────────────────────────────────────────────────────────────

class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = 'expenses/budget_list.html'
    context_object_name = 'budgets'

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related('category')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()

        # Annotate each budget with this month's actual spending
        monthly_totals = {
            row['category_id']: row['total']
            for row in Expense.objects.filter(
                user=user, date__year=today.year, date__month=today.month
            ).values('category_id').annotate(total=Sum('amount'))
        }

        for b in ctx['budgets']:
            spent = monthly_totals.get(b.category_id, 0)
            b.spent = spent
            b.over_budget = spent > b.monthly_limit
            b.pct = min(int((spent / b.monthly_limit) * 100), 100) if b.monthly_limit else 0

        return ctx


class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'expenses/budget_form.html'
    success_url = reverse_lazy('budget_list')

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['user'] = self.request.user
        return kw

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Budget set.')
        return super().form_valid(form)


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'expenses/budget_form.html'
    success_url = reverse_lazy('budget_list')

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['user'] = self.request.user
        return kw

    def form_valid(self, form):
        messages.success(self.request, 'Budget updated.')
        return super().form_valid(form)


class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    model = Budget
    template_name = 'expenses/budget_confirm_delete.html'
    success_url = reverse_lazy('budget_list')

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Budget removed.')
        return super().form_valid(form)
