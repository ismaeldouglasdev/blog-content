---
title: "Kubernetes pra iniciantes: conceitos essenciais sem complicação"
date: "2026-09-27"
category: "tutorial"
tags: ["kubernetes", "devops", "containers"]
excerpt: "Kubernetes pra iniciantes: conceitos essenciais sem complicação."
cover: "https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/covers/2026-09-27-kubernetes-pra-iniciantes-conceitos-essenciais-sem.jpg"
lang: "pt"
---

A adoção do Kubernetes tem crescido exponencialmente nos últimos anos, e não é para menos. Ao lidar com aplicações que precisam ser escaláveis e gerenciáveis de forma eficiente, o Kubernetes se destaca como uma solução poderosa. No entanto, para quem está começando, o ambiente pode parecer complexo e intimidador. Este artigo visa desmistificar os conceitos básicos do Kubernetes, tornando-os acessíveis e compreensíveis.

## Pods e Deployments

No coração do Kubernetes, temos os **pods**, que são as menores unidades de implantação. Um pod pode conter um ou mais containers que compartilham o mesmo espaço de rede e armazenamento. Vamos considerar um exemplo simples de um pod que executa uma aplicação Node.js.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: meu-app
spec:
  containers:
    - name: meu-container
      image: node:22
      ports:
        - containerPort: 3000
```

No exemplo acima, criamos um pod chamado `meu-app` que roda um container com a imagem do Node.js. Agora, para gerenciar a criação e a atualização de pods, utilizamos os **deployments**. Um deployment garante que o número desejado de pods esteja sempre em execução.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meu-app-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: meu-app
  template:
    metadata:
      labels:
        app: meu-app
    spec:
      containers:
        - name: meu-container
          image: node:22
          ports:
            - containerPort: 3000
```

Aqui, definimos um deployment que cria três réplicas do nosso pod `meu-app`. Caso um dos pods falhe, o Kubernetes o reiniciará automaticamente, garantindo alta disponibilidade.

## Services

Com os pods em funcionamento, precisamos de uma maneira de acessá-los. É aí que entram os **services**. Um service é uma abstração que define uma forma de acessar um ou mais pods.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: meu-app-service
spec:
  type: NodePort
  selector:
    app: meu-app
  ports:
    - port: 3000
      targetPort: 3000
      nodePort: 30001
```

Neste exemplo, criamos um service chamado `meu-app-service`, que expõe nosso pod na porta 30001. Assim, podemos acessar nossa aplicação através do endereço `http://<endereço-do-nó>:30001`.

## Ingress

Para uma gestão mais avançada do tráfego, utilizamos o **ingress**. Um ingress permite o controle sobre o acesso aos serviços, geralmente através de um balanceador de carga. Ele é especialmente útil quando precisamos gerenciar múltiplos serviços sob um único domínio.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: meu-app-ingress
spec:
  rules:
    - host: meu-app.exemplo.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: meu-app-service
                port:
                  number: 3000
```

Com essa configuração, podemos acessar nosso serviço `meu-app-service` através do domínio `meu-app.exemplo.com`.

## ConfigMaps e Secrets

Em aplicações reais, frequentemente temos configurações que precisam ser mantidas separadas do código. Para isso, utilizamos **ConfigMaps** e **Secrets**. Um ConfigMap é usado para armazenar dados de configuração não sensíveis, enquanto um Secret é destinado a informações sensíveis, como senhas.

Exemplo de um ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: meu-app-config
data:
  DATABASE_URL: "mongodb://localhost:27017/meuapp"
```

E um exemplo de Secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: meu-app-secret
type: Opaque
data:
  PASSWORD: bXlwYXNzd29yZA==
```

No exemplo do Secret, o valor `bXlwYXNzd29yZA==` é a string "mypassword" codificada em base64.

## Scaling

Uma das grandes vantagens do Kubernetes é a capacidade de escalar aplicações. Podemos aumentar ou diminuir o número de réplicas de um pod com um simples comando. Para escalar nosso deployment, utilizamos:

```bash
kubectl scale deployment meu-app-deployment --replicas=5
```

Esse comando mudará o número de réplicas do deployment para cinco, permitindo que a aplicação suporte mais usuários ou cargas de trabalho.

## Minikube pra dev

Para quem está começando e quer experimentar o Kubernetes localmente, **Minikube** é uma excelente ferramenta. Ele permite que você crie um cluster Kubernetes em sua máquina local, facilitando o desenvolvimento e testes.

Para instalar o Minikube, você pode seguir os passos da documentação oficial. Após a instalação, basta iniciar o cluster com:

```bash
minikube start
```

Depois, você pode aplicar suas configurações YAML diretamente no seu cluster local.

## Conclusão

Aqui, exploramos os conceitos essenciais do Kubernetes de forma acessível. Ao entender como funcionam os pods, deployments, services, ingress, ConfigMaps, secrets e a capacidade de escalar aplicações, você estará mais preparado para enfrentar os desafios de gerenciar aplicações em containeres.

### Takeaways práticos:

- **Pods** são a menor unidade de execução no Kubernetes, podendo conter um ou mais containers.
- **Deployments** gerenciam a criação e manutenção de pods, garantindo alta disponibilidade.
- **Services** expõem pods para acesso externo, facilitando a comunicação.
- **Ingress** permite o gerenciamento avançado de tráfego e roteamento.
- **ConfigMaps** e **Secrets** ajudam a gerenciar configurações e informações sensíveis.
- O **Minikube** é uma ferramenta ideal para desenvolvedores que desejam experimentar Kubernetes localmente.

## Fontes

- [Documentação oficial do Kubernetes](https://kubernetes.io/docs/home/)
- [Kubernetes Basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/)
- [Minikube Docs](https://minikube.sigs.k8s.io/docs/start/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Ingress in Kubernetes](https://kubernetes.io/docs/concepts/services-networking/ingress/)