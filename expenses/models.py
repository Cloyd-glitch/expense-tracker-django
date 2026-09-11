from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Expense(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="expenses"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="expenses"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.category} - {self.amount} ({self.date})"

    def get_absolute_url(self):
        return reverse("expense_detail", kwargs={"pk": self.pk})


class Budget(models.Model):
    """Optional: a weekly spending limit per category, per user."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="budgets"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="budgets"
    )
    weekly_limit = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("user", "category")

    def __str__(self):
        return f"{self.user} - {self.category}: {self.weekly_limit}/wk"