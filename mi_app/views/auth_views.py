from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model

from ..models import PedidoWhatsApp, Direccion, ConfiguracionSitio
from ..forms import RegistroForm, UserUpdateForm, DireccionForm

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, "Usuario o contraseña inválidos.")
    else:
        form = AuthenticationForm()
    
    site_config = ConfiguracionSitio.objects.first()
    return render(request, 'mi_app/login.html', {'form': form, 'site_config': site_config})


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # activación automática
            user.save()

            messages.success(request, f'¡Bienvenido, {user.username}! Tu cuenta ha sido creada. Ya puedes iniciar sesión.')
            return redirect('login')
    else:
        form = RegistroForm()

    site_config = ConfiguracionSitio.objects.first()
    return render(request, 'mi_app/registro.html', {'form': form, 'site_config': site_config})


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, '¡Tu cuenta ha sido activada exitosamente! Ya puedes iniciar sesión.')
        return redirect('login')
    else:
        messages.error(request, 'El enlace de activación es inválido o ya no es necesario. El registro ahora es automático.')
        return redirect('index')


@login_required(login_url='/login/')
def mi_cuenta(request):
    profile_form = UserUpdateForm(instance=request.user)
    address_form = DireccionForm()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # Subida de avatar desde "Mi Cuenta"
        if form_type == 'update_profile_avatar':
            avatar_file = request.FILES.get('avatar')
            profile = getattr(request.user, 'profile', None)
            if profile is None:
                messages.error(request, 'No se encontró tu perfil de usuario.')
                return redirect('mi_cuenta')
            if avatar_file:
                # Asignar sólo el avatar para no tocar otros campos
                profile.avatar = avatar_file
                profile.save(update_fields=['avatar'])
                messages.success(request, '¡Tu foto de perfil se actualizó correctamente!')
            else:
                messages.error(request, 'Selecciona una imagen para subir.')
            return redirect('mi_cuenta')

        # Eliminación de avatar desde "Mi Cuenta"
        if form_type == 'delete_avatar':
            profile = getattr(request.user, 'profile', None)
            if profile is None:
                messages.error(request, 'No se encontró tu perfil de usuario.')
                return redirect('mi_cuenta')
            if profile.avatar:
                # Al limpiar el campo, nuestras señales eliminarán el recurso antiguo
                profile.avatar = None
                profile.save(update_fields=['avatar'])
                messages.success(request, 'Tu foto de perfil fue eliminada.')
            else:
                messages.info(request, 'No tienes una foto de perfil para eliminar.')
            return redirect('mi_cuenta')

        if form_type == 'update_profile':
            profile_form = UserUpdateForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, '¡Tu perfil ha sido actualizado con éxito!')
                return redirect('mi_cuenta')

        elif form_type == 'manage_address':
            address_id = request.POST.get('address_id')
            instance = get_object_or_404(Direccion, pk=address_id, user=request.user) if address_id else None
            address_form = DireccionForm(request.POST, instance=instance)

            if address_form.is_valid():
                address = address_form.save(commit=False)
                address.user = request.user
                address.save()
                messages.success(request, '¡Dirección guardada con éxito!')
                return redirect('mi_cuenta')

        elif form_type == 'delete_address':
            address_id = request.POST.get('address_id')
            try:
                direccion_a_eliminar = Direccion.objects.get(pk=address_id, user=request.user)
                direccion_a_eliminar.delete()
                messages.success(request, 'Dirección eliminada correctamente.')
            except Direccion.DoesNotExist:
                messages.error(request, 'No se pudo encontrar la dirección para eliminar.')
            return redirect('mi_cuenta')

    pedidos = PedidoWhatsApp.objects.filter(user=request.user).order_by('-fecha_creacion')
    direcciones = Direccion.objects.filter(user=request.user).order_by('-predeterminada', 'alias')

    active_tab = request.GET.get('tab') or 'perfil'
    active_tab_color = 'var(--brand-primary)' if active_tab == 'perfil' else '#fff'

    site_config = ConfiguracionSitio.objects.first()
    context = {
        'pedidos': pedidos,
        'direcciones': direcciones,
        'profile_form': profile_form,
        'address_form': address_form,
        'activeTab': active_tab,
        'active_tab_color': active_tab_color,
        'site_config': site_config,
    }
    return render(request, 'mi_app/mi_cuenta.html', context)


# === INICIO DE LA MEJORA: Vista para eliminar la cuenta ===
@login_required
def eliminar_cuenta_view(request):
    """
    Maneja la lógica para la eliminación de la cuenta de un usuario.
    GET: Muestra la página de confirmación.
    POST: Elimina la cuenta y cierra la sesión.
    """
    if request.method == 'POST':
        user = request.user
        # Cerramos la sesión ANTES de eliminar al usuario para evitar problemas
        logout(request)
        # Eliminamos el usuario de la base de datos
        user.delete()
        messages.success(request, 'Tu cuenta ha sido eliminada permanentemente. ¡Esperamos verte de nuevo pronto!')
        return redirect('index')
    
    site_config = ConfiguracionSitio.objects.first()
    return render(request, 'mi_app/confirmar_eliminacion.html', {'site_config': site_config})
# === FIN DE LA MEJORA ===