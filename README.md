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

* **FastAPI Serving API**: `http://localhost:18000`
  * Documentação interativa (Swagger UI): `http://localhost:18000/docs`
* **MinIO Console (S3/Data Lake)**: `http://localhost:9001` (Usuário: `admin` | Senha: `strongpassword123`)
* **MySQL (Serving DB)**: `localhost:13306` (Usuário: `root` | Senha: `strongpassword123` | Banco: `serving_db`)
* **Apache Kafka Broker**: `localhost:29092`

---

## 🔧 Configuração e Customização da Simulação

Você pode parametrizar a velocidade da simulação diretamente editando o arquivo `monitoring_service/docker-compose.yml` sob a seção de `environment` do serviço `monitoring_service`:

*   **`SIMULATION_INTERVAL_SEC`**: Controla a frequência de geração da telemetria. Define quantos segundos reais duram 1 hora simulada.
    *   `3600.0` (Padrão): Modo de **Tempo Real** (1 hora simulada = 1 hora real). Cada equipamento publica uma leitura a cada hora real.
    *   `5.0` (ou menor): Modo **Acelerado** (1 hora simulada = 5 segundos reais). Ideal para testes rápidos locais, gerando dados em alta velocidade.
*   **`EQUIPAMENTO_ID`**: (Opcional) Permite rodar a simulação focada em um único ID de equipamento (ex: `SN-TC-01`). Se não estiver configurado, simula todos os equipamentos do banco de dados.

---

