from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from customers.models import Customer
from leads.models import Pipeline
from design.models import DesignPhase
from production_installation.models import ProductionInstallationPhase
from workflow.models import WorkflowHistory

# Store the previous state before saving
@receiver(pre_save, sender=Customer)
def store_previous_state(sender, instance, **kwargs):
    """
    Store the previous state before the customer is saved.
    """
    if instance.pk:  # Only for existing customers (updates)
        try:
            previous_customer = Customer.objects.get(pk=instance.pk)
            instance._previous_state = previous_customer.state
        except Customer.DoesNotExist:
            instance._previous_state = None
    else:  # For new customers
        instance._previous_state = None

@receiver(post_save, sender=Customer)
def create_workflow_history(sender, instance, created, **kwargs):
    """
    Create WorkflowHistory entry when customer state changes or when customer is created.
    """
    previous_state = getattr(instance, '_previous_state', None)
    current_state = instance.state
    
    # For new customers, create initial workflow history
    if created:
        WorkflowHistory.objects.create(
            customer=instance,
            previous_state=None,  # No previous state for new customers
            new_state=current_state,
            changed_by=getattr(instance, '_changed_by', None)  # You can set this in your view
        )
        print(f"Initial workflow history created for customer: {instance.name} - State: {current_state}")
    
    # For existing customers, only create history if state actually changed
    elif previous_state and previous_state != current_state:
        WorkflowHistory.objects.create(
            customer=instance,
            previous_state=previous_state,
            new_state=current_state,
            changed_by=getattr(instance, '_changed_by', None)  # You can set this in your view
        )
        print(f"Workflow history created for customer: {instance.name} - {previous_state} -> {current_state}")

@receiver(post_save, sender=Customer)
def create_or_update_pipeline(sender, instance, **kwargs):
    """
    Automatically create or update a Pipeline object when a Customer's state is set to 'Pipeline'.
    """
    if instance.state == "Pipeline":
        # Create or update the pipeline for the customer
        pipeline, created = Pipeline.objects.get_or_create(customer=instance)
        if created:
            print(f"Pipeline created for customer: {instance.name}")
        else:
            print(f"Pipeline updated for customer: {instance.name}")
    else:
        # Optional: Delete the pipeline if the customer's state is not 'Pipeline'
        Pipeline.objects.filter(customer=instance).delete()

@receiver(post_save, sender=Customer)
def create_design_phase(sender, instance, **kwargs):
    if instance.state == 'Design':
        design_phase, created = DesignPhase.objects.get_or_create(customer=instance)
        if created:
            print(f"Design phase created for customer: {instance.name}")
        else:
            print(f"Design phase updated for customer: {instance.name}")
    else:
        # Optional: Delete the design phase if the customer's state is not 'Design'
        DesignPhase.objects.filter(customer=instance).delete()

@receiver(post_save, sender=Customer)
def create_production_installation_phase(sender, instance, **kwargs):
    if instance.state in ['Production', 'Installation']:
        ProductionInstallationPhase.objects.get_or_create(customer=instance)