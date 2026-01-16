/* ==========================================================
   DOCUMENT READY
========================================================== */
$(document).ready(function () {
    /* ---------- 1. SELECT2 ---------- */ function inicializarSelects() {
        if (!$.fn.select2) return;

        $('#id_natureza').select2({
            theme: 'bootstrap-5',
            placeholder: '🔍 Digite o nome (ou alias) do crime...',
            allowClear: true,
            width: '100%',
            dropdownParent: $('#fato'),
            language: {
                noResults: () => 'Nenhuma natureza encontrada',
                searching: () => 'Buscando...',
            }, // ---- CÓDIGO AJAX (Mantido) ----
            minimumInputLength: 3, // Começa a buscar após 3 caracteres
            ajax: {
                // Use o nome da rota URL do Django. Crie essa rota em urls.py!
                url: "{% url 'buscar_naturezas_ajax' %}",
                dataType: 'json',
                delay: 250, // Espera 250ms após a digitação
                data: function (params) {
                    return {
                        q: params.term, // 'q' é o termo enviado para a view Python
                    };
                },
                processResults: function (data) {
                    // A View Python já formatou como Select2 espera, então só retornamos
                    return {
                        results: data.results,
                    };
                },
                cache: true,
            }, // -------------------------
        });

        $('#id_opm').select2({
            theme: 'bootstrap-5',
            width: '100%',
        });
    }
    inicializarSelects();

    /* ------------------------------------------------------------------
     * HANDLER PARA CADASTRO RÁPIDO DE NATUREZA (Chamada de Modal)
     * Deve ser colocado aqui para que o botão seja funcional
     * ------------------------------------------------------------------
     */
    $('#btn-add-natureza').on('click', function (e) {
        e.preventDefault();
        abrirModalNatureza();
    });

    // Handler para submissão do formulário dentro do modal
    // Exemplo de código jQuery para submeter o modal
    $('#form-add-natureza').on('submit', function (e) {
        e.preventDefault(); // CRÍTICO: Previne a submissão padrão para /nova/

        // Certifique-se de que a URL de destino está correta no AJAX
        let url_destino = $(this).attr('action'); // Pega a URL definida no 'action' do form (correto)

        // OU, se você definiu a URL diretamente no JS, certifique-se que é:
        // let url_destino = "/naturezas/novo/";

        $.ajax({
            type: 'POST',
            url: url_destino, // Usa a URL correta
            data: $(this).serialize(),
            // ... (código de sucesso/erro) ...
        });
    }); /* ---------- 2. NAVEGAÇÃO ENTRE ABAS ---------- */
    /* ------------------------------------------------------------------ */

    // ... (Mantido)
    $('.next-tab').on('click', function () {
        const next = $('.nav-pills .active').parent().next().find('button');
        if (next.length) new bootstrap.Tab(next[0]).show();
        window.scrollTo(0, 0);
    });

    $('.prev-tab').on('click', function () {
        const prev = $('.nav-pills .active').parent().prev().find('button');
        if (prev.length) new bootstrap.Tab(prev[0]).show();
        window.scrollTo(0, 0);
    }); /* ---------- 3. LÓGICA CVLI ---------- */

    // ... (Mantido)
    function verificarCVLI() {
        const crimes = [
            'HOMICÍDIO DOLOSO',
            'FEMINICÍDIO',
            'ABORTO',
            'LESÃO CORPORAL SEGUIDA DE MORTE',
            'ROUBO COM MORTE',
            'LATROCÍNIO',
            'ROUBO A PEDESTRE COM MORTE',
            'ROUBO A RESIDÊNCIA COM MORTE',
            'ROUBO A ESTABELECIMENTO COM MORTE',
            'ROUBO A ESTABELECIMENTO BANCÁRIO COM MORTE',
            'INSTIGAÇÃO AO SUICÍDIO',
        ];

        const texto = $('#id_natureza option:selected').text().toUpperCase();
        const div = $('#div_instrumento');

        crimes.some((c) => texto.includes(c)) ? div.show() : div.hide();
    }

    $('#id_natureza').on('change', verificarCVLI);
    verificarCVLI(); /* ---------- 4. FORMSETS ---------- */

    // ... (Mantido)
    function addRow(prefix) {
        const totalForms = $(`#id_${prefix}-TOTAL_FORMS`);
        const index = parseInt(totalForms.val());

        const templateId = {
            envolvidos: 'envolvido-template',
            apreensoes: 'apreensao-template',
            imagens: 'imagem-template',
        }[prefix];

        let html = $(`#${templateId}`)
            .html()
            .replace(/__prefix__/g, index);

        const container = {
            envolvidos: '#envolvidos-container',
            apreensoes: '#apreensoes-formset-container',
            imagens: '#imagens-container',
        }[prefix];

        $(container).append(html);
        totalForms.val(index + 1);

        if (prefix !== 'imagens' && $.fn.select2) {
            $(container).find('select').select2({ theme: 'bootstrap-5', width: '100%' });
        }
    }

    $('#add-envolvido-btn').click(() => addRow('envolvidos'));
    $('#add-apreensao-btn').click(() => addRow('apreensoes'));
    $('#add-imagem-btn').click(() => addRow('imagens'));

    $(document).on('click', '.remove-formset-row', function () {
        const row = $(this).closest('.envolvido-form, .form-apreensao-item, .imagem-form-bloco');
        const idField = row.find('input[name$="-id"]');

        if (idField.val()) {
            row.find('input[name$="-DELETE"]').val('on');
            row.hide();
        } else {
            row.remove();
        }
    });
});

/* ==========================================================
   NATUREZA (AJAX) ⭐️ NOVO BLOCO ⭐️
========================================================== */
function abrirModalNatureza() {
    // Inicializa e mostra o modal do Bootstrap
    const modalNatureza = new bootstrap.Modal(document.getElementById('modalNatureza'));
    modalNatureza.show();
    $('#id_natureza_nome_modal').focus();
}

function fecharModalNatureza() {
    // Fecha e limpa o modal
    const modalInstance = bootstrap.Modal.getInstance(document.getElementById('modalNatureza'));
    if (modalInstance) modalInstance.hide();
    $('#form-add-natureza')[0].reset();
    $('#natureza-modal-errors').html('');
}

function salvarNaturezaRapida() {
    var $form = $('#form-add-natureza');

    // Pega a URL: prioriza o 'action' do form, senão usa o data-url do botão.
    var url = $form.attr('action') || $('#btn-salvar-natureza').data('url');

    // Token CSRF é coletado
    var csrfToken = $('[name="csrfmiddlewaretoken"]').val();

    // Cria o objeto de dados a ser enviado (garantindo os campos obrigatórios)
    var dados_para_enviar = {
        csrfmiddlewaretoken: csrfToken,
        nome: $('#id_natureza_nome_modal').val(),
        tipo_impacto: $('#id_natureza_aspecto_modal').val(),
    };

    // **DEBUG:** Mostra o que será enviado.
    console.log('Dados a serem enviados:', dados_para_enviar);

    // --- Requisição AJAX ---
    $.ajax({
        type: 'POST',
        url: url,
        data: dados_para_enviar, // <-- VÍRGULA CORRIGIDA AQUI!
        headers: {
            'X-CSRFToken': csrfToken,
        },
        success: function (response) {
            if (response.success) {
                // Sucesso: Adiciona a nova Natureza ao Select2
                var newOption = new Option(response.text, response.id, true, true);
                $('#id_natureza').append(newOption).trigger('change');

                // Fecha o modal e limpa o formulário
                $('#modalNatureza').modal('hide'); // Use o ID correto do modal: #modalNatureza
                $form[0].reset();

                alert('Natureza cadastrada com sucesso!');
            } else {
                // Falha de validação (retorno 400 OK na resposta success)
                alert('Erro de validação: ' + JSON.stringify(response.errors));
                // Opcional: Exibir erros no div #natureza-modal-errors
            }
        },
        error: function (xhr) {
            // Falha de Servidor (400 ou 500)
            var errors = JSON.parse(xhr.responseText).errors;

            // Exibir erro no modal e no console
            $('#natureza-modal-errors').html('Falha: ' + JSON.stringify(errors));
            alert(
                'Erro ao salvar Natureza. Verifique o console. Detalhes: ' + JSON.stringify(errors)
            );
            console.error('AJAX Error:', errors);
        },
    });
}

/* ==========================================================
   INSTRUMENTO (AJAX)
========================================================== */
// ... (Mantido)
function abrirModalInstrumento() {
    $('#modalInstrumento, #overlayInst').show();
}

function fecharModalInstrumento() {
    $('#modalInstrumento, #overlayInst').hide();
    $('#novo_nome_instrumento').val('');
}

function salvarInstrumentoRapido() {
    const nome = $('#novo_nome_instrumento').val().trim();
    if (!nome) return alert('Digite o nome do instrumento.');

    fetch("{% url 'adicionar_instrumento_ajax' %}", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val(),
        },
        body: 'nome=' + encodeURIComponent(nome),
    })
        .then((r) => r.json())
        .then((data) => {
            const select = $('#id_instrumento');
            select.append(new Option(data.nome, data.id, true, true)).trigger('change');
            fecharModalInstrumento();
        });
}

/* ==========================================================
   MATERIAL APREENDIDO (AJAX)
========================================================== */
// ... (Mantido)
let selectMaterialAtual = null;

function abrirModalMaterial(botao) {
    selectMaterialAtual = botao.closest('.input-group').querySelector('select');
    $('#modalMaterial, #overlayMaterial').show();
    $('#novo_nome_material').focus();
}

function fecharModalMaterial() {
    $('#modalMaterial, #overlayMaterial').hide();
    $('#novo_nome_material').val('');
    selectMaterialAtual = null;
}

function salvarMaterialRapido() {
    const nome = $('#novo_nome_material').val().trim();
    if (!nome) {
        alert('Informe o nome do material.');
        return;
    }

    const urlEl = document.querySelector('[data-url]');
    if (!urlEl) {
        console.error('data-url não encontrado no botão.');
        alert('Erro interno de configuração.');
        return;
    }

    const url = urlEl.getAttribute('data-url');

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val(),
        },
        body: 'nome=' + encodeURIComponent(nome),
    })
        .then((response) => {
            // Caso Django tenha redirecionado (login, APPEND_SLASH, etc.)
            if (response.redirected) {
                console.error('Redirect detectado:', response.url);
                alert('Sua sessão expirou. Faça login novamente.');
                window.location.href = response.url;
                return null;
            }

            if (!response.ok) {
                return response.text().then((text) => {
                    console.error('Erro HTTP:', response.status, text);
                    throw new Error('HTTP ' + response.status);
                });
            }

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                return response.text().then((text) => {
                    console.error('Resposta não é JSON:', text);
                    throw new Error('Resposta inesperada do servidor');
                });
            }

            return response.json();
        })
        .then((data) => {
            if (!data.id) {
                alert(data.error || 'Erro ao salvar material');
                return;
            }

            const option = new Option(data.nome, data.id, true, true);
            selectMaterialAtual.append(option);
            $(selectMaterialAtual).trigger('change');

            if (!data.created) {
                alert('Material já existia e foi selecionado.');
            }

            fecharModalMaterial();
        })

        .catch((err) => {
            console.error('Falha AJAX Material:', err);
            alert('Erro ao salvar material.');
        });
}
