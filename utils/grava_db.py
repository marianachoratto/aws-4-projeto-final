# Nome do arquivo: grava_db.py

import json
import boto3
import os
import logging
from decimal import Decimal
import urllib.parse # Para lidar com nomes de arquivos com espaços ou caracteres especiais

# Configurar o logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configurar o endpoint dinamicamente (para LocalStack)
dynamodb_endpoint = os.getenv('DYNAMODB_ENDPOINT', None) 
s3_endpoint = dynamodb_endpoint # No LocalStack, o endpoint é o mesmo para tudo

# Conectar ao DynamoDB
dynamodb = boto3.resource('dynamodb', endpoint_url=dynamodb_endpoint)
table = dynamodb.Table('NotasFiscais')

# Conectar ao S3 (NOVO!)
# Precisamos do S3 client para baixar o arquivo que foi enviado
s3_client = boto3.client('s3', endpoint_url=s3_endpoint)


# Função para salvar UMA nota fiscal no DynamoDB
# (Simplifiquei a antiga 'inserir_registros')
def salvar_nota(nota_fiscal):
    try:
        # Validação básica
        required_keys = ["id", "cliente", "valor", "data_emissao"]
        if not all(key in nota_fiscal for key in required_keys):
            logger.error(f"Validação falhou. Chaves ausentes na nota: {nota_fiscal.get('id')}")
            return False # Retorna falha

        # O DynamoDB não aceita 'float' do Python, temos que usar 'Decimal'
        item = nota_fiscal.copy()
        item['valor'] = Decimal(str(item['valor']))
        
        # Inserir o item no DynamoDB
        table.put_item(Item=item)
        
        logger.info(f"Registro {item['id']} inserido com sucesso.")
        return True # Retorna sucesso

    except Exception as e:
        logger.error(f"Erro ao inserir registro {nota_fiscal.get('id')}: {e}")
        return False # Retorna falha


# Função principal (Handler) - TOTALMENTE REESCRITA
def lambda_handler(event, context):
    logger.info(f"Evento recebido: {json.dumps(event)}")

    # 1. O evento do S3 vem dentro da chave 'Records'
    for record in event['Records']:
        try:
            # 2. Pegar o nome do bucket e o nome do arquivo (object key)
            bucket_name = record['s3']['bucket']['name']
            
            # O nome do arquivo pode ter caracteres especiais (como '+') 
            # e precisa ser decodificado
            object_key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            
            logger.info(f"Processando arquivo {object_key} do bucket {bucket_name}...")

            # 3. Baixar o arquivo do S3 para a pasta /tmp da Lambda (armazenamento temporário)
            download_path = f'/tmp/{object_key.split("/")[-1]}' # Pega só o nome do arquivo
            s3_client.download_file(bucket_name, object_key, download_path)
            
            logger.info(f"Arquivo baixado para {download_path}")

            # 4. Ler o arquivo JSON que acabamos de baixar
            with open(download_path, 'r', encoding='utf-8') as f:
                # json.load(f) lê o arquivo e já converte o JSON
                # Assumindo que o arquivo é um ARRAY de notas
                array_de_notas = json.load(f) 
            
            logger.info(f"Arquivo JSON lido. Encontradas {len(array_de_notas)} notas.")
            
            sucesso_count = 0
            
            # 5. Fazer um loop no array e salvar cada nota no DynamoDB
            for nota in array_de_notas:
                if salvar_nota(nota):
                    sucesso_count += 1
            
            logger.info(f"Processamento concluído: {sucesso_count} de {len(array_de_notas)} notas salvas.")

        except Exception as e:
            logger.error(f"Erro ao processar o registro do S3: {e}")
            # Continua para o próximo 'record' se houver
    
    return {
        'statusCode': 200,
        'body': json.dumps('Processamento do S3 concluído.')
    }