# Pipeline de Telemetria Hospitalar

Este repositório contém a infraestrutura e o pipeline de dados de telemetria hospitalar estruturado em contêineres Docker.

## 🚀 Como Executar o Sistema

Para rodar todo o ecossistema (Kafka, MinIO/S3, PostgreSQL Serving DB, Data Pipeline Consumer, Simulador de Telemetria e FastAPI Serving API):

1. **Certifique-se de que o Docker e o Docker Compose estão instalados e rodando em sua máquina.**
2. **Navegue até a pasta do serviço de monitoramento:**
   ```bash
   cd monitoring_service
   ```
3. **Suba os serviços utilizando o Docker Compose:**
   ```bash
   docker-compose up -d --build
   ```

## 📡 Portas e Serviços Expostos

* **FastAPI Serving API**: `http://localhost:8000`
  * Documentação interativa (Swagger UI): `http://localhost:8000/docs`
* **MinIO Console (S3/Data Lake)**: `http://localhost:9001` (Usuário: `admin` | Senha: `strongpassword123`)
* **PostgreSQL (Serving DB)**: `localhost:5432` (Usuário: `postgres` | Senha: `strongpassword123` | Banco: `serving_db`)
* **Apache Kafka Broker**: `localhost:29092`

---
