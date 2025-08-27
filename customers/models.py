import uuid
from django.db import models



class KitchenType(models.Model):
    TYPES = [
        ('WPC', 'WPC'),
        ('SS', 'Stainless Steel'),
        ('Hybrid', 'Hybrid'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='kitchen_types')
    type = models.CharField(max_length=20, choices=TYPES)
    count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.type} - {self.count}"



# class Customer(models.Model):
#     STATES = [
#         ('Lead', 'Lead'),
#         ('Pipeline', 'Pipeline'),
#         ('Design', 'Design'),
#         ('Confirmation', 'Confirmation'),
#         ('Production', 'Production'),
#         ('Installation', 'Installation'),
#         ('Sign Out', 'Sign Out'),
#     ]

#     customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  
#     name = models.CharField(max_length=255)
#     location = models.CharField(max_length=255)
#     contact_number = models.CharField(max_length=15)
#     state = models.CharField(max_length=20, choices=STATES, default='Lead')
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.name

class Customer(models.Model):
    STATES = [
        ('Lead', 'Lead'),
        ('Pipeline', 'Pipeline'),
        ('Design', 'Design'),
        ('Confirmation', 'Confirmation'),
        ('Production', 'Production'),
        ('Installation', 'Installation'),
        ('Sign Out', 'Sign Out'),
    ]

    

    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)   
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=15)
    state = models.CharField(max_length=20, choices=STATES, default='Lead')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 2. Add the new status field to the model
    is_active = models.BooleanField(default=True)


    def __str__(self):
        # Optional: You can also add the status to the string representation
        return f"{self.name} ({self.get_status_display()})"
 
    
class Document(models.Model):
    DOCUMENT_CHOICES = [
        ('site_photos_and_measurements', 'Site Photos and Measurements'),
        ('plan_and_elevation', 'Plan and Elevation'),
        ('3d', '3D'),
        ('ept', 'EPT'),
        ('factory_quotation', 'Factory Quotation'),
        ('client_quotation', 'Client Quotation'),
        ('appliances', 'Appliances'),
        ('counter_tops_with_sink_and_faucet', 'Counter Tops with Sink and Faucet'),
        ('site_completion_photos', 'Site Completion Photos'),
    ]
    
    name = models.CharField(
        max_length=255,
        choices=DOCUMENT_CHOICES,
        default='site_photos_and_measurements',
        help_text="Select the name/title for the document."
    )
    file = models.FileField(upload_to="customer_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # This will display the human-friendly version of the choice
        return self.get_name_display()
    
class Requirement(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="requirements")

    # cabinet
    cabinet_wpc = models.BooleanField(default=False)
    cabinet_ss = models.BooleanField(default=False)

    # Door Material
    door_wpc = models.BooleanField(default=False)
    door_ss = models.BooleanField(default=False)

    # Finish Options
    finish_glax = models.BooleanField(default=False)
    finish_ceramic = models.BooleanField(default=False)
    finish_glass = models.BooleanField(default=False)
    finish_pu = models.BooleanField(default=False)
    finish_laminate = models.BooleanField(default=False)

    # Layout
    layout_l_shape = models.BooleanField(default=False)
    layout_u_shape = models.BooleanField(default=False)
    layout_c_shape = models.BooleanField(default=False)
    layout_g_shape = models.BooleanField(default=False)
    layout_island = models.BooleanField(default=False)
    layout_linear = models.BooleanField(default=False)
    layout_parallel = models.BooleanField(default=False)

    # Design
    design_island = models.BooleanField(default=False)
    design_breakfast = models.BooleanField(default=False)
    design_bar_unit = models.BooleanField(default=False)
    design_pantry_unit = models.BooleanField(default=False)

    # Cabinets and Storage
    cabinet_tall_units = models.BooleanField(default=False)
    cabinet_base_units = models.BooleanField(default=False)
    cabinet_wall_units = models.BooleanField(default=False)
    cabinet_loft_units = models.BooleanField(default=False)

    # Base Units
    base_drawers = models.BooleanField(default=False)
    base_hinge_doors = models.BooleanField(default=False)
    base_pullouts = models.BooleanField(default=False)
    base_wicker_basket = models.BooleanField(default=False)
    # Wall Unit
    wall_unit_imove = models.BooleanField(default=False)
    wall_hinge_doors = models.BooleanField(default=False)
    wall_bifold_liftup = models.BooleanField(default=False)
    wall_bifold_motorised = models.BooleanField(default=False)
    wall_flapup = models.BooleanField(default=False)
    wall_rolling_shutter = models.BooleanField(default=False)

    # Tall Unit
    tall_unit_pantry_pullout = models.BooleanField(default=False)
    lavido_pullout = models.BooleanField(default=False)
    tall_unit_ss_shelves = models.BooleanField(default=False)
    tall_unit_glass_shelf = models.BooleanField(default=False)

    # Handles
    handle_g = models.BooleanField(default=False)
    handle_j = models.BooleanField(default=False)
    handle_gola = models.BooleanField(default=False)
    handle_lip_profile = models.BooleanField(default=False)
    handle_expose_handless = models.BooleanField(default=False)
    inbuilt_handles = models.BooleanField(default=False)

    # Handles Color
    handle_color_rose_gold = models.BooleanField(default=False)
    handle_color_silver = models.BooleanField(default=False)
    handle_color_gold = models.BooleanField(default=False)
    handle_color_black = models.BooleanField(default=False)

    # Profile Lights
    profile_lights = models.BooleanField(default=False)

    # Ovens
    oven_built_in = models.BooleanField(default=False)
    oven_free_standing = models.BooleanField(default=False)

    # Refrigerators
    refrigerator_built_in = models.BooleanField(default=False)
    refrigerator_free_standing = models.BooleanField(default=False)

    # Dishwashers
    dishwasher_built_in = models.BooleanField(default=False)
    dishwasher_free_standing = models.BooleanField(default=False)

    # Coffee Makers
    coffee_maker_built_in = models.BooleanField(default=False)
    coffee_maker_free_standing = models.BooleanField(default=False)

    # Cook Tops
    cook_top_90 = models.BooleanField(default=False)
    cook_top_60 = models.BooleanField(default=False)
    cook_top_120 = models.BooleanField(default=False)

    # Sinks and Faucets
    sink_double_bowl = models.BooleanField(default=False)
    sink_single_bowl = models.BooleanField(default=False)
    sink_double_with_drain = models.BooleanField(default=False)
    sink_multifunction = models.BooleanField(default=False)

    # Sinks and Faucets Base Unit
    sink_base_drawers = models.BooleanField(default=False)
    sink_base_doors = models.BooleanField(default=False)
    sink_base_waste_bin = models.BooleanField(default=False)
    sink_base_detergent_holder = models.BooleanField(default=False)
    sink_base_detergent_pullouts = models.BooleanField(default=False)
    sink_base_wastebin_pullout = models.BooleanField(default=False)


    # Corner Solutions
    corner_solution_lemans = models.BooleanField(default=False)
    corner_solution_magic_corner = models.BooleanField(default=False)
    corner_solution_shelves = models.BooleanField(default=False)

    # Built-in Sinks
    built_in_sink_over_counter = models.BooleanField(default=False)
    built_in_sink_under_counter = models.BooleanField(default=False)

    # Countertops
    countertop_quartz = models.BooleanField(default=False)
    countertop_granite = models.BooleanField(default=False)
    countertop_tiles = models.BooleanField(default=False)

    # Timeline
    timeline_45_60_days = models.BooleanField(default=False)
    timeline_60_90_days = models.BooleanField(default=False)
    timeline_above_90_days = models.BooleanField(default=False)

    # Text Fields
    aesthetics_and_colors = models.TextField(blank=True)
    interior_designer = models.TextField(blank=True)

    # Comments
    comments = models.TextField(blank=True)
    
    documents = models.ManyToManyField(Document, related_name="requirements", blank=True)

    def __str__(self):
        return f"Requirements for {self.customer.name}"
