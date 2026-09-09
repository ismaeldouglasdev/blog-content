---
title: "PostgreSQL and the Resurgence of Relational SQL Databases"
date: "2026-09-07"
category: "curiosidade"
tags: ["postgresql", "database", "tendencias"]
excerpt: "NoSQL databases, promising flexibility and scalability, won developers hearts, but recently"
lang: "en"
translation_of: "2026-09-07-postgresql-e-o-renascimento-dos-bancos-sql-relacionais"
---

## Introdução
The era of NoSQL databases, which promised flexibility and scalability, seemed to have won the hearts of developers. However, in recent years, we have witnessed a resurgence of relational SQL databases, led by solutions like PostgreSQL. But what drove this return? Here, I will show the reasons behind this movement and how PostgreSQL has stood out as one of the top options for data storage.


<figure>
  <img src="https://raw.githubusercontent.com/ismaeldouglasdev/blog-content/main/posts/media/2026-09-07-postgresql-e-o-renascimento-dos-bancos-sql-relacionais.jpg" alt="The elephant, PostgreSQL's mascot, the relational database that came back." loading="lazy" />
  <figcaption>
    The elephant, PostgreSQL's mascot, the relational database that came back. — Imagem: <a href="https://commons.wikimedia.org/wiki/File%3APostgresql_elephant.svg">Postgresql elephant.svg</a> por Daniel Lundin —
    <a href="https://opensource.org/license/bsd-3-clause">BSD</a> · via Wikimedia Commons
  </figcaption>
</figure>

## The NoSQL Era (2010-2018)
In the early 2010s, NoSQL databases began to gain popularity. They promised to be more flexible and scalable than traditional databases, and many developers adopted them to handle large volumes of data. However, over time, problems began to emerge. The lack of standardization and the complexity of NoSQL databases made it difficult to ensure data consistency and integrity. Additionally, the lack of support for transactions and the difficulty in performing complex queries made NoSQL databases less appealing to many developers.

## The Turning Point
In the mid-2010s, developers began to realize that relational SQL databases were not as limited as they seemed. With the advent of technologies like PostgreSQL, which offered features such as JSON support and extensions, relational SQL databases started to regain the attention of developers. Additionally, the need to ensure data consistency and integrity, as well as the ability to perform complex queries, made relational SQL databases more attractive.

---
## Native JSON in PostgreSQL
One of the features that most contributed to the resurgence of PostgreSQL was its native support for JSON. With version 9.4, PostgreSQL introduced the JSON data type, which allowed for efficient storage and querying of JSON data. This made PostgreSQL an attractive option for applications that required flexible and scalable data storage. For example, in one of my Python projects, I used PostgreSQL to store configuration data in JSON, which gave me a great deal of flexibility in how the data was stored and queried.

---
## Extensions (pgvector, PostGIS, pg_cron)
Another feature that made PostgreSQL more attractive was its ability to add extensions. With version 9.1, PostgreSQL introduced the ability to add extensions, which allowed for adding new features and functionalities to the database. Some of the most popular extensions include pgvector, which allows for storing and querying vector data, PostGIS, which allows for storing and querying geospatial data, and pg_cron, which allows for scheduling tasks to be executed automatically. These extensions made PostgreSQL a more versatile and flexible option for developers.

## Supabase and PlanetScale
Additionally, the rise of solutions like Supabase and PlanetScale has also contributed to the resurgence of PostgreSQL. Supabase is a platform that provides an abstraction layer over PostgreSQL, making it easier for developers to create scalable and secure applications. Meanwhile, PlanetScale is a platform that offers a scalable and secure database solution based on PostgreSQL. These solutions have made PostgreSQL more accessible and appealing to developers.

## SQL gained momentum again
With the resurgence of PostgreSQL, SQL also regained the attention of developers. The ability to perform complex queries and ensure data consistency and integrity made SQL a more attractive option for many developers. Additionally, the ability to use SQL to query JSON and vector data also made SQL more versatile and flexible.

## Conclusão
In summary, the resurgence of PostgreSQL is due to the combination of features such as native JSON support, extensions, and solutions like Supabase and PlanetScale. Additionally, the need to ensure data consistency and integrity, as well as the ability to perform complex queries, has made relational SQL databases more appealing to developers. Here are some practical takeaways:

* PostgreSQL is an attractive option for data storage due to its native JSON support and extensions.
* Extensions like pgvector, PostGIS, and pg_cron make PostgreSQL more versatile and flexible.
* Solutions like Supabase and PlanetScale make PostgreSQL more accessible and appealing to developers.
* SQL is a more attractive option for many developers due to its ability to perform complex queries and ensure data consistency and integrity.

---

## Sources
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Supabase Documentation](https://supabase.io/docs)
- [PlanetScale Documentation](https://planetscale.com/docs)
- [pgvector GitHub Repository](https://github.com/pgvector/pgvector)
- [PostGIS GitHub Repository](https://github.com/postgis/postgis)
- [pg_cron GitHub Repository](https://github.com/citusdata/pg_cron)
## 📸 Cover image credit
- **Image:** [Postgresql elephant.svg](https://commons.wikimedia.org/wiki/File%3APostgresql_elephant.svg)
- **Author:** Daniel Lundin
- **License:** [BSD](https://en.wikipedia.org/wiki/BSD_licenses) · via Wikimedia Commons

## 📸 Crédito da imagem de capa
- **Imagem:** [Postgres Query.jpg](https://commons.wikimedia.org/wiki/File%3APostgres_Query.jpg)
- **Autor(a):** Chiffre01
- **Licença:** [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) · via Wikimedia Commons
