// Usamos el jQuery que ya viene con el admin de Django
(function($) {
    'use strict';
    // Mensaje 1: Para saber si el archivo se está cargando.
    console.log("Paso 1: Archivo dynamic_subcategories.js CARGADO.");

    $(document).ready(function() {
        // Mensaje 2: Para saber si el script se inicia.
        console.log("Paso 2: Documento listo. Iniciando script de subcategorías.");

        const categoriaPadreSelect = $('#id_categoria_padre');
        const subcategoriaSelect = $('#id_categoria');
        const subcategoriaUrl = '/api/admin/get-subcategories/';

        function actualizarSubcategorias() {
            const parentId = categoriaPadreSelect.val();
            // Mensaje 3: Para ver si detecta el cambio de categoría.
            console.log("Paso 3: Categoría Principal cambió a ID: " + parentId);

            subcategoriaSelect.html('<option value="">---------</option>');
            if (parentId) {
                $.ajax({
                    url: subcategoriaUrl,
                    data: { 'parent_id': parentId },
                    success: function(data) {
                        // Mensaje 4: Para confirmar que recibió datos del servidor.
                        console.log("Paso 4: Subcategorías recibidas del servidor: ", data);
                        
                        const originalSubcategoriaId = subcategoriaSelect.val();
                        $.each(data, function(key, value) {
                            subcategoriaSelect.append($('<option>', {
                                value: value.id,
                                text: value.nombre
                            }));
                        });
                        
                        if (subcategoriaSelect.find('option[value="' + originalSubcategoriaId + '"]').length > 0) {
                           subcategoriaSelect.val(originalSubcategoriaId);
                        }
                    },
                    error: function(xhr, status, error) {
                        // Mensaje de Error: Si la comunicación con el servidor falla.
                        console.error("¡ERROR! La petición al servidor falló: ", status, error);
                    }
                });
            }
        }

        categoriaPadreSelect.on('change', actualizarSubcategorias);
        
        // Si ya hay una categoría padre seleccionada al cargar la página
        if (categoriaPadreSelect.val()) {
            console.log("Iniciando carga automática para producto existente.");
            actualizarSubcategorias();
        }
    });
})(django.jQuery);

class Media:
    js = ('admin/js/dynamic_subcategories.js',)