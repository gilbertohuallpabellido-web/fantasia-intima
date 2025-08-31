// --- CORRECCIÓN: Usamos django.jQuery en lugar de $ ---
// Esto asegura que siempre usemos la versión de jQuery del admin de Django.
(function($) {
    'use strict';
    $(document).ready(function() {
        // Seleccionamos los dos menús desplegables
        const categoriaPadreSelect = $('#id_categoria_padre');
        const subcategoriaSelect = $('#id_categoria');
        
        // Esta es la URL que creamos en el archivo urls.py
        const subcategoriaUrl = '/api/admin/get-subcategories/';

        // Función que se ejecuta cuando cambia el primer menú
        function actualizarSubcategorias() {
            const parentId = categoriaPadreSelect.val();
            
            if (parentId) {
                // Hacemos una petición al servidor para obtener las subcategorías
                $.ajax({
                    url: subcategoriaUrl,
                    data: { 'parent_id': parentId },
                    success: function(data) {
                        // Guardamos el valor que estaba seleccionado (si lo había)
                        const originalSubcategoriaId = subcategoriaSelect.val();
                        
                        // Limpiamos y llenamos el segundo menú con las nuevas opciones
                        subcategoriaSelect.html('<option value="">---------</option>');
                        $.each(data, function(key, value) {
                            subcategoriaSelect.append($('<option>', {
                                value: value.id,
                                text: value.nombre
                            }));
                        });
                        
                        // Si el valor original sigue siendo una opción válida, lo volvemos a seleccionar
                        if (subcategoriaSelect.find('option[value="' + originalSubcategoriaId + '"]').length > 0) {
                           subcategoriaSelect.val(originalSubcategoriaId);
                        }
                    },
                    error: function(xhr, status, error) {
                        // Mostramos un error en la consola si la petición falla
                        console.error("Error al obtener subcategorías: ", status, error);
                    }
                });
            } else {
                // Si no se selecciona ninguna categoría padre, vaciamos el segundo menú
                subcategoriaSelect.html('<option value="">---------</option>');
            }
        }

        // Le decimos al primer menú que ejecute la función cada vez que cambie
        categoriaPadreSelect.on('change', actualizarSubcategorias);
        
        // Si el menú de categoría padre ya tiene un valor al cargar la página (al editar),
        // disparamos el evento 'change' para cargar las subcategorías iniciales.
        if (categoriaPadreSelect.val()) {
            categoriaPadreSelect.trigger('change');
        }
    });
})(django.jQuery); // <-- Aquí pasamos django.jQuery