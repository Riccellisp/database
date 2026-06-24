import json
import time
import sys
from kafka import KafkaConsumer
from data_pipeline.config import Config
from data_pipeline.processors.bronze_to_silver import process_bronze_to_silver
from data_pipeline.processors.silver_to_gold import process_silver_to_gold
from data_pipeline.storage.s3_client import init_buckets

def start_pipeline():
    try:
        init_buckets()
    except Exception as e:
        print(f"Aviso: Não foi possível conectar ao MinIO/S3 durante a inicialização: {e}")

    try:
        from data_pipeline.database.connection import init_sql_db
        init_sql_db()
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados SQL: {e}")

    consumer = None
    retries = 15
    while retries > 0:
        try:
            consumer = KafkaConsumer(
                Config.TELEMETRY_TOPIC,
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='medallion-pipeline-group'
            )
            print("Conectado ao Kafka com sucesso!")
            break
        except Exception as e:
            print(f"Aguardando Kafka inicializar ({retries} tentativas restantes)... Erro: {e}")
            time.sleep(5)
            retries -= 1

    if not consumer:
        print("Não foi possível conectar ao broker Kafka.")
        sys.exit(1)

    print(f"Escutando mensagens de telemetria no tópico '{Config.TELEMETRY_TOPIC}'...")
    try:
        for message in consumer:
            try:
                telemetry_msg = message.value
                
                hospital_id = telemetry_msg.get("hospital_id")
                equipamento_id = telemetry_msg.get("equipamento_id")
                tipo_eq = telemetry_msg.get("tipo")
                
                if not hospital_id or not equipamento_id or not tipo_eq:
                    print("Mensagem de telemetria inválida ou incompleta. Ignorando...")
                    continue
                
                # Step 1: Bronze to Silver
                df_eq = process_bronze_to_silver(
                    hospital_id=hospital_id,
                    equipamento_id=equipamento_id,
                    tipo_eq=tipo_eq,
                    new_telemetry_msg=telemetry_msg
                )
                
                # Step 2: Silver to Gold
                process_silver_to_gold(
                    hospital_id=hospital_id,
                    equipamento_id=equipamento_id,
                    tipo_eq=tipo_eq,
                    df_eq=df_eq
                )
                
            except Exception as e:
                print(f"Erro ao processar mensagem no pipeline: {e}")
    except KeyboardInterrupt:
        print("\nPipeline finalizado pelo usuário.")
    finally:
        consumer.close()

if __name__ == "__main__":
    start_pipeline()
