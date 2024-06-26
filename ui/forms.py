# ui/forms.py
from django import forms

class SimulationForm(forms.Form):
    COATING_MODELS = [
        # Add actual coating models here or load them dynamically
    ]
    CLEANING_OPTIONS = [
        ('Cleaning Frequency', 'Cleaning Frequency'),
        ('Fixed Cleanings', 'Fixed Cleanings'),
        ('Reactive Cleaning', 'Reactive Cleaning'),
    ]
    GROWTH_TYPES = [
        ('gaussian', 'Gaussian'),
        ('sigmoid', 'Sigmoid'),
        ('linear', 'Linear'),
    ]
    VESSEL_TYPES = [
        ('Ship Type', 'Ship Type'),
        ('Bulk Carrier', 'Bulk Carrier'),
        ('Gas Carrier Big', 'Gas Carrier Big'),
        ('Gas Carrier Small', 'Gas Carrier Small'),
        ('Tanker', 'Tanker'),
        ('Container Ship', 'Container Ship'),
        ('General Cargo Ship', 'General Cargo Ship'),
        ('Refrigerated Cargo Carrier', 'Refrigerated Cargo Carrier'),
        ('Combination Carrier', 'Combination Carrier'),
        ('LNG Carrier Big', 'LNG Carrier Big'),
        ('LNG Carrier Small', 'LNG Carrier Small'),
        ('Ro-Ro Cargo Ship (VC)', 'Ro-Ro Cargo Ship (VC)'),
        ('Ro-Ro Cargo Ship', 'Ro-Ro Cargo Ship'),
        ('Ro-Ro Passenger Ship', 'Ro-Ro Passenger Ship'),
        ('Cruise Passenger Ship', 'Cruise Passenger Ship'),
    ]

    coating_model = forms.ChoiceField(choices=COATING_MODELS, required=True)
    cleaning_option = forms.ChoiceField(choices=CLEANING_OPTIONS, required=True)
    cleaning_frequency = forms.IntegerField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Cleaning Frequency (months)'}))
    growth_type = forms.ChoiceField(choices=GROWTH_TYPES, required=True)
    average_power = forms.FloatField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Average Power'}))
    max_speed = forms.IntegerField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Max Speed'}))
    activity = forms.FloatField(required=True, widget=forms.TextInput(attrs={'placeholder': '% Activity'}))
    region = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Region'}))
    fuel_type = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Fuel Type'}))
    fouling_type = forms.CharField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Fouling Type'}))
    vessel_type = forms.ChoiceField(choices=VESSEL_TYPES, required=True)
    dwt = forms.IntegerField(required=True, widget=forms.TextInput(attrs={'placeholder': 'DWT'}))
    distance_travelled = forms.IntegerField(required=True, widget=forms.TextInput(attrs={'placeholder': 'Distance Travelled'}))
