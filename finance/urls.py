from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_transactions, name="upload_transactions"),
    path("update-category/<int:pk>/",views.update_category,name="update_category"),
    path("auto-categorize/",views.auto_categorize,name="auto_categorize"),
    path("profit-loss/",views.profit_loss,name="profit_loss"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("test-ai/",views.test_ai_categorization,name="test_ai_categorization"),
    path("ai-auto-categorize/",views.ai_auto_categorize,name="ai_auto_categorize"),
    path("financial-analyst/", views.financial_analyst, name="financial_analyst"),
]