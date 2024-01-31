import os
import glob
import re


palavras_excluidas = ["static final", "extends LocalEntity", "private Integer versao"]

def read_java_files(url):
    classesExcluidas = ["filtervo", "vo", "importacao", "legado", "enum", "Client", "sed", "SED"]
    public_class_files = []
    public_abstract_class_files = []

    for source, _, files in os.walk(url):
        for file in glob.glob(os.path.join(source, '*.java')):
            file_name = os.path.basename(file)
            if any(palavra in file_name for palavra in classesExcluidas):
                continue
            file_name = camel_case_para_snake_case(file_name, 'false')
            file_name = 'sge_' + file_name
            

            with open(file, 'r') as f:
                conteudo = f.read()

            if 'public class ' in conteudo:
                public_class_files.append((file, file_name))
            elif 'public abstract class ' in conteudo:
                public_abstract_class_files.append((file, file_name))

    # Processa primeiro os arquivos com 'public abstract class'
    for file, file_name in public_abstract_class_files:
        processar_arquivo_java(file, file_name)
                

    # Depois processa os arquivos com 'public class'
    for file, file_name in public_class_files:
        processar_arquivo_java(file, file_name)

   
            
            

def processar_arquivo_java(file_path, file_name):
    with open(file_path, 'r') as file:
        conteudo = file.read()
        if 'conselho_classe_matricula_deficiencia' in file_name:
            print(file_name)
        # Verifica se o arquivo contém 'public class'
        if 'class ' in conteudo:
            info_classe = extrair_anotacoes(conteudo)
            gerar_lookml(info_classe, file_name)
            
        else:
            print(f"Arquivo {file_name} ignorado, não contém 'public class'.")



def extrair_anotacoes(conteudo):
    propriedades = {}
    nome_tabela = None
    linhas = conteudo.splitlines()
    classe_base = None
    nome_coluna = None
    extende_papel = "extends Papel" in conteudo
    
    for i, linha in enumerate(linhas):
        if linha.strip().startswith('public ') and 'extends' in linha:
            classe_base = linha.split('extends')[-1].split()[0].strip()
            
            continue

        if any(palavra_excluida in linha for palavra_excluida in palavras_excluidas):
            continue

        if linha.strip().startswith('@Table('):
            nome_tabela = linha.split('"')[1]
            
        
        if 'private' in linha or 'protected' in linha:
            partes = linha.split()
            if len(partes) < 3:
                continue
            tipo_campo = partes[1]
            nome_campo = partes[2].replace(';', '')

            j = i - 1
            anotacoes = []
            nome_coluna_especificado = None
            while j >= 0 and ('@' in linhas[j]):
                anotacao = linhas[j].strip()
                if anotacao.startswith('@Column(name ='):
                    nome_coluna_especificado = anotacao.split('"')[1]
                    
                if anotacao.startswith('@'):
                    anotacoes.append(anotacao)
                    
                j -= 1
            
            
            nome_coluna = nome_coluna_especificado if nome_coluna_especificado is not None else nome_campo
            nome_campo = camel_case_para_snake_case(nome_campo, 'false')
            propriedades[nome_campo] = {'tipo': tipo_campo, 'anotacoes': anotacoes, 'nome_coluna': nome_coluna}
            

    return {'nome_tabela': nome_tabela, 'propriedades': propriedades, 'extende_papel': extende_papel, 'classe_base': classe_base}

def camel_case_para_snake_case(nome, tem_id):
    if not nome is None:
        if '.java' in nome:
            nome = nome.replace('.java', '')
        
        nome = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', nome)
        nome = re.sub('([a-z0-9])([A-Z])', r'\1_\2', nome).lower()
    if tem_id == 'true' :
        nome += '_id'

    return nome

def gerar_lookml(info_classe, file_name):

    nome_tabela = info_classe['nome_tabela']
    classe_base = info_classe['classe_base']
    extende_papel = info_classe['extende_papel']
    lookml = f"view: {file_name} {{\n"
    
    if not nome_tabela is  None:


        if nome_tabela:
            lookml += f"  sql_table_name: {{_user_attributes['database_user']}}.{nome_tabela} ;;\n\n"

        if classe_base and not 'SonnerBaseEntity' in classe_base:
                if lookml_classe_base_gerado(classe_base):
                    lookml += f"  extends: [{camel_case_para_snake_case(classe_base, 'false')}]\n\n"
                else: 
                    print("Classe base nao foi encontrada view criada para ela - " + classe_base )
                    
        

        if extende_papel:
            lookml += "     dimension: id {\n"
            lookml += "         type: number\n"
            lookml += "         sql: ${{TABLE}}.id ;;\n"
            lookml += "         primary_key: yes\n"
            lookml += "     }\n\n"

        for nome_campo, info in info_classe['propriedades'].items():
            tipo_lookml, is_primary_key = mapear_tipo_lookml(info['anotacoes'], info['tipo'])
            

            if tipo_lookml == 'date':
                lookml += f"     dimension_group: {nome_campo} {{\n"
                lookml += f"        timeframes: [time, date, week, month, year]\n"
            else:
                lookml += f"     dimension: {nome_campo} {{\n"

            lookml += f"        sql: ${{TABLE}}.{info['nome_coluna']} ;;\n"
            lookml += f"        type: {tipo_lookml}\n"
            if is_primary_key:
                lookml += "         primary_key: yes\n"
            lookml += "     }\n"
            lookml += "\n"
        lookml += "     }\n"

        salvar_lookml_em_arquivo(lookml, file_name, pasta_looks)
        return lookml
    else: return print("Classe nao gerada - " + file_name)

def lookml_classe_base_gerado(classe_base):
    # Verifica se o arquivo LookML para a classe base existe
    caminho_arquivo = os.path.join(pasta_looks, f"{camel_case_para_snake_case(classe_base, 'false')}.view.lkml")
    return os.path.exists(caminho_arquivo)

def salvar_lookml_em_arquivo(lookml, nome_arquivo, pasta_destino):
    # Certifique-se de que a pasta de destino existe
    os.makedirs(pasta_destino, exist_ok=True)

    caminho_completo = os.path.join(pasta_destino, f"{nome_arquivo}.view.lkml")

    with open(caminho_completo, 'w') as arquivo:
        arquivo.write(lookml)
    print(f"Arquivo LookML salvo em: {caminho_completo}")


def mapear_tipo_lookml(anotacoes, tipo_campo):
    is_primary_key = '@Id' in anotacoes or '@GeneratedValue' in anotacoes

    if tipo_campo == 'ForeignKey':
        return 'number', is_primary_key

    # Mapeamento baseado no tipo do campo
    tipo_lookml = {
        'String': 'string',
        'Integer': 'number',
        'Long': 'number',
        'BigDecimal': 'number',
        'Date': 'date',  # ou 'time', dependendo da necessidade
        'Boolean': 'yesno',
        # Adicione outros mapeamentos conforme necessário
    }.get(tipo_campo, 'string')  # Tipo padrão

    return tipo_lookml, is_primary_key

pasta_leitura = '/home/bernard/development/projects/grp-web/grp-web/sonner-model/src/main/java/br/com/sonner/escola/model/'
pasta_looks = '/home/bernard/development/pip/generated'
# Substitua 'caminho_para_pasta' pelo caminho do diretório que contém os arquivos Java
read_java_files(pasta_leitura)
