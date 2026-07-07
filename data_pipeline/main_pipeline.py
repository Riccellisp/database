import json
import time
import sys
from kafka import KafkaConsumer
from data_pipeline.config import Config
from data_pipeline.processors.bronze_to_silver import process_bronze_to_silver
from data_pipeline.processors.silver_to_gold import process_silver_to_gold
from data_pipeline.storage.s3_client import init_buckets

# In-memory cache to resolve hospital_id for equipments without hitting DB every message
EQUIPMENT_HOSPITAL_CACHE = {}

def get_hospital_id_for_equipment(equipamento_id):
    if not equipamento_id:
        return None
    if equipamento_id in EQUIPMENT_HOSPITAL_CACHE:
        return EQUIPMENT_HOSPITAL_CACHE[equipamento_id]
        
    from data_pipeline.database.connection import get_db_session
    from data_pipeline.database.models import SimEquipment
    
    session = get_db_session()
    try:
        db_eq = session.query(SimEquipment).filter(SimEquipment.equipamento_id == equipamento_id).first()
        if db_eq:
            h_id = db_eq.hospital_id
            EQUIPMENT_HOSPITAL_CACHE[equipamento_id] = h_id
            return h_id
    except Exception as e:
        print(f"Erro ao buscar hospital_id no banco para o equipamento {equipamento_id}: {e}")
    finally:
        session.close()
    return None

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
                
                equipamento_id = telemetry_msg.get("equipamento_id")
                tipo_eq = telemetry_msg.get("tipo")
                
                # Resolve hospital_id (from cache/DB)
                hospital_id = telemetry_msg.get("hospital_id")
                if not hospital_id and equipamento_id:
                    hospital_id = get_hospital_id_for_equipment(equipamento_id)
                
                if not hospital_id or not equipamento_id or not tipo_eq:
                    print(f"Mensagem de telemetria inválida, incompleta ou hospital não resolvido. Ignorando... eq_id={equipamento_id}, hospital={hospital_id}")
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
