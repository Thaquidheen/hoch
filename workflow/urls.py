from django.urls import path
from .views import (
    WorkflowHistoryListView,
    DashboardSummaryView,
    StateDistributionView,
    DailyTrendsView,
    CustomerProgressView,
    StateTransitionAnalyticsView,
    today_dashboard
)

urlpatterns = [
   path('history/', WorkflowHistoryListView.as_view(), name='workflow_history_list'),

    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard_summary'),
    path('dashboard/today/', today_dashboard, name='today_dashboard'),
    path('dashboard/state-distribution/', StateDistributionView.as_view(), name='state_distribution'),
    path('dashboard/daily-trends/', DailyTrendsView.as_view(), name='daily_trends'),
    path('dashboard/customer-progress/', CustomerProgressView.as_view(), name='customer_progress'),
    path('dashboard/state-transitions/', StateTransitionAnalyticsView.as_view(), name='state_transitions'),

]
