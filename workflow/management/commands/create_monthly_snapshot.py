# your_app/management/commands/create_monthly_snapshot.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from workflow.models import MonthlySnapshot 
from customers.models import Customer
from workflow.models import WorkflowHistory

from datetime import datetime

class Command(BaseCommand):
    help = "Create a snapshot of how many customers were in each state at a given date."

    def add_arguments(self, parser):
        parser.add_argument(
            "snapshot_date",
            type=str,
            help="Date in YYYY-MM-DD format (e.g. 2025-07-31)."
        )

    def handle(self, *args, **options):
        snapshot_str = options["snapshot_date"]
        snapshot_date = datetime.strptime(snapshot_str, "%Y-%m-%d").date()

  
        STATES = [s[0] for s in Customer.STATES]
        state_counts = {s: 0 for s in STATES}

        # For each customer, figure out what state they were in on snapshot_date
        all_customers = Customer.objects.all()

        for cust in all_customers:
            cust_state_on_date = self.find_state_on_date(cust, snapshot_date)
            if cust_state_on_date:
                state_counts[cust_state_on_date] += 1

        # Save the snapshot
        MonthlySnapshot.objects.create(
            snapshot_date=snapshot_date,
            state_counts=state_counts
        )

        self.stdout.write(
            self.style.SUCCESS(f"Monthly snapshot created for {snapshot_date} with data: {state_counts}")
        )

    def find_state_on_date(self, customer, snapshot_date):
        """
        Return the state of this customer at the end of snapshot_date.
        We'll check their WorkflowHistory plus their creation time/current state.
        """
        # We'll gather all transitions in chronological order
        transitions = list(
            customer.workflow_histories.all().order_by("timestamp")
        )

        # The approach:
        # start_state = the earliest known state (either at creation or from workflow if you record that)
        # step through transitions until we pass snapshot_date
        # the final state we have on or before snapshot_date is their state at that time

        # If we haven't logged the creation event in WorkflowHistory, we assume the initial state is customer.state
        # or if you store initial in WorkflowHistory, adjust accordingly.

        # We'll assume the state was the 'state' field at creation if there's no earlier record:
        # Then each transition changes the state at timestamp.

        # Option 1: If you always log an initial state in WorkflowHistory, you can skip this guess.
        current_state = None
        # If your DB sets them as 'Lead' initially, let's assume that was correct from day 1.
        # Otherwise, you can use customer.state if you never update that field directly,
        # or see if there's a first transition with previous_state.

        # We'll do a simpler approach:
        # If there's a transition with timestamp < snapshot_date that sets new_state,
        # update current_state. If the last transition is after snapshot_date, the state is what it was prior.
        
        # Sort transitions by timestamp ascending
        # We'll walk through them up to snapshot_date.

        # We'll guess initial state is the 'previous_state' of the first record if it exists,
        # or customer.state if none
        # But let's do a simpler approach: start with the customer's state at creation:
        initial_state = customer.state  # or "Lead"
        current_state = initial_state

        for t in transitions:
            transition_date = t.timestamp.date()
            if transition_date <= snapshot_date:
                # This transition happened on or before snapshot_date, so state changed
                current_state = t.new_state
            else:
                # This transition is in the future relative to snapshot_date
                break

        return current_state
