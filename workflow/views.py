from django.utils import timezone  # Correct import


from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Customer,  WorkflowHistory
from .serializers import  WorkflowHistorySerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from django.db.models import Count, Q, Avg, F, Min, Max
from django.db.models.functions import TruncDate
from datetime import datetime, date, timedelta
from .models import Customer, WorkflowHistory
from .serializers import (

    DashboardSummarySerializer,
    StateDistributionSerializer,
    DailyTrendsSerializer,
    CustomerProgressSerializer,
    StateTransitionSerializer
)

# Create your views here.
class WorkflowHistoryListView(ListAPIView):
    queryset = WorkflowHistory.objects.select_related("customer", "changed_by").all()
    serializer_class = WorkflowHistorySerializer
    permission_classes = [IsAuthenticated]



class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get date parameter or use today
        date_param = request.query_params.get('date')
        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        else:
            target_date = timezone.now().date()
        
        # Get current state counts for the specified date
        # This gets the latest state for each customer up to the target date
        customer_states = self.get_customer_states_on_date(target_date)
        
        # Count states
        state_counts = {
            'leads_count': 0,
            'pipeline_count': 0,
            'design_count': 0,
            'confirmation_count': 0,
            'production_count': 0,
            'installation_count': 0,
            'sign_out_count': 0,
        }
        
        for state in customer_states.values():
            if state == 'Lead':
                state_counts['leads_count'] += 1
            elif state == 'Pipeline':
                state_counts['pipeline_count'] += 1
            elif state == 'Design':
                state_counts['design_count'] += 1
            elif state == 'Confirmation':
                state_counts['confirmation_count'] += 1
            elif state == 'Production':
                state_counts['production_count'] += 1
            elif state == 'Installation':
                state_counts['installation_count'] += 1
            elif state == 'Sign Out':
                state_counts['sign_out_count'] += 1
        
        # Get new customers created on target date
        new_customers_today = Customer.objects.filter(
            created_at__date=target_date
        ).count()
        
        # Get state transitions for the day
        state_transitions = WorkflowHistory.objects.filter(
            timestamp__date=target_date
        ).values('previous_state', 'new_state').annotate(
            count=Count('workflow_id')
        ).order_by('-count')
        
        data = {
            'date': target_date,
            'total_customers': len(customer_states),
            'new_customers_today': new_customers_today,
            'state_transitions': list(state_transitions),
            **state_counts
        }
        
        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)
    
    def get_customer_states_on_date(self, target_date):
        """Get the latest state for each customer up to the target date"""
        # Get the latest workflow history for each customer up to target date
        latest_histories = WorkflowHistory.objects.filter(
            timestamp__date__lte=target_date
        ).values('customer').annotate(
            latest_timestamp=Max('timestamp')
        )
        
        customer_states = {}
        for item in latest_histories:
            # Get the actual workflow history record
            history = WorkflowHistory.objects.get(
                customer=item['customer'],
                timestamp=item['latest_timestamp']
            )
            customer_states[item['customer']] = history.new_state
            
        return customer_states

class StateDistributionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        date_param = request.query_params.get('date')
        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        else:
            target_date = timezone.now().date()
        
        # Get current customer states
        dashboard_view = DashboardSummaryView()
        customer_states = dashboard_view.get_customer_states_on_date(target_date)
        
        # Count and calculate percentages
        state_counts = {}
        for state in customer_states.values():
            state_counts[state] = state_counts.get(state, 0) + 1
        
        total_customers = len(customer_states)
        
        distribution_data = []
        for state, count in state_counts.items():
            percentage = (count / total_customers * 100) if total_customers > 0 else 0
            distribution_data.append({
                'state': state,
                'count': count,
                'percentage': round(percentage, 2)
            })
        
        serializer = StateDistributionSerializer(distribution_data, many=True)
        return Response(serializer.data)

class DailyTrendsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get date range (default to last 30 days)
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        trends_data = []
        current_date = start_date
        
        while current_date <= end_date:
            # New leads (customers created on this date)
            new_leads = Customer.objects.filter(
                created_at__date=current_date
            ).count()
            
            # State changes on this date
            state_changes = WorkflowHistory.objects.filter(
                timestamp__date=current_date
            ).count()
            
            # Completed installations (customers moved to 'Sign Out' state)
            completed_installations = WorkflowHistory.objects.filter(
                timestamp__date=current_date,
                new_state='Sign Out'
            ).count()
            
            trends_data.append({
                'date': current_date,
                'new_leads': new_leads,
                'state_changes': state_changes,
                'completed_installations': completed_installations
            })
            
            current_date += timedelta(days=1)
        
        serializer = DailyTrendsSerializer(trends_data, many=True)
        return Response(serializer.data)

class CustomerProgressView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get customers with their progress
        customers = Customer.objects.all()
        progress_data = []
        
        for customer in customers:
            # Get customer's workflow history
            histories = WorkflowHistory.objects.filter(
                customer=customer
            ).order_by('timestamp')
            
            if not histories.exists():
                continue
                
            current_state = histories.last().new_state
            
            # Calculate days in current state
            last_state_change = histories.last().timestamp.date()
            days_in_current_state = (timezone.now().date() - last_state_change).days
            
            # Calculate total days in process
            first_entry = histories.first().timestamp.date()
            total_days_in_process = (timezone.now().date() - first_entry).days
            
            # Get state history
            state_history = []
            for history in histories:
                state_history.append({
                    'state': history.new_state,
                    'date': history.timestamp.date(),
                    'changed_by': str(history.changed_by) if history.changed_by else None
                })
            
            progress_data.append({
                'customer_name': customer.name,
                'customer_id': customer.customer_id,
                'current_state': current_state,
                'days_in_current_state': days_in_current_state,
                'total_days_in_process': total_days_in_process,
                'state_history': state_history
            })
        
        # Sort by days in current state (descending)
        progress_data.sort(key=lambda x: x['days_in_current_state'], reverse=True)
        
        serializer = CustomerProgressSerializer(progress_data, many=True)
        return Response(serializer.data)

class StateTransitionAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get state transitions with average time
        transitions = WorkflowHistory.objects.exclude(
            previous_state__isnull=True
        ).values('previous_state', 'new_state').annotate(
            count=Count('workflow_id')
        )
        
        transition_data = []
        for transition in transitions:
            # Calculate average days for this transition
            transition_histories = WorkflowHistory.objects.filter(
                previous_state=transition['previous_state'],
                new_state=transition['new_state']
            )
            
            avg_days = 0
            if transition_histories.exists():
                total_days = 0
                valid_transitions = 0
                
                for history in transition_histories:
                    # Find the previous state entry for this customer
                    previous_history = WorkflowHistory.objects.filter(
                        customer=history.customer,
                        new_state=history.previous_state,
                        timestamp__lt=history.timestamp
                    ).order_by('-timestamp').first()
                    
                    if previous_history:
                        days_diff = (history.timestamp.date() - previous_history.timestamp.date()).days
                        total_days += days_diff
                        valid_transitions += 1
                
                if valid_transitions > 0:
                    avg_days = total_days / valid_transitions
            
            transition_data.append({
                'from_state': transition['previous_state'],
                'to_state': transition['new_state'],
                'count': transition['count'],
                'avg_days': round(avg_days, 1)
            })
        
        # Sort by count (descending)
        transition_data.sort(key=lambda x: x['count'], reverse=True)
        
        serializer = StateTransitionSerializer(transition_data, many=True)
        return Response(serializer.data)

# Convenience view for today's dashboard
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def today_dashboard(request):
    """Get today's dashboard summary"""
    today = timezone.now().date()
    
    dashboard_view = DashboardSummaryView()
    response = dashboard_view.get(request)
    
    return response




