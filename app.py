import streamlit as st
import json
import os
from datetime import datetime, timedelta
import requests
from lxml import etree
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv
import os


# Adiciona uma imagem no header usando HTML
st.markdown(
    """
    <style>
        .header-container {
            display: flex;
            justify-content: center;
            align-items: center;
            background: linear-gradient(135deg, #1f4037, #99f2c8);
           
        }
        .header-container img {
            max-width: 200px; /* Tamanho da imagem */
            margin-right: 10px; /* Espaçamento ao lado da imagem */
        }
        .header-container h1 {
            color: white; /* Cor do texto */
            font-size: 30px;
        }
    </style>
    <div class="header-container">
        <img src="https://raw.githubusercontent.com/Scsant/vale-pedagio-app/9a8cbe3dddcdadf284f1281fd864bb84097fcb31/Bracell_logo.png" alt="Logo">
        
    </div>
    """,
    unsafe_allow_html=True
)

# Conteúdo da página
st.write("Logística Florestal")


# Estilo para aplicar o gradiente
page_style = """
<style>
    /* Gradiente para o fundo */
    .stApp {
        background: linear-gradient(135deg, #1f4037, #99f2c8);
        color: white;
    }

</style>
"""

st.markdown(page_style, unsafe_allow_html=True)

# Estilos personalizados para o botão
button_style = """
<style>
    div.stButton > button {
        background-color: #333333; /* Cor de fundo escura */
        color: white;             /* Cor do texto */
        border: 1px solid #444444; /* Borda */
        padding: 0.5em 1em;       /* Espaçamento interno */
        border-radius: 5px;       /* Bordas arredondadas */
        transition: all 0.3s ease; /* Suavização ao passar o mouse */
    }
    div.stButton > button:hover {
        background-color: #555555; /* Cor ao passar o mouse */
        color: #ffffff;            /* Cor do texto ao passar o mouse */
        border: 1px solid #666666; /* Cor da borda ao passar o mouse */
    }
</style>
"""

# Aplica os estilos
st.markdown(button_style, unsafe_allow_html=True)


# Carrega as variáveis do .env
load_dotenv()


# Acessa as variáveis de ambiente
PRODUCAO_URL = os.getenv("PRODUCAO_URL")
PRODUCAO_LOGIN = os.getenv("PRODUCAO_LOGIN")
PRODUCAO_SENHA = os.getenv("PRODUCAO_SENHA")

# Dicionário de erros
ERROS = {
    "0": {"descricao": "Sucesso", "obs": ""},
    "1": {"descricao": "CNPJ, login ou senha inválidos", "obs": "Timeout da sessão ou código de sessão inválido"},
    "3": {"descricao": "Sessão expirada ou inválida", "obs": ""},
    "4": {"descricao": "Veículo não disponível", "obs": "Veículo não encontrado no sistema ou com restrições"},
    "11": {"descricao": "Prazo máximo extrapolado", "obs": "Máximo de 40 dias para extratos e 15 dias para vigência de Vale Pedágio"},
    "12": {"descricao": "Rota inválida", "obs": "Rota não encontrada no sistema"},
    "13": {"descricao": "Número de eixos inválido", "obs": "Deve ser entre 2 e 10 (ou 15 para outros serviços)"},
    "14": {"descricao": "Saldo insuficiente", "obs": "Crédito disponível menor que o valor da viagem"},
    "15": {"descricao": "Recibo não disponível", "obs": "Recibo só é retornado se a viagem não foi cancelada ou encerrada"},
    "49": {"descricao": "Viagem não pode ser cancelada", "obs": "Viagem confirmada há mais de 3 horas"},
    "51": {"descricao": "Praça(s) inválida(s)", "obs": "Formato esperado: 99-99-99"},
    "52": {"descricao": "Não foi encontrado o transportador", "obs": "Transportador não encontrado no sistema"},
    "53": {"descricao": "Viagem não pode ser reemitida", "obs": "Viagem expirada ou já reemitida"},
    "54": {"descricao": "Viagem parcialmente reconhecida", "obs": "Algumas praças não puderam ser reemitidas"},
    "55": {"descricao": "Viagem não pode ser nula", "obs": "Valor da viagem deve ser maior que R$ 0,00"},
    "58": {"descricao": "Nome de rota já existente", "obs": "Usuário tentou cadastrar uma rota já existente"},
    "59": {"descricao": "Rota inexistente", "obs": "Usuário tentou pesquisar uma rota que não existe"},
    "62": {"descricao": "Mais de um resultado encontrado", "obs": "Esperado um único valor, mas múltiplos foram encontrados"},
    "66": {"descricao": "Praça não encontrada", "obs": "Usuário tentou cadastrar uma praça inexistente"}
}

# Função para consultar o erro
def consultar_erro(codigo):
    """
    Consulta o código de erro e exibe a descrição e observações na interface.

    Parâmetros:
        codigo (str): O código do erro a ser consultado.
    """
    if codigo in ERROS:
        descricao = ERROS[codigo]["descricao"]
        obs = ERROS[codigo]["obs"]
        st.error(f"Erro {codigo}: {descricao}")
        if obs:
            st.write(f"Observação: {obs}")
    else:
        st.error("Código de erro não encontrado.")


ERROS_FILE = "erros.json"  # Arquivo para registrar erros

# Garante que o arquivo `erros.json` exista na inicialização
if not os.path.exists(ERROS_FILE):
    with open(ERROS_FILE, "w") as file:
        json.dump([], file)  # Cria um arquivo vazio para registrar os erros


def carregar_erros():
    """Carrega os erros do arquivo JSON."""
    with open(ERROS_FILE, "r") as file:
        return json.load(file)


def salvar_erros(erros):
    """Salva os erros no arquivo JSON."""
    with open(ERROS_FILE, "w") as file:
        json.dump(erros, file, indent=4)


def registrar_erro(tipo, mensagem, placa=None, fazenda=None, operador=None):
    """Registra um erro no arquivo `erros.json`."""
    erros = carregar_erros()
    novo_erro = {
        "Data/Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Tipo": tipo,
        "Mensagem": mensagem,
        "Placa": placa,
        "Fazenda": fazenda,
        "Operador": operador
    }
    erros.append(novo_erro)
    salvar_erros(erros)



USUARIOS_FILE = "usuarios.json"  # Arquivo para armazenar os usuários

# Criar o arquivo `usuarios.json` com o usuário inicial
if not os.path.exists(USUARIOS_FILE):
    with open(USUARIOS_FILE, "w") as file:
        json.dump({"sluis": "Bracell@25"}, file)  # Adiciona o usuário inicial


def carregar_usuarios():
    """Carrega os usuários do arquivo JSON."""
    with open(USUARIOS_FILE, "r") as file:
        return json.load(file)


def salvar_usuarios(usuarios):
    """Salva os usuários no arquivo JSON."""
    with open(USUARIOS_FILE, "w") as file:
        json.dump(usuarios, file, indent=4)


def cadastrar_usuario(nome_usuario, senha="Bracell@25"):
    """Cadastra um novo usuário."""
    usuarios = carregar_usuarios()
    nome_usuario = nome_usuario.lower()  # Converte para minúsculo para evitar duplicatas
    if nome_usuario in usuarios:
        return False  # Usuário já existe
    usuarios[nome_usuario] = senha  # Adiciona com a senha fornecida
    salvar_usuarios(usuarios)
    return True

# Configurações e constantes
DADOS_FILE = "dados.json"  # Arquivo para armazenar dados locais
FILE_PATH = "placas_grupos.json"
ADMIN_PASSWORD = "supervisor123"  # Senha para acessar a área de administração
SENHA_PRINCIPAL = "Bracell@258"  # Senha para acessar a aplicação
ADMIN_CONTROL_PASSWORD = "controle123" 


# Garante que o arquivo `dados.json` exista na inicialização
if not os.path.exists(DADOS_FILE):
    with open(DADOS_FILE, "w") as file:
        json.dump([], file)  # Cria o arquivo com uma lista vazia

# Função para carregar os dados do arquivo JSON
def carregar_dados():
    if os.path.exists(DADOS_FILE):
        try:
            with open(DADOS_FILE, "r") as file:
                content = file.read().strip()  # Remove espaços em branco no início e fim
                if content:  # Verifica se o arquivo não está vazio
                    return json.loads(content)
        except json.JSONDecodeError:
            st.warning(f"O arquivo {DADOS_FILE} está corrompido. Criando um novo arquivo vazio.")
            with open(DADOS_FILE, "w") as file:
                json.dump([], file)  # Recria o arquivo com lista vazia
    return []  # Retorna lista vazia se arquivo não existir ou estiver corrompido


# Função para salvar os dados no arquivo JSON
def salvar_dados(dados):
    with open(DADOS_FILE, "w") as file:
        json.dump(dados, file, indent=4)


        
def adicionar_registro(data_emissao, placa, fazenda, custo_ida, custo_volta, numero_viagem_ida, numero_viagem_volta, operador):
    dados = carregar_dados()
    novo_registro = {
        "Data/Hora": data_emissao,
        "Placa": placa,
        "Fazenda": fazenda,
        "Custo Ida": custo_ida,
        "Custo Volta": custo_volta,
        "Custo Total": custo_ida + custo_volta,
        "Numero Recibo Ida": numero_viagem_ida,
        "Numero Recibo Volta": numero_viagem_volta,
        "Operador": operador  # Adiciona o nome do operador logado
    }
    dados.append(novo_registro)
    salvar_dados(dados)



def baixar_dados_como_excel():
    dados = carregar_dados()
    if not dados:
        st.warning("Nenhum dado disponível para download.")
        return
    
    df = pd.DataFrame(dados)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Dados")
    buffer.seek(0)
    
    st.download_button(
        label="Baixar Dados como Excel",
        data=buffer,
        file_name="dados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )




# Função para carregar os dados de placas de um arquivo JSON
def carregar_placas():
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, "r") as file:
            return json.load(file)
    else:
        return {
            "Bitrem_4": [],
            "Bitrem_5": [],
            "Tritrem_5": [],
            "Tritrem_6": []
        }
placa_grupos = carregar_placas()

# Função para salvar os dados de placas em um arquivo JSON
def salvar_placas(dados):
    global placa_grupos
    with open(FILE_PATH, "w") as file:
        json.dump(dados, file, indent=4)
    placa_grupos = dados  # Atualiza a variável global

# Função para garantir que uma placa só esteja em um grupo
def remover_placa_de_outros_grupos(placa, grupo_atual):
    """Remove uma placa de todos os grupos, exceto do grupo atual."""
    for grupo, lista_placas in placa_grupos.items():
        if grupo != grupo_atual and placa in lista_placas:
            lista_placas.remove(placa)

# Função para adicionar placas a um grupo e garantir que não haja duplicatas em outros grupos
def adicionar_placas_a_grupo(grupo, placas_para_adicionar):
    global placa_grupos
    novas_placas_adicionadas = []
    
    for placa in placas_para_adicionar:
        # Remover a placa de outros grupos antes de adicionar ao grupo atual
        remover_placa_de_outros_grupos(placa, grupo)
        
        # Adicionar a placa ao grupo atual, se ainda não estiver lá
        if placa not in placa_grupos[grupo]:
            placa_grupos[grupo].append(placa)
            novas_placas_adicionadas.append(placa)

    # Salva o JSON atualizado para garantir persistência
    salvar_placas(placa_grupos)
    return novas_placas_adicionadas
# Função para remover namespaces do XML
def remove_namespaces(tree):
    for elem in tree.iter():
        elem.tag = elem.tag.split('}')[-1]
    etree.cleanup_namespaces(tree)
    return tree

def enviar_para_api(data):
    """
    Envia os dados do vale-pedágio para a API via POST.
    """
    url = "https://pedbracc.onrender.com/api/vale-pedagio/"  # Substitua pela URL da sua API em produção
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, json=data, headers=headers, verify=False)
        if response.status_code == 201:
            st.success("Dados enviados com sucesso para o banco de dados!")
            st.write(response.json())  # Opcional: exibe a resposta do servidor
        else:
            st.error(f"Erro ao enviar dados para a API: {response.status_code}")
            st.write(response.text)  # Exibe a mensagem de erro do servidor
    except Exception as e:
        st.error(f"Erro ao conectar à API: {e}")


def autenticar_usuario(ambiente="producao"):
    """
    Autentica o usuário em um ambiente específico.

    Parâmetros:
        ambiente (str): "producao" ou "homologacao".
    Retorno:
        str: Sessão autenticada ou None em caso de falha.
    """
    st.write(f"Autenticando usuário no ambiente {ambiente}...")

    # Define o URL e as credenciais com base no ambiente
    if ambiente == "producao":
        url = PRODUCAO_URL
        login = PRODUCAO_LOGIN
        senha = PRODUCAO_SENHA
    elif ambiente == "homologacao":
        url = 'https://apphom.viafacil.com.br/wsvp/ValePedagio'
        login = "ADMINISTRADOR"
        senha = "grupostp"
    else:
        st.error("Ambiente inválido. Use 'producao' ou 'homologacao'.")
        return None

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'autenticarUsuario'
    }
    
    # Construção do envelope SOAP
    envelope = etree.Element('{http://schemas.xmlsoap.org/soap/envelope/}Envelope',
                             nsmap={
                                 'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                                 'xsd': 'http://www.w3.org/2001/XMLSchema',
                                 'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                                 'cgmp': 'http://cgmp.com'
                             })
    body = etree.SubElement(envelope, '{http://schemas.xmlsoap.org/soap/envelope/}Body')
    autenticar_usuario = etree.SubElement(body, '{http://cgmp.com}autenticarUsuario',
                                          attrib={'{http://schemas.xmlsoap.org/soap/envelope/}encodingStyle': 'http://schemas.xmlsoap.org/soap/encoding/'})

    # Código de acesso é o mesmo para os dois ambientes
    codigodeacesso = etree.SubElement(autenticar_usuario, 'codigodeacesso', attrib={etree.QName('xsi', 'type'): 'xsd:string'})
    codigodeacesso.text = '53943098000187'
    etree.SubElement(autenticar_usuario, 'login', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = login
    etree.SubElement(autenticar_usuario, 'senha', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = senha

    # Cria a requisição SOAP
    soap_request = etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    try:
        response = requests.post(url, data=soap_request, headers=headers, timeout=10, verify=False)
        response.raise_for_status()

        # Parse da resposta
        response_content = etree.fromstring(response.content)
        response_content = remove_namespaces(response_content)

        autenticar_usuario_return = response_content.find('.//autenticarUsuarioReturn')
        if autenticar_usuario_return is not None:
            sessao_element = autenticar_usuario_return.find('.//sessao')
            if sessao_element is not None:
                sessao = sessao_element.text
                st.write(f"Sessão obtida para {ambiente}: {sessao}")
                return sessao
        st.error(f"Erro: Elemento 'sessao' não encontrado ou autenticação falhou no ambiente {ambiente}.")
        return None

    except requests.exceptions.RequestException as e:
        st.error(f"Erro na requisição SOAP no ambiente {ambiente}: {e}")
        return None






def processar_viagem(placa, fazenda):
    global placa_grupos
    placa_grupos = carregar_placas()  # Recarregar os dados de grupos de placas

    # Obtenha sessões para produção e homologação
    sessao = autenticar_usuario(ambiente="producao")  # Sessão para produção
    sessaoHomologacao = autenticar_usuario(ambiente="homologacao")  # Sessão para homologação
    
    if not sessao or not sessaoHomologacao:
        st.error("Erro ao autenticar o usuário.")
        registrar_erro(
            tipo="Autenticação",
            mensagem="Falha ao autenticar o usuário em produção ou homologação.",
            operador=st.session_state.get("usuario_logado")
        )
        return

    grupo = encontrar_grupo(placa)
    if not grupo:
        st.error(f"A placa {placa} não está cadastrada em nenhum grupo.")
        registrar_erro(
            tipo="Placa Não Encontrada",
            mensagem=f"Placa {placa} não encontrada em nenhum grupo.",
            placa=placa,
            fazenda=fazenda,
            operador=st.session_state.get("usuario_logado")
        )
        return

    nEixosIda, nEixosVolta = definir_eixos(grupo)
    if nEixosIda is None or nEixosVolta is None:
        st.error("Erro ao definir os eixos para o grupo.")
        registrar_erro(
            tipo="Definição de Eixos",
            mensagem=f"Não foi possível definir eixos para o grupo {grupo}.",
            placa=placa,
            fazenda=fazenda,
            operador=st.session_state.get("usuario_logado")
        )
        return
    
    if not fazenda:
        st.error("Fazenda não especificada.")
        registrar_erro(
            tipo="Fazenda Não Especificada",
            mensagem="Fazenda não foi fornecida pelo operador.",
            placa=placa,
            operador=st.session_state.get("usuario_logado")
        )
        return

    inicioVigencia = datetime.today().strftime('%Y-%m-%d')
    fimVigencia = (datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d')
    rotas = [{'ida': f'FAZ {fazenda} - IDA', 'volta': f'FAZ {fazenda} - VOLTA'}]

    for rota in rotas:
        try:
            # Obter custo da rota de ida (sessão de homologação)
            custo_ida = obter_custo_rota(sessaoHomologacao, rota['ida'], placa, nEixosIda, inicioVigencia, fimVigencia)
            if 'erro' in custo_ida:
                raise Exception(custo_ida['erro'])  # Lança uma exceção para o bloco de tratamento
            st.write(f"Custo da rota de ida ({rota['ida']}): R$ {custo_ida['valor']}")
        except Exception as e:
            st.error(f"Erro ao obter custo da rota de ida ({rota['ida']}): {e}")
            registrar_erro(
                tipo="Custo Ida",
                mensagem=f"Erro ao obter custo da rota ({rota['ida']}): {e}",
                placa=placa,
                fazenda=fazenda,
                operador=st.session_state.get("usuario_logado")
            )
            custo_ida = {'valor': 0.0}  # Define um valor padrão

        # Comprar viagem de ida (sessão de produção)
        numero_viagem_ida = comprar_viagem(sessao, rota['ida'], placa, nEixosIda, inicioVigencia, fimVigencia)
        if not numero_viagem_ida:
            st.error(f"Falha na compra da viagem de ida para {rota['ida']}")
            registrar_erro(
                tipo="Compra Ida",
                mensagem=f"Falha na compra da viagem de ida para {rota['ida']}",
                placa=placa,
                fazenda=fazenda,
                operador=st.session_state.get("usuario_logado")
            )
            continue

        try:
            # Obter custo da rota de volta (sessão de homologação)
            custo_volta = obter_custo_rota(sessaoHomologacao, rota['volta'], placa, nEixosVolta, inicioVigencia, fimVigencia)
            if 'erro' in custo_volta:
                raise Exception(custo_volta['erro'])  # Lança uma exceção para o bloco de tratamento
            st.write(f"Custo da rota de volta ({rota['volta']}): R$ {custo_volta['valor']}")
        except Exception as e:
            st.error(f"Erro ao obter custo da rota de volta ({rota['volta']}): {e}")
            registrar_erro(
                tipo="Custo Volta",
                mensagem=f"Erro ao obter custo da rota ({rota['volta']}): {e}",
                placa=placa,
                fazenda=fazenda,
                operador=st.session_state.get("usuario_logado")
            )
            custo_volta = {'valor': 0.0}  # Define um valor padrão

        # Comprar viagem de volta (sessão de produção)
        numero_viagem_volta = comprar_viagem(sessao, rota['volta'], placa, nEixosVolta, inicioVigencia, fimVigencia)
        if not numero_viagem_volta:
            st.error(f"Falha na compra da viagem de volta para {rota['volta']}")
            registrar_erro(
                tipo="Compra Volta",
                mensagem=f"Falha na compra da viagem de volta para {rota['volta']}",
                placa=placa,
                fazenda=fazenda,
                operador=st.session_state.get("usuario_logado")
            )
            continue

        # Adicionar os dados ao arquivo JSON
        adicionar_registro(
            data_emissao=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            placa=placa,
            fazenda=fazenda,
            custo_ida=float(custo_ida['valor']),
            custo_volta=float(custo_volta['valor']),
            numero_viagem_ida=numero_viagem_ida,
            numero_viagem_volta=numero_viagem_volta,
            operador=st.session_state["usuario_logado"]
        )
        
        

    st.success("Processo concluído!")



def comprar_viagem(sessao, rota, placa, nEixos, inicioVigencia, fimVigencia):
    """
    Função para comprar viagem via SOAP.

    Parâmetros:
        sessao (str): Sessão autenticada (produção ou homologação).
        rota (str): Nome da rota.
        placa (str): Placa do caminhão.
        nEixos (int): Número de eixos.
        inicioVigencia (str): Data de início da vigência (YYYY-MM-DD).
        fimVigencia (str): Data de fim da vigência (YYYY-MM-DD).

    Retorno:
        str: Número da viagem ou None em caso de falha.
    """
    url = PRODUCAO_URL
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'comprarViagem'
    }

    # Construção do envelope SOAP
    envelope = etree.Element('{http://schemas.xmlsoap.org/soap/envelope/}Envelope',
                             nsmap={
                                 'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                                 'xsd': 'http://www.w3.org/2001/XMLSchema',
                                 'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                                 'cgmp': 'http://cgmp.com'
                             })
    body = etree.SubElement(envelope, '{http://schemas.xmlsoap.org/soap/envelope/}Body')
    comprar_viagem = etree.SubElement(body, '{http://cgmp.com}comprarViagem',
                                      attrib={'{http://schemas.xmlsoap.org/soap/envelope/}encodingStyle': 'http://schemas.xmlsoap.org/soap/encoding/'})

    # Adiciona os parâmetros ao SOAP envelope
    etree.SubElement(comprar_viagem, 'sessao', attrib={etree.QName('xsi', 'type'): 'xsd:long'}).text = sessao
    etree.SubElement(comprar_viagem, 'rota', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = rota
    etree.SubElement(comprar_viagem, 'placa', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = placa
    etree.SubElement(comprar_viagem, 'nEixos', attrib={etree.QName('xsi', 'type'): 'xsd:int'}).text = str(nEixos)
    etree.SubElement(comprar_viagem, 'inicioVigencia', attrib={etree.QName('xsi', 'type'): 'xsd:date'}).text = inicioVigencia
    etree.SubElement(comprar_viagem, 'fimVigencia', attrib={etree.QName('xsi', 'type'): 'xsd:date'}).text = fimVigencia

    # Converte o envelope para string
    soap_request = etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    try:
        response = requests.post(url, data=soap_request, headers=headers, timeout=10, verify=False)
        response.raise_for_status()

        #st.code(response.content.decode('utf-8'))  # Exibe o conteúdo completo da resposta SOAP

        # Parse da resposta SOAP
        root = etree.fromstring(response.content)
        root = remove_namespaces(root)

        numero = root.find('.//numero')
        status = root.find('.//status')

        if status is not None and status.text == '0':
            st.success(f"Compra realizada com sucesso para rota {rota}. Número da viagem: {numero.text}")
            return numero.text
        else:
            # Consultar e exibir detalhes do erro
            consultar_erro(status.text)
            st.error(f"Falha na compra da viagem para {rota}.")
            return None

    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão ao servidor para rota {rota}: {e}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao processar resposta para rota {rota}: {e}")
        return None
    

# Função para imprimir recibo
def imprimir_recibo(sessao, numero_viagem, imprimir_observacoes):
    url_impressao = 'https://app.viafacil.com.br/vpnew/imprimirValePedagioSTP.do'
    payload = {
        'sessao': sessao,
        'viagem': numero_viagem,
        'imprimirObservacoes': str(imprimir_observacoes).lower()
    }

    try:
        response = requests.post(url_impressao, data=payload, verify=False)
        response.raise_for_status()
        st.write(f"Recibo da viagem {numero_viagem} foi impresso com sucesso.")
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao imprimir o recibo para a viagem {numero_viagem}: {e}")


def obter_custo_rota(sessao_homologacao, rota, placa, n_eixos, inicio_vigencia, fim_vigencia):
    url = 'https://apphom.viafacil.com.br/wsvp/ValePedagio'
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'obterCustoRota'
    }

    envelope = etree.Element('{http://schemas.xmlsoap.org/soap/envelope/}Envelope',
                             nsmap={
                                 'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                                 'xsd': 'http://www.w3.org/2001/XMLSchema',
                                 'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                                 'cgmp': 'http://cgmp.com'
                             })
    body = etree.SubElement(envelope, '{http://schemas.xmlsoap.org/soap/envelope/}Body')
    obter_custo_rota = etree.SubElement(body, '{http://cgmp.com}obterCustoRota',
                                        attrib={'{http://schemas.xmlsoap.org/soap/envelope/}encodingStyle': 'http://schemas.xmlsoap.org/soap/encoding/'})

    etree.SubElement(obter_custo_rota, 'sessao', attrib={etree.QName('xsi', 'type'): 'xsd:long'}).text = str(sessao_homologacao)
    etree.SubElement(obter_custo_rota, 'nomeRota', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = rota
    etree.SubElement(obter_custo_rota, 'placa', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = placa
    etree.SubElement(obter_custo_rota, 'nEixos', attrib={etree.QName('xsi', 'type'): 'xsd:int'}).text = str(n_eixos)
    etree.SubElement(obter_custo_rota, 'inicioVigencia', attrib={etree.QName('xsi', 'type'): 'xsd:date'}).text = inicio_vigencia
    etree.SubElement(obter_custo_rota, 'fimVigencia', attrib={etree.QName('xsi', 'type'): 'xsd:date'}).text = fim_vigencia

    soap_request = etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    try:
        response = requests.post(url, data=soap_request, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        root = etree.fromstring(response.content)
        root = remove_namespaces(root)  # Certifique-se de que esta função está definida.

        valor = root.find('.//valor')
        status = root.find('.//status')

        if status is not None and status.text == '0':
            return {'valor': valor.text if valor is not None else None, 'status': status.text}
        else:
            return {'erro': f"Código de status {status.text if status else 'indefinido'}"}
    except Exception as e:
        return {'erro': str(e)}




# Função para encontrar grupo de uma placa
def encontrar_grupo(placa):
    for grupo, placas in placa_grupos.items():
        if placa in placas:
            return grupo
    return None

# Função para determinar os eixos baseado no grupo do caminhão
def definir_eixos(grupo):
    if grupo == "Bitrem_4":
        return 4, 7
    elif grupo == "Bitrem_5":
        return 5, 7
    elif grupo == "Tritrem_5":
        return 5, 9
    elif grupo == "Tritrem_6":
        return 6, 9
    else:
        return None, None
        
# Interface Streamlit
st.title("Login")

nome_usuario = st.text_input("Usuário:").strip().lower()  # Entrada do nome de usuário (convertido para minúsculo)
senha = st.text_input("Senha:", type="password")  # Entrada de senha

# Verifica credenciais
if st.button("Entrar"):
    usuarios = carregar_usuarios()
    if nome_usuario in usuarios and senha == usuarios[nome_usuario]:
        st.success(f"Bem-vindo, {nome_usuario}!")
        st.session_state["usuario_logado"] = nome_usuario
    else:
        st.error("Usuário ou senha inválidos.")

# Exibe o restante da aplicação se o usuário estiver logado
if "usuario_logado" in st.session_state:
    st.title("Formulário de Vale Pedágio")
    st.write(f"Usuário logado: {st.session_state['usuario_logado']}")

    # Processamento de viagem
    placa = st.text_input("Placa para processar viagem:")
    fazenda = st.text_input("Fazenda:")

    if st.button("Processar Viagem"):
        if placa and fazenda:
            processar_viagem(placa, fazenda)
        else:
            st.warning("Por favor, preencha todos os campos!")

# Área de Administração - Gerenciamento de Grupos de Placas
with st.expander("Área de Administração - Somente Autorizados"):
    senha_admin = st.text_input("Senha para acessar a administração:", type="password", key="admin_password")
    
    if senha_admin == ADMIN_PASSWORD:
        st.success("Acesso concedido à área de administração.")

        # Redefinir todos os grupos de placas
        if st.button("Redefinir todos os grupos de placas"):
            os.remove(FILE_PATH)
            placa_grupos = carregar_placas()  # Recarregar dados iniciais
            st.success("Todos os grupos foram redefinidos.")

        # Gerenciamento de placas em cada grupo
        for grupo in placa_grupos.keys():
            st.subheader(f"Grupo {grupo}")
            placas = placa_grupos[grupo]
            st.write(", ".join(placas) if placas else "Nenhuma placa cadastrada.")

            # Adicionar múltiplas placas
            novas_placas = st.text_area(f"Adicionar placas ao grupo {grupo}", key=f"add_{grupo}")
            if st.button(f"Adicionar ao {grupo}", key=f"add_btn_{grupo}"):
                if novas_placas.strip():
                    placas_para_adicionar = [p.strip().upper() for p in novas_placas.replace(",", "\n").split()]
                    novas_placas_adicionadas = adicionar_placas_a_grupo(grupo, placas_para_adicionar)

                    if novas_placas_adicionadas:
                        st.success(f"Placas adicionadas ao grupo {grupo}: {', '.join(novas_placas_adicionadas)}")
                    else:
                        st.warning("Nenhuma nova placa foi adicionada.")
                else:
                    st.warning("Digite uma ou mais placas para adicionar.")

            # Remover múltiplas placas
            placas_para_remover = st.text_area(f"Remover placas do grupo {grupo}", key=f"remove_{grupo}")
            if st.button(f"Remover do {grupo}", key=f"remove_btn_{grupo}"):
                if placas_para_remover.strip():
                    placas_para_remover_lista = [p.strip().upper() for p in placas_para_remover.replace(",", "\n").split()]
                    for placa in placas_para_remover_lista:
                        if placa in placa_grupos[grupo]:
                            placa_grupos[grupo].remove(placa)
                    salvar_placas(placa_grupos)
                    st.success("Placas removidas com sucesso!")
                else:
                    st.warning("Digite uma ou mais placas para remover.")
    elif senha_admin:
        st.error("Senha incorreta para a área de administração.")

# Área de Controle - Download de Dados
with st.expander("Área de Controle - Somente Autorizados"):
    senha_controle = st.text_input("Senha para acessar o controle:", type="password", key="controle_password")
    
    if senha_controle == ADMIN_CONTROL_PASSWORD:
        st.success("Acesso concedido à área de controle.")

        # Botão para baixar os dados como Excel
        if st.button("Baixar Dados como Excel"):
            baixar_dados_como_excel()

        # Cadastro de novos usuários
        st.subheader("Gerenciamento de Usuários")
        novo_usuario = st.text_input("Nome do novo usuário:")
        nova_senha = st.text_input("Senha para o novo usuário:", type="password")

        if st.button("Cadastrar Novo Usuário"):
            if novo_usuario.strip() and nova_senha.strip():
                sucesso = cadastrar_usuario(novo_usuario, nova_senha)
                if sucesso:
                    st.success(f"Usuário '{novo_usuario}' cadastrado com sucesso!")
                else:
                    st.error(f"Usuário '{novo_usuario}' já existe.")
            else:
                st.warning("Por favor, insira um nome de usuário e senha válidos.")
    elif senha_controle:
        st.error("Senha incorreta para a área de controle.")

