---
title: "Serverless no AWS Lambda: funcoes, APIs e automacoes baratas"
date: "2026-08-27"
category: "tutorial"
tags: ["serverless", "aws", "lambda", "cloud"]
excerpt: "Introdução: Serverless e Quando Vale a Pena Quando se fala em desenvolvimento de software, uma das principais preocupações é a infraestrutura necessária para rodar as"
lang: "pt"
---

## Introdução: Serverless e Quando Vale a Pena
Quando se fala em desenvolvimento de software, uma das principais preocupações é a infraestrutura necessária para rodar as aplicações. Servidores, manutenção, escalabilidade - tudo isso pode ser um desafio, especialmente para projetos menores ou startups. É aqui que entra o conceito de serverless, uma abordagem que permite aos desenvolvedores criar e implantar aplicações sem se preocupar com a infraestrutura subjacente. aqui, vou mostrar como o AWS Lambda, um dos principais serviços serverless da Amazon Web Services (AWS), pode ser utilizado para criar funções, APIs e automações de forma eficiente e barata.

## Lambda Básico com Python/Node
Para começar a usar o AWS Lambda, é importante entender como criar uma função simples. O Lambda suporta várias linguagens de programação, incluindo Python e Node.js, que são duas das mais populares. Com o Python, por exemplo, você pode criar uma função que responde a um evento simples, como uma requisição HTTP. Já com o Node.js, a criação de funções assíncronas é ainda mais direta, graças à sua natureza não bloqueante.

Um exemplo simples em Python poderia ser uma função que retorna um "Olá, Mundo!" quando chamada:
```python
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Olá, Mundo!'
    }
```
Já em Node.js, uma função equivalente poderia ser:
```javascript
exports.handler = async (event) => {
    const response = {
        statusCode: 200,
        body: 'Olá, Mundo!',
    };
    return response;
};
```
Essas funções básicas demonstram como o Lambda pode ser usado para criar endpoints simples ou realizar tarefas específicas sem a necessidade de provisionar servidores.

## API Gateway para REST
Um dos usos mais comuns do AWS Lambda é em conjunto com o API Gateway, para criar APIs RESTful. O API Gateway atua como um frontend para as funções Lambda, permitindo que elas sejam chamadas através de requisições HTTP. Isso facilita a criação de APIs sem a complexidade de gerenciar servidores ou balanceadores de carga.

Por exemplo, você pode criar um recurso no API Gateway que mapeia uma requisição GET para uma função Lambda. Quando uma requisição é feita para esse recurso, o API Gateway chama a função Lambda correspondente, passando os parâmetros necessários, e então retorna a resposta da função para o cliente.

## Event Triggers (S3, SQS, DynamoDB)
Além de ser chamado através do API Gateway, o Lambda pode ser disparado por uma variedade de eventos provenientes de outros serviços da AWS, como o Amazon S3, Amazon SQS, e Amazon DynamoDB. Isso permite que as funções Lambda sejam usadas para processar dados assim que eles são criados ou atualizados, sem a necessidade de polling ou outros mecanismos de verificações periódicas.

Por exemplo, você pode configurar o Lambda para ser disparado sempre que um novo arquivo é uploadado para um bucket do S3. A função então pode processar o arquivo, realizando tarefas como compressão, conversão de formato, ou até mesmo análise de conteúdo.

## Cold Start e Mitigações
Um dos desafios ao trabalhar com o Lambda é o chamado "cold start", que ocorre quando uma função é chamada após um período de inatividade. Nesse caso, o Lambda precisa criar uma nova instância da função, o que pode levar alguns milissegundos. Embora o cold start seja um problema conhecido, existem estratégias para mitigá-lo, como manter as funções "quentes" através de chamadas periódicas ou usar provisionamento de conjuntos de instâncias do Lambda.

## Custos Reais vs EC2
Um dos principais benefícios do uso do Lambda é o modelo de cobrança baseado no uso. Você paga apenas pelo tempo de execução das suas funções, o que pode ser significativamente mais barato do que manter instâncias EC2 sempre ligadas. Além disso, não há necessidade de provisionar ou gerenciar servidores, o que reduz a carga de trabalho para os times de operações.

## SAM e CDK
Para facilitar o desenvolvimento e a implantação de aplicações serverless, a AWS oferece o AWS Serverless Application Model (SAM) e o AWS Cloud Development Kit (CDK). O SAM é um framework open-source que permite que você defina aplicações serverless em um modelo simples e consistente, enquanto o CDK é um kit de desenvolvimento que permite definir infraestrutura em código, usando linguagens como TypeScript, Python, ou Java.

## Conclusão
O AWS Lambda oferece uma forma poderosa e flexível de criar aplicações serverless, permitindo que os desenvolvedores se concentrem em escrever código sem se preocupar com a infraestrutura subjacente. Com o Lambda, você pode criar funções, APIs, e automações de forma eficiente e barata, escalando automaticamente para atender às necessidades da sua aplicação.

Takeaways práticos:
* Use o Lambda para criar funções serverless que respondam a eventos específicos.
* Integre o Lambda com o API Gateway para criar APIs RESTful.
* Aproveite os eventos provenientes de outros serviços da AWS para disparar funções Lambda.
* Mitigue o cold start com provisionamento de conjuntos de instâncias ou chamadas periódicas.
* Compare os custos do Lambda com os da EC2 para encontrar a melhor opção para o seu caso de uso.
* Utilize o SAM e o CDK para simplificar o desenvolvimento e a implantação de aplicações serverless.

## Fontes
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [AWS API Gateway Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html)
- [AWS Serverless Application Model (SAM)](https://aws.amazon.com/serverless/sam/)
- [AWS Cloud Development Kit (CDK)](https://aws.amazon.com/cdk/)
- [Documentação oficial do Python](https://docs.python.org/3/)
- [Documentação oficial do Node.js](https://nodejs.org/en/docs/)