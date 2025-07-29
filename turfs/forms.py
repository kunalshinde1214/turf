from django import forms
from .models import Turf, TurfReview, TurfCategory


class TurfForm(forms.ModelForm):
    class Meta:
        model = Turf
        fields = [
            'name', 'description', 'category', 'address', 'city', 'state', 'pincode',
            'surface_type', 'length', 'width', 'capacity', 'price_per_hour',
            'weekend_price_multiplier', 'features', 'main_image'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'features':
                field.widget = forms.CheckboxSelectMultiple(choices=[
                    ('parking', 'Parking'),
                    ('washroom', 'Washroom'),
                    ('lighting', 'Floodlights'),
                    ('changing_room', 'Changing Room'),
                    ('cafeteria', 'Cafeteria'),
                    ('first_aid', 'First Aid'),
                    ('security', '24/7 Security'),
                    ('equipment', 'Equipment Rental'),
                ])
            elif field_name in ['surface_type', 'category']:
                field.widget.attrs['class'] = 'form-select'
            elif field_name == 'description':
                field.widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
            elif field_name == 'main_image':
                field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs['class'] = 'form-control'


class TurfReviewForm(forms.ModelForm):
    class Meta:
        model = TurfReview
        fields = ['rating', 'comment']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].widget = forms.Select(
            choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
            attrs={'class': 'form-select'}
        )
        self.fields['comment'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Share your experience...'
        })


class TurfSearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search turfs, cities...'
        })
    )
    category = forms.ModelChoiceField(
        queryset=TurfCategory.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City'
        })
    )
    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min Price'
        })
    )
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max Price'
        })
    )
    sort = forms.ChoiceField(
        choices=[
            ('name', 'Name'),
            ('price_low', 'Price: Low to High'),
            ('price_high', 'Price: High to Low'),
            ('rating', 'Highest Rated'),
            ('newest', 'Newest First'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )