from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.forms import inlineformset_factory
from django.contrib.auth import get_user_model
from .models import Producto, ColorVariante

# Importamos el modelo de usuario de Django
User = get_user_model()

# Formulario para el registro de nuevos usuarios
class CustomUserCreationForm(UserCreationForm):
    """
    Formulario de creación de usuario personalizado que incluye email, nombre y apellido.
    Hereda de UserCreationForm de Django y añade campos para un registro más completo.
    """
    email = forms.EmailField(
        required=True,
        max_length=254,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'})
    )
    first_name = forms.CharField(
        max_length=30, 
        required=True,
        label="Nombre(s)",
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'})
    )
    last_name = forms.CharField(
        max_length=150, 
        required=True,
        label="Apellido(s)",
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def save(self, commit=True):
        """
        Sobreescribe el método save para usar el correo electrónico
        como el nombre de usuario si no se proporciona uno.
        """
        user = super().save(commit=False)
        # Seteamos el username con el correo electrónico si no se ha especificado
        if not user.username:
            user.username = user.email
        
        if commit:
            user.save()
        return user

# Formulario para productos
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'precio', 'categoria', 'color_principal', 'imagen_principal']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'precio': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'categoria': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'color_principal': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'imagen_principal': forms.FileInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
        }

# Formulario para las variantes de color
class ColorVarianteForm(forms.ModelForm):
    class Meta:
        model = ColorVariante
        fields = ['color', 'imagen', 'stock']
        widgets = {
            'color': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'imagen': forms.FileInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'stock': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
        }

ColorVarianteFormSet = inlineformset_factory(
    Producto,
    ColorVariante,
    form=ColorVarianteForm,
    fields=['color', 'imagen', 'stock'],
    extra=1,
    can_delete=True
)

# Formulario para el inicio de sesión
class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario", widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}))