import streamlit as st
import requests
from lxml import etree
from datetime import datetime, timedelta

# ---- Verificação de Senha ----
# Crie uma senha para proteger a aplicação
senha = "Bracell@258"  # Substitua por uma senha segura

# Campo de entrada para a senha
password = st.text_input("Digite a senha para acessar:", type="password")

# Se a senha estiver correta, o resto da aplicação é mostrado
if password == senha:

    # Função para remover namespaces do XML
    def remove_namespaces(tree):
        """Remove namespaces de um elemento XML e seus filhos."""
        for elem in tree.getiterator():
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
            response = requests.post(url, data=soap_request, headers=headers)
            response.raise_for_status()

            # Exibindo o conteúdo da resposta no Streamlit para diagnóstico
            st.write("Resposta SOAP do servidor:")
            st.write(response.content.decode('utf-8'))

            # Remover namespaces
            response_content = etree.fromstring(response.content)
            response_content = remove_namespaces(response_content)

            # Verifica o elemento 'autenticarUsuarioReturn'
            autenticar_usuario_return = response_content.find('.//autenticarUsuarioReturn')
            if autenticar_usuario_return is not None:
                sessao_element = autenticar_usuario_return.find('.//sessao')
                if sessao_element is not None:
                    sessao = sessao_element.text
                    st.write(f"Sessão obtida: {sessao}")
                    return sessao
                else:
                    st.error("Erro: Elemento 'sessao' não encontrado dentro de 'autenticarUsuarioReturn'.")
            else:
                st.error("Erro: Elemento 'autenticarUsuarioReturn' não encontrado.")

            return None
        except requests.exceptions.RequestException as e:
            st.error(f"Erro na requisição SOAP: {e}")
            return None

    # Função para processar a viagem
    def processar_viagem(placa, fazenda, conjunto):
        # Autentica o usuário e obtém a sessão
        sessao = autenticar_usuario()
        if not sessao:
            st.error("Erro ao autenticar o usuário. Verifique as credenciais e tente novamente.")
            return

        # Definir as datas de vigência
        inicioVigencia = datetime.today().strftime('%Y-%m-%d')
        fimVigencia = (datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d')

        # Definir os eixos com base no tipo de conjunto selecionado
        if conjunto == 'Bitrem':
            nEixosIda = 4
            nEixosVolta = 7
        elif conjunto == 'Tritrem':
            nEixosIda = 6
            nEixosVolta = 9
        elif conjunto == 'Cargo Polo (5 eixos ida)':
            nEixosIda = 5
            nEixosVolta = 9
        elif conjunto == 'Cargo Polo (6 eixos ida)':
            nEixosIda = 6
            nEixosVolta = 9
        else:
            st.error("Tipo de conjunto não reconhecido.")
            return

        rotas = [
            {'ida': f'FAZ {fazenda} - IDA', 'volta': f'FAZ {fazenda} - VOLTA'},
        ]

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
    def comprar_viagem(sessao, rota, placa, nEixos, inicioVigencia, fimVigencia, itemFin1=None, itemFin2=None, itemFin3=None):
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

        if itemFin1:
            etree.SubElement(comprar_viagem, 'itemFin1', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = itemFin1
        if itemFin2:
            etree.SubElement(comprar_viagem, 'itemFin2', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = itemFin2
        if itemFin3:
            etree.SubElement(comprar_viagem, 'itemFin3', attrib={etree.QName('xsi', 'type'): 'xsd:string'}).text = itemFin3

        soap_request = etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')

        try:
            response = requests.post(url, data=soap_request, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            st.error(f"Erro na requisição SOAP para rota {rota}: {e}")
            return None

        st.write("Resposta completa do servidor para rota:", rota)
        st.write(response.content.decode('utf-8'))

        try:
            root = etree.fromstring(response.content)
            root = remove_namespaces(root)  # Remove namespaces para facilitar a busca
            numero = None
            status = None
            for element in root.iter():
                if element.tag.endswith('numero'):
                    numero = element.text
                if element.tag.endswith('status'):
                    status = element.text

            if status == '0':
                st.write(f"Compra realizada com sucesso para rota {rota}. Número da viagem: {numero}")
                return numero
            else:
                st.error(f"Erro na compra da viagem para rota {rota}: Código de status {status}")
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

    # Interface Streamlit
    st.title("Formulário de Vale Pedágio")

    placa = st.text_input("Placa:")
    fazenda = st.text_input("Fazenda:")
    conjunto = st.selectbox("Conjunto:", ["Bitrem", "Tritrem", "Cargo Polo (5 eixos ida)", "Cargo Polo (6 eixos ida)"])

    if st.button("Processar Viagem"):
        if placa and fazenda and conjunto:
            processar_viagem(placa, fazenda, conjunto)
        else:
            st.warning("Por favor, preencha todos os campos!")


