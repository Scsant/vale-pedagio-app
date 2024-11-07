import streamlit as st
import json
import os
from datetime import datetime, timedelta
import requests
from lxml import etree

# Configurações e constantes
FILE_PATH = "placas_grupos.json"
ADMIN_PASSWORD = "supervisor123"  # Senha para acessar a área de administração
SENHA_PRINCIPAL = "Bracell@258"  # Senha para acessar a aplicação


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

# Função para autenticar o usuário
def autenticar_usuario():
    st.write("Autenticando usuário...")
    url = 'https://apphom.viafacil.com.br/wsvp/ValePedagio'
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'autenticarUsuario'
    }
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

    codigodeacesso = etree.SubElement(autenticar_usuario, 'codigodeacesso', attrib={etree.QName('xsi', 'type'): 'xsd:string'})
    codigodeacesso.text = '53943098000187'
    login = etree.SubElement(autenticar_usuario, 'login', attrib={etree.QName('xsi', 'type'): 'xsd:string'})
    login.text = 'ADMINISTRADOR'
    senha = etree.SubElement(autenticar_usuario, 'senha', attrib={etree.QName('xsi', 'type'): 'xsd:string'})
    senha.text = 'grupostp'

    soap_request = etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    try:
        response = requests.post(url, data=soap_request, headers=headers, timeout=10)
        response.raise_for_status()

        st.write("Resposta SOAP do servidor:")
        st.write(response.content.decode('utf-8'))

        response_content = etree.fromstring(response.content)
        response_content = remove_namespaces(response_content)

        autenticar_usuario_return = response_content.find('.//autenticarUsuarioReturn')
        if autenticar_usuario_return is not None:
            sessao_element = autenticar_usuario_return.find('.//sessao')
            if sessao_element is not None:
                sessao = sessao_element.text
                st.write(f"Sessão obtida: {sessao}")
                return sessao
        st.error("Erro: Elemento 'sessao' não encontrado ou autenticação falhou.")
        return None

    except requests.exceptions.RequestException as e:
        st.error(f"Erro na requisição SOAP: {e}")
        return None

# Função para processar a viagem
def processar_viagem(placa, fazenda):
    global placa_grupos
    placa_grupos = carregar_placas()  # Recarregar os dados de grupos de placas

    sessao = autenticar_usuario()
    if not sessao:
        st.error("Erro ao autenticar o usuário.")
        return

    grupo = encontrar_grupo(placa)
    if not grupo:
        st.error(f"A placa {placa} não está cadastrada em nenhum grupo.")
        return

    nEixosIda, nEixosVolta = definir_eixos(grupo)
    if nEixosIda is None or nEixosVolta is None:
        st.error("Erro ao definir os eixos para o grupo.")
        return

    inicioVigencia = datetime.today().strftime('%Y-%m-%d')
    fimVigencia = (datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d')
    rotas = [{'ida': f'FAZ {fazenda} - IDA', 'volta': f'FAZ {fazenda} - VOLTA'}]

    for rota in rotas:
        numero_viagem_ida = comprar_viagem(sessao, rota['ida'], placa, nEixosIda, inicioVigencia, fimVigencia)
        if numero_viagem_ida:
            imprimir_recibo(sessao, numero_viagem_ida, True)
        else:
            st.error(f"Falha na compra da viagem de ida para {rota['ida']}")

        numero_viagem_volta = comprar_viagem(sessao, rota['volta'], placa, nEixosVolta, inicioVigencia, fimVigencia)
        if numero_viagem_volta:
            imprimir_recibo(sessao, numero_viagem_volta, True)
        else:
            st.error(f"Falha na compra da viagem de volta para {rota['volta']}")

    st.success("Processo de compra e impressão de recibo concluído.")

# Função para comprar viagem
def comprar_viagem(sessao, rota, placa, nEixos, inicioVigencia, fimVigencia):
    url = 'https://apphom.viafacil.com.br/wsvp/ValePedagio'
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'comprarViagem'
    }

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

    etree.SubElement(comprar_viagem, 'sessao', attrib={etree.QName('xsi', 'type'): 'xsd:long'}).text = sessao
    etree.SubElement(comprar_viagem, 'rota', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = rota
    etree.SubElement(comprar_viagem, 'placa', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = placa
    etree.SubElement(comprar_viagem, 'nEixos', attrib={etree.QName('xsi', 'type'): 'xsd:int'}).text = str(nEixos)
    etree.SubElement(comprar_viagem, 'inicioVigencia', attrib={etree.QName('xsi', 'type'): 'xsd:date'}).text = inicioVigencia
    etree.SubElement(comprar_viagem, 'fimVigencia', attrib={etree.QName('xsi', 'type'): 'xsd:date'}).text = fimVigencia

    soap_request = etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    try:
        response = requests.post(url, data=soap_request, headers=headers, timeout=10)
        response.raise_for_status()
        st.write("Resposta completa do servidor para rota:", rota)
        st.code(response.content.decode('utf-8'))
        root = etree.fromstring(response.content)
        root = remove_namespaces(root)

        numero = root.find('.//numero')
        status = root.find('.//status')

        if status is not None and status.text == '0':
            st.write(f"Compra realizada com sucesso para rota {rota}. Número da viagem: {numero.text}")
            return numero.text
        else:
            st.error(f"Erro na compra da viagem para rota {rota}: Código de status {status.text if status else 'indefinido'}")
            return None

    except Exception as e:
        st.error(f"Erro ao processar a resposta para rota {rota}: {e}")
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
        response = requests.post(url_impressao, data=payload)
        response.raise_for_status()
        st.write(f"Recibo da viagem {numero_viagem} foi impresso com sucesso.")
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao imprimir o recibo para a viagem {numero_viagem}: {e}")



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
password = st.text_input("Digite a senha para acessar a aplicação:", type="password")
if password == SENHA_PRINCIPAL:
    st.title("Formulário de Vale Pedágio")

    # Processamento de viagem - Acesso para todos
    placa = st.text_input("Placa para processar viagem:")
    fazenda = st.text_input("Fazenda:")

    if st.button("Processar Viagem"):
        if placa and fazenda:
            processar_viagem(placa, fazenda)
        else:
            st.warning("Por favor, preencha todos os campos!")

    # Área de administração - Protegida por senha adicional
    with st.expander("Área de Administração - Supervisores Somente"):
        senha_admin = st.text_input("Senha para acessar a administração:", type="password", key="admin_password")
        if senha_admin == ADMIN_PASSWORD:
            st.success("Acesso concedido à área de administração.")

            # Botão para redefinir todos os grupos de placas
            if st.button("Redefinir todos os grupos de placas"):
                os.remove(FILE_PATH)
                placa_grupos = carregar_placas()  # Recarregar dados iniciais
                st.success("Todos os grupos foram redefinidos.")

            # Interface para gerenciar placas em cada grupo
            for grupo in placa_grupos.keys():
                st.subheader(f"Grupo {grupo}")
                placas = placa_grupos[grupo]
                st.write(", ".join(placas) if placas else "Nenhuma placa cadastrada.")

                # Adicionar múltiplas placas usando a função `adicionar_placas_a_grupo`
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
else:
    st.warning("Por favor, insira a senha para acessar a aplicação.")import streamlit as st
import json
import os
from datetime import datetime, timedelta
import requests
from lxml import etree

# Configurações e constantes
FILE_PATH = "placas_grupos.json"
ADMIN_PASSWORD = "supervisor123"  # Senha para acessar a área de administração
SENHA_PRINCIPAL = "Bracell@258"  # Senha para acessar a aplicação


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

# Função para autenticar o usuário
def autenticar_usuario():
    st.write("Autenticando usuário...")
    url = 'https://apphom.viafacil.com.br/wsvp/ValePedagio'
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'autenticarUsuario'
    }
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

    codigodeacesso = etree.SubElement(autenticar_usuario, 'codigodeacesso', attrib={etree.QName('xsi', 'type'): 'xsd:string'})
    codigodeacesso.text = '53943098000187'
    login = etree.SubElement(autenticar_usuario, 'login', attrib={etree.QName('xsi', 'type'): 'xsd:string'})
    login.text = 'ADMINISTRADOR'
    senha = etree.SubElement(autenticar_usuario, 'senha', attrib={etree.QName('xsi', 'type'): 'xsd:string'})
    senha.text = 'grupostp'

    soap_request = etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    try:
        response = requests.post(url, data=soap_request, headers=headers, timeout=10)
        response.raise_for_status()

        st.write("Resposta SOAP do servidor:")
        st.write(response.content.decode('utf-8'))

        response_content = etree.fromstring(response.content)
        response_content = remove_namespaces(response_content)

        autenticar_usuario_return = response_content.find('.//autenticarUsuarioReturn')
        if autenticar_usuario_return is not None:
            sessao_element = autenticar_usuario_return.find('.//sessao')
            if sessao_element is not None:
                sessao = sessao_element.text
                st.write(f"Sessão obtida: {sessao}")
                return sessao
        st.error("Erro: Elemento 'sessao' não encontrado ou autenticação falhou.")
        return None

    except requests.exceptions.RequestException as e:
        st.error(f"Erro na requisição SOAP: {e}")
        return None

# Função para processar a viagem
def processar_viagem(placa, fazenda):
    global placa_grupos
    placa_grupos = carregar_placas()  # Recarregar os dados de grupos de placas

    sessao = autenticar_usuario()
    if not sessao:
        st.error("Erro ao autenticar o usuário.")
        return

    grupo = encontrar_grupo(placa)
    if not grupo:
        st.error(f"A placa {placa} não está cadastrada em nenhum grupo.")
        return

    nEixosIda, nEixosVolta = definir_eixos(grupo)
    if nEixosIda is None or nEixosVolta is None:
        st.error("Erro ao definir os eixos para o grupo.")
        return

    inicioVigencia = datetime.today().strftime('%Y-%m-%d')
    fimVigencia = (datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d')
    rotas = [{'ida': f'FAZ {fazenda} - IDA', 'volta': f'FAZ {fazenda} - VOLTA'}]

    for rota in rotas:
        numero_viagem_ida = comprar_viagem(sessao, rota['ida'], placa, nEixosIda, inicioVigencia, fimVigencia)
        if numero_viagem_ida:
            imprimir_recibo(sessao, numero_viagem_ida, True)
        else:
            st.error(f"Falha na compra da viagem de ida para {rota['ida']}")

        numero_viagem_volta = comprar_viagem(sessao, rota['volta'], placa, nEixosVolta, inicioVigencia, fimVigencia)
        if numero_viagem_volta:
            imprimir_recibo(sessao, numero_viagem_volta, True)
        else:
            st.error(f"Falha na compra da viagem de volta para {rota['volta']}")

    st.success("Processo de compra e impressão de recibo concluído.")

# Função para comprar viagem
def comprar_viagem(sessao, rota, placa, nEixos, inicioVigencia, fimVigencia):
    url = 'https://apphom.viafacil.com.br/wsvp/ValePedagio'
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'comprarViagem'
    }

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

    etree.SubElement(comprar_viagem, 'sessao', attrib={etree.QName('xsi', 'type'): 'xsd:long'}).text = sessao
    etree.SubElement(comprar_viagem, 'rota', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = rota
    etree.SubElement(comprar_viagem, 'placa', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = placa
    etree.SubElement(comprar_viagem, 'nEixos', attrib={etree.QName('xsi', 'type'): 'xsd:int'}).text = str(nEixos)
    etree.SubElement(comprar_viagem, 'inicioVigencia', attrib={etree.QName('xsi', 'type'): 'xsd:date'}).text = inicioVigencia
    etree.SubElement(comprar_viagem, 'fimVigencia', attrib={etree.QName('xsi', 'type'): 'xsd:date'}).text = fimVigencia

    soap_request = etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    try:
        response = requests.post(url, data=soap_request, headers=headers, timeout=10)
        response.raise_for_status()
        st.write("Resposta completa do servidor para rota:", rota)
        st.code(response.content.decode('utf-8'))
        root = etree.fromstring(response.content)
        root = remove_namespaces(root)

        numero = root.find('.//numero')
        status = root.find('.//status')

        if status is not None and status.text == '0':
            st.write(f"Compra realizada com sucesso para rota {rota}. Número da viagem: {numero.text}")
            return numero.text
        else:
            st.error(f"Erro na compra da viagem para rota {rota}: Código de status {status.text if status else 'indefinido'}")
            return None

    except Exception as e:
        st.error(f"Erro ao processar a resposta para rota {rota}: {e}")
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
        response = requests.post(url_impressao, data=payload)
        response.raise_for_status()
        st.write(f"Recibo da viagem {numero_viagem} foi impresso com sucesso.")
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao imprimir o recibo para a viagem {numero_viagem}: {e}")



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
password = st.text_input("Digite a senha para acessar a aplicação:", type="password")
if password == SENHA_PRINCIPAL:
    st.title("Formulário de Vale Pedágio")

    # Processamento de viagem - Acesso para todos
    placa = st.text_input("Placa para processar viagem:")
    fazenda = st.text_input("Fazenda:")

    if st.button("Processar Viagem"):
        if placa and fazenda:
            processar_viagem(placa, fazenda)
        else:
            st.warning("Por favor, preencha todos os campos!")

    # Área de administração - Protegida por senha adicional
    with st.expander("Área de Administração - Supervisores Somente"):
        senha_admin = st.text_input("Senha para acessar a administração:", type="password", key="admin_password")
        if senha_admin == ADMIN_PASSWORD:
            st.success("Acesso concedido à área de administração.")

            # Botão para redefinir todos os grupos de placas
            if st.button("Redefinir todos os grupos de placas"):
                os.remove(FILE_PATH)
                placa_grupos = carregar_placas()  # Recarregar dados iniciais
                st.success("Todos os grupos foram redefinidos.")

            # Interface para gerenciar placas em cada grupo
            for grupo in placa_grupos.keys():
                st.subheader(f"Grupo {grupo}")
                placas = placa_grupos[grupo]
                st.write(", ".join(placas) if placas else "Nenhuma placa cadastrada.")

                # Adicionar múltiplas placas usando a função `adicionar_placas_a_grupo`
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
else:
    st.warning("Por favor, insira a senha para acessar a aplicação.")
    if st.button("Processar Viagem"):
        if placa and fazenda and conjunto:
            processar_viagem(placa, fazenda, conjunto)
        else:
            st.warning("Por favor, preencha todos os campos!")
