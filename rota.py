import os
import streamlit as st
import requests
from lxml import etree
from datetime import datetime, timedelta

# Função para autenticar o usuário e retornar a sessão
def autenticar_usuario():
    print("Autenticando usuário...")
    
    # Obtém as credenciais a partir de variáveis de ambiente
    codigo_acesso = os.getenv("CODIGO_ACESSO")
    login = os.getenv("LOGIN")
    senha = os.getenv("SENHA")
    
    # Verifica se as variáveis de ambiente estão definidas
    if not codigo_acesso or not login or not senha:
        st.error("Credenciais não encontradas! Defina as variáveis de ambiente corretamente.")
        return None
    
    # URL do serviço SOAP de homologação para autenticação
    url = 'https://app.viafacil.com.br/wsvp/ValePedagio'
    
    # Cabeçalhos SOAP
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'autenticarUsuario'
    }
    
    # Criação do envelope SOAP
    envelope = etree.Element('{http://schemas.xmlsoap.org/soap/envelope/}Envelope',
                             nsmap={
                                 'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                                 'xsd': 'http://www.w3.org/2001/XMLSchema',
                                 'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
                                 'cgmp': 'http://cgmp.com'
                             })
    
    # Criação do corpo da requisição
    body = etree.SubElement(envelope, '{http://schemas.xmlsoap.org/soap/envelope/}Body')
    autenticar_usuario = etree.SubElement(body, '{http://cgmp.com}autenticarUsuario',
                                          attrib={'{http://schemas.xmlsoap.org/soap/envelope/}encodingStyle': 'http://schemas.xmlsoap.org/soap/encoding/'})
    
    # Adicionando os elementos de autenticação
    etree.SubElement(autenticar_usuario, 'codigodeacesso').text = codigo_acesso
    etree.SubElement(autenticar_usuario, 'login').text = login
    etree.SubElement(autenticar_usuario, 'senha').text = senha
    
    # Converte o envelope SOAP para string
    soap_request = etree.tostring(envelope, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    
    # Faz a requisição SOAP
    try:
        response = requests.post(url, data=soap_request, headers=headers)
        response.raise_for_status()  # Verifica erros de requisição HTTP
        
        # Processa a resposta
        response_content = etree.fromstring(response.content)
        ns = {
            'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns1': 'http://cgmp.com',
            'ns2': 'http://ws.dto.model.cgmp.com'
        }
        
        autenticar_usuario_response = response_content.find('.//ns1:autenticarUsuarioResponse', namespaces=ns)
        if autenticar_usuario_response is not None:
            autenticar_usuario_return = autenticar_usuario_response.find('.//autenticarUsuarioReturn')
            if autenticar_usuario_return is not None:
                sessao = autenticar_usuario_return.find('.//sessao').text
                status = autenticar_usuario_return.find('.//status').text
                
                if status == '0':
                    print(f"Autenticação bem-sucedida. Sessão: {sessao}")
                    return sessao  # Retorna a sessão para uso futuro
                else:
                    st.error(f"Erro na autenticação. Status: {status}")
                    return None
            else:
                st.error("Elemento 'autenticarUsuarioReturn' não encontrado.")
                return None
        else:
            st.error("Elemento 'autenticarUsuarioResponse' não encontrado.")
            return None
        
    except requests.exceptions.RequestException as e:
        st.error(f"Erro na requisição SOAP: {e}")
        return None
