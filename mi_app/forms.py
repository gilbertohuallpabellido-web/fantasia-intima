from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms import inlineformset_factory
from django.contrib.auth import get_user_model
from .models import Producto, ColorVariante, Direccion

User = get_user_model()

class RegistroForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        max_length=254,
        label="Correo electrónico",
        help_text="Requerido. Se usará para notificaciones y recuperación de cuenta."
    )
    first_name = forms.CharField(
        max_length=30, 
        required=True,
        label="Nombre(s)"
    )
    last_name = forms.CharField(
        max_length=150, 
        required=True,
        label="Apellido(s)"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con esta dirección de correo electrónico.")
        return email

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class DireccionForm(forms.ModelForm):
    class Meta:
        model = Direccion
        fields = ['alias', 'destinatario', 'direccion', 'referencia', 'ciudad', 'telefono', 'predeterminada']

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'precio', 'precio_oferta', 'categoria', 'imagen_principal', 'es_nueva_coleccion']

class ColorVarianteForm(forms.ModelForm):
    class Meta:
        model = ColorVariante
        fields = ['color', 'imagen', 'stock']

ColorVarianteFormSet = inlineformset_factory(
    Producto,
    ColorVariante,
    form=ColorVarianteForm,
    fields=['color', 'imagen', 'stock'],
    extra=1,
    can_delete=True
)

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario", 
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'})
    )
    password = forms.CharField(
        label="Contraseña", 
        widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'})
    )
