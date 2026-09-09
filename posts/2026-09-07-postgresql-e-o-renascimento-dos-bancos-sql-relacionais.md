---
title: "PostgreSQL e o renascimento dos bancos SQL relacionais"
date: "2026-09-07"
category: "curiosidade"
tags: ["postgresql", "database", "tendencias"]
excerpt: "Introdução A era dos bancos de dados NoSQL, que prometiam flexibilidade e escalabilidade, parecia ter conquistado o coração dos desenvolvedores. No entanto, nos últimos anos"
lang: "pt"
---

## Introdução
A era dos bancos de dados NoSQL, que prometiam flexibilidade e escalabilidade, parecia ter conquistado o coração dos desenvolvedores. No entanto, nos últimos anos, temos assistido a um renascimento dos bancos de dados SQL relacionais, liderado por soluções como o PostgreSQL. Mas o que levou a esse retorno? aqui, vou mostrar as razões por trás desse movimento e como o PostgreSQL se destacou como uma das principais opções para armazenamento de dados.


<figure>
  <img src="https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/media/2026-09-07-postgresql-e-o-renascimento-dos-bancos-sql-relacionais.jpg" alt="O elefante, mascote do PostgreSQL, banco relacional que voltou ao centro." loading="lazy" />
  <figcaption>
    O elefante, mascote do PostgreSQL, banco relacional que voltou ao centro. — Imagem: <a href="https://commons.wikimedia.org/wiki/File%3APostgresql_elephant.svg">Postgresql elephant.svg</a> por Daniel Lundin —
    <a href="https://opensource.org/license/bsd-3-clause">BSD</a> · via Wikimedia Commons
  </figcaption>
</figure>

## A era NoSQL (2010-2018)
No início dos anos 2010, os bancos de dados NoSQL começaram a ganhar popularidade. Eles prometiam ser mais flexíveis e escaláveis do que os bancos de dados tradicionais, e muitos desenvolvedores os adotaram para lidar com grandes volumes de dados. No entanto, com o tempo, começaram a surgir problemas. A falta de padronização e a complexidade dos bancos de dados NoSQL tornaram difícil garantir a consistência e a integridade dos dados. Além disso, a falta de suporte a transações e a dificuldade em realizar consultas complexas tornaram os bancos de dados NoSQL menos atraentes para muitos desenvolvedores.

## O virar de chave
Em meados dos anos 2010, os desenvolvedores começaram a perceber que os bancos de dados SQL relacionais não eram tão limitados quanto pareciam. Com o advento de tecnologias como o PostgreSQL, que oferecia recursos como suporte a JSON e extensões, os bancos de dados SQL relacionais começaram a ganhar novamente a atenção dos desenvolvedores. Além disso, a necessidade de garantir a consistência e a integridade dos dados, bem como a capacidade de realizar consultas complexas, tornou os bancos de dados SQL relacionais mais atraentes.

## JSON nativo no PostgreSQL
Um dos recursos que mais contribuiu para o renascimento do PostgreSQL foi o suporte a JSON nativo. Com a versão 9.4, o PostgreSQL introduziu o tipo de dados JSON, que permitia armazenar e consultar dados JSON de forma eficiente. Isso tornou o PostgreSQL uma opção atraente para aplicativos que requeriam armazenamento de dados flexíveis e escaláveis. Por exemplo, em um dos meus projetos em Python, utilizei o PostgreSQL para armazenar dados de configuração em JSON, o que me permitiu ter uma grande flexibilidade na forma como os dados eram armazenados e consultados.

## Extensions (pgvector, PostGIS, pg_cron)
Outro recurso que tornou o PostgreSQL mais atraente foi a capacidade de adicionar extensões. Com a versão 9.1, o PostgreSQL introduziu a capacidade de adicionar extensões, que permitiam adicionar novos recursos e funcionalidades ao banco de dados. Algumas das extensões mais populares incluem o pgvector, que permite armazenar e consultar dados vetoriais, o PostGIS, que permite armazenar e consultar dados geoespaciais, e o pg_cron, que permite agendar tarefas para serem executadas automaticamente. Essas extensões tornaram o PostgreSQL uma opção mais versátil e flexível para os desenvolvedores.

## Supabase e PlanetScale
Além disso, a ascensão de soluções como o Supabase e o PlanetScale também contribuiu para o renascimento do PostgreSQL. O Supabase é uma plataforma que oferece uma camada de abstração sobre o PostgreSQL, tornando mais fácil para os desenvolvedores criar aplicativos escaláveis e seguros. Já o PlanetScale é uma plataforma que oferece uma solução de banco de dados escalável e segura, baseada no PostgreSQL. Essas soluções tornaram o PostgreSQL mais acessível e atraente para os desenvolvedores.

## SQL ganhou de volta
Com o renascimento do PostgreSQL, o SQL também ganhou novamente a atenção dos desenvolvedores. A capacidade de realizar consultas complexas e garantir a consistência e a integridade dos dados tornou o SQL uma opção mais atraente para muitos desenvolvedores. Além disso, a capacidade de utilizar o SQL para realizar consultas em dados JSON e vetoriais também tornou o SQL mais versátil e flexível.

## Conclusão
resumindo, o renascimento do PostgreSQL se deve à combinação de recursos como o suporte a JSON nativo, extensões e soluções como o Supabase e o PlanetScale. Além disso, a necessidade de garantir a consistência e a integridade dos dados, bem como a capacidade de realizar consultas complexas, tornou os bancos de dados SQL relacionais mais atraentes para os desenvolvedores. Aqui estão alguns takeaways práticos:

* O PostgreSQL é uma opção atraente para armazenamento de dados devido ao seu suporte a JSON nativo e extensões.
* As extensões como o pgvector, PostGIS e pg_cron tornam o PostgreSQL mais versátil e flexível.
* Soluções como o Supabase e o PlanetScale tornam o PostgreSQL mais acessível e atraente para os desenvolvedores.
* O SQL é uma opção mais atraente para muitos desenvolvedores devido à sua capacidade de realizar consultas complexas e garantir a consistência e a integridade dos dados.

## Fontes
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Supabase Documentation](https://supabase.io/docs)
- [PlanetScale Documentation](https://planetscale.com/docs)
- [pgvector GitHub Repository](https://github.com/pgvector/pgvector)
- [PostGIS GitHub Repository](https://github.com/postgis/postgis)
- [pg_cron GitHub Repository](https://github.com/citusdata/pg_cron)
## 📸 Crédito da imagem de capa
- **Imagem:** [Postgres Query.jpg](https://commons.wikimedia.org/wiki/File%3APostgres_Query.jpg)
- **Autor(a):** Chiffre01
- **Licença:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) · via Wikimedia Commons
