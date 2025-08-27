from rest_framework import serializers
from .models import *



class KitchenTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = KitchenType
        fields = ['id', 'type', 'count']



class CustomerSerializer(serializers.ModelSerializer):
    kitchen_types = KitchenTypeSerializer(many=True, required=False)

    class Meta:
        model = Customer
        fields = [
            'customer_id',
            'name',
            'location',
            'contact_number',
            'state',
            'is_active',
            'created_at',
            'kitchen_types'
        ]
        read_only_fields = ['customer_id', 'created_at']

    def create(self, validated_data):
        """Create a Customer and related KitchenTypes."""
        kitchen_types_data = validated_data.pop('kitchen_types', [])
        # The 'status' field is already in validated_data and will be saved automatically
        customer = Customer.objects.create(**validated_data)

        for kt_data in kitchen_types_data:
            KitchenType.objects.create(customer=customer, **kt_data)

        return customer

    def update(self, instance, validated_data):
        """Update a Customer and manage changes in nested KitchenTypes."""
        kitchen_types_data = validated_data.pop('kitchen_types', None)

        # The 'status' field is also handled here automatically
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if kitchen_types_data is not None:
            instance.kitchen_types.all().delete()
            for kt_data in kitchen_types_data:
                KitchenType.objects.create(customer=instance, **kt_data)

        return instance

class CustomerStateSerializer(serializers.ModelSerializer):
 
    class Meta:
        model = Customer
        fields = ['state']  # Only allow updating the state field

    def validate_state(self, value):
        """
        Validates the state field to ensure it matches valid choices.
        """
        valid_states = [
            'Lead', 'Pipeline', 'Design', 'Confirmation',
            'Production', 'Installation', 'Sign Out'
        ]
        if value not in valid_states:
            raise serializers.ValidationError(f"Invalid state '{value}'. Valid states are: {', '.join(valid_states)}.")
        return value
    
class DocumentSerializer(serializers.ModelSerializer):
    name_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Document
        fields = ('id', 'name', 'name_display', 'file', 'uploaded_at')

    def get_name_display(self, obj):
        return obj.get_name_display()

class RequirementSerializer(serializers.ModelSerializer):
    documents = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )
    documents_data = DocumentSerializer(source="documents", many=True, read_only=True)

    class Meta:
        model = Requirement
        fields = '__all__'  # Include 'documents' and 'documents_data'
        
    def get_documents_data(self, obj):
        # Return a list of document file URLs or an empty list
        return [{"file": document.file.url} for document in obj.documents.all()]
    def create(self, validated_data):
        documents = validated_data.pop("documents", [])
        requirement = Requirement.objects.create(**validated_data)
        for document in documents:
            Document.objects.create(requirements=requirement, file=document)
        return requirement

    def update(self, instance, validated_data):
        documents = validated_data.pop("documents", [])
        instance = super().update(instance, validated_data)
        for document in documents:
            Document.objects.create(requirements=instance, file=document)
        return instance



# quotatiio



