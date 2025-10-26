
# Desafio Final: Santander Code Girls 2025 - Pipeline de Dados Serverless com AWS e LocalStack

Este projeto é o desafio final do bootcamp **Santander Code Girls 2025**. O objetivo é construir um pipeline de dados "serverless" (sem servidor) ponta-a-ponta, capaz de processar arquivos em lote (batch) de forma automática e assíncrona.

O pipeline simula um cenário real de ingestão de dados, onde um arquivo JSON contendo múltiplas notas fiscais é enviado para um bucket S3. Esse evento de upload dispara automaticamente uma função Lambda, que lê o arquivo, processa cada nota fiscal individualmente e as persiste em uma tabela de banco de dados NoSQL (DynamoDB).

## 🚀 O Papel do LocalStack

Para construir e testar esta arquitetura de nuvem de forma ágil, segura e sem custos, utilizamos o **LocalStack**.

O LocalStack é um simulador de nuvem completo que nos permite executar os serviços da AWS (como S3, Lambda, DynamoDB, SQS, etc.) inteiramente dentro de um container Docker em nossa máquina local. Isso nos permite desenvolver, testar e depurar aplicações "cloud-native" antes de enviá-las para o ambiente real da AWS.

## 🏛️ Arquitetura do Projeto

O fluxo de dados deste projeto é 100% orientado a eventos (event-driven).

> **Upload no S3 ➔ Trigger aciona a Lambda ➔ Lambda lê o arquivo ➔ Lambda salva no DynamoDB**

1.  **S3 (Simple Storage Service):** Um bucket chamado `notas-fiscais-upload` é configurado para armazenar os arquivos JSON de entrada.
2.  **S3 Event Notification (Trigger):** O bucket S3 é configurado para disparar um evento `s3:ObjectCreated:*` sempre que um novo arquivo é salvo.
3.  **Lambda (Função `ProcessarNotasFiscais`):** Esta função Python é o "cérebro" da operação. Ela é acionada pelo evento do S3, recebe a notificação, usa essa informação para baixar o arquivo JSON do S3, lê seu conteúdo (um array de notas) e faz um loop, inserindo cada nota no DynamoDB.
4.  **DynamoDB (Banco NoSQL):** Uma tabela chamada `NotasFiscais` armazena os registros individuais, com `id` como chave primária.

## 🛠️ Tecnologias Utilizadas

  * **AWS CLI:** Ferramenta de linha de comando para criar e gerenciar todos os recursos.
  * **LocalStack:** Para simular o ambiente AWS localmente.
  * **Docker Desktop:** Para executar o container do LocalStack.
  * **Python 3.9:** Linguagem de programação da nossa função Lambda.
  * **Boto3:** O SDK (biblioteca) oficial da AWS para Python, usado dentro da Lambda para se comunicar com o S3 e o DynamoDB.
  * **Serviços AWS Simulados:**
      * **S3:** Para armazenamento de objetos.
      * **Lambda:** Para computação serverless.
      * **DynamoDB:** Para persistência de dados.
      * **CloudWatch Logs:** Para depuração da Lambda (via `aws logs tail`).
      * **IAM:** Simulado para fornecer as permissões necessárias (ex: `lambda:InvokeFunction`).

-----

## ⚙️ Como Executar o Projeto

Siga estes passos para configurar e executar todo o pipeline do zero.

### Pré-requisitos

  * **Docker Desktop** instalado e em execução.
  * **AWS CLI (v2)** instalado e configurado (mesmo com credenciais "dummy", ex: `aws configure`).
  * **Python 3.9+** (com `pip`).
  * **LocalStack** instalado via pip: `pip install localstack`

### 1\. Iniciar o LocalStack

Em um terminal, inicie o LocalStack (isso irá baixar a imagem Docker na primeira vez).

```powershell
localstack start
```

### 2\. Criar os Recursos da AWS

Abra um **novo** terminal. Daqui em diante, todos os comandos `aws` usarão a flag `--endpoint-url=http://localhost:4566` para apontar para o nosso LocalStack.

**a) Criar o Bucket S3:**

```powershell
aws --endpoint-url=http://localhost:4566 s3api create-bucket --bucket notas-fiscais-upload
```

**b) Criar a Tabela DynamoDB:**

```powershell
aws --endpoint-url=http://localhost:4566 dynamodb create-table `
 --table-name NotasFiscais `
 --attribute-definitions AttributeName=id,AttributeType=S `
 --key-schema AttributeName=id,KeyType=HASH `
 --billing-mode PAY_PER_REQUEST
```

### 3\. Preparar e Criar a Função Lambda

**a) Salve o Código Python:**
Crie um arquivo chamado `grava_db.py` com o código abaixo. Este código é responsável por ler o evento do S3, baixar o arquivo e salvar no DynamoDB.

**b) Crie o Pacote `.zip`:**
O Lambda exige que o código seja enviado como um arquivo `.zip`.

```powershell
# No Windows (usando o botão direito):
# 1. Clique com o botão direito em `grava_db.py`
# 2. Enviar para > Pasta compactada (zipada)
# 3. Renomeie o arquivo para `lambda_function.zip`
```

**c) Crie a Função Lambda:**
Execute este comando de dentro da pasta onde está o seu `lambda_function.zip`.

```powershell
aws lambda create-function `
 --function-name ProcessarNotasFiscais `
 --runtime python3.9 `
 --role arn:aws:iam::000000000000:role/lambda-role `
 --handler grava_db.lambda_handler `
 --zip-file fileb://lambda_function.zip `
 --endpoint-url=http://localhost:4566
```

### 4\. Configurar o Trigger (S3 ➔ Lambda)

Esta é a "cola" que une os serviços.

**a) Dar Permissão à Lambda:**
Autoriza o S3 a invocar a nossa função.

```powershell
aws lambda add-permission `
 --function-name ProcessarNotasFiscais `
 --statement-id s3-trigger `
 --action "lambda:InvokeFunction" `
 --principal s3.amazonaws.com `
 --source-arn arn:aws:s3:::notas-fiscais-upload `
 --endpoint-url=http://localhost:4566
```

**b) Criar o Arquivo de Configuração do Trigger:**
Crie um arquivo chamado `notification.json` com o conteúdo abaixo. Ele diz ao S3 para acionar nossa Lambda em eventos de "criação de objeto".


**c) Configurar o Bucket S3:**
Aplique a configuração de notificação ao bucket.


## 🔥 Testando o Pipeline

Agora, vamos ver a mágica acontecer\! Você precisará de 2 ou 3 terminais abertos.

**Terminal 1 (Opcional, mas recomendado): Ver os Logs da Lambda**
Este comando fica "aberto", escutando os logs da sua função em tempo real.

```powershell
aws --endpoint-url=http://localhost:4566 logs tail /aws/lambda/ProcessarNotasFiscais --follow
```

**Terminal 2: Fazer o Upload do Arquivo**
Pegue seu arquivo de notas fiscais (ex: `notas_fiscais_2025.json`) e faça o upload dele para o S3.

```powershell
aws --endpoint-url=http://localhost:4566 s3 cp "notas_fiscais_2025.json" s3://notas-fiscais-upload/
```

**Resultado:**
Se você estiver com o terminal de logs aberto, verá as mensagens aparecendo:

<img width="1353" height="678" alt="image" src="https://github.com/user-attachments/assets/da76c732-48bc-43ef-a44b-db0466d35be3" />


**Terminal 3 (Verificação Final): Consultar o DynamoDB**
Para provar que os dados estão no banco, execute um "scan" na tabela:

```powershell
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name NotasFiscais
```

A saída será um JSON contendo todos os 15 itens salvos pela Lambda.
