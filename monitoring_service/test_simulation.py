import os
import time
import sqlite3
from datetime import datetime, timedelta

# Set configuration overrides for testing
os.environ["SIMULATION_INTERVAL_SEC"] = "0.1"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9999" # Forced offline fallback
os.environ["ANOMALY_CHANCE"] = "0.3" # Increase anomaly chance for test visibility
os.environ["CSV_PATH"] = ""

from monitoring_service.persistence import db
from monitoring_service.config import Config
from monitoring_service.simulators.base import ciclo_uso_hospitalar, detectar_falha
from monitoring_service.simulators.equipments import atualizar_estado_temporal
from monitoring_service.kafka.producer import KafkaProducerWrapper
from monitoring_service.utils import logger

def test_offline_run():
    print("=== [TEST] Iniciando Teste de Validação Offline ===")
    
    # Reset local test simulation DB if exists to guarantee a fresh initial state
    db_dir = os.path.dirname(os.path.abspath(db.__file__))
    db_path = os.path.join(db_dir, "..", "persistence", "simulation.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"Limpando base de teste anterior: {db_path}")
        except PermissionError:
            pass
            
    # Initialize DB (will load from historical)
    db.init_db()
    
    # Load equipments
    eqs = db.get_all_equipments()
    print(f"Carregados {len(eqs)} equipamentos para simulação.")
    assert len(eqs) == 10, f"Deveria ter carregado exatamente 10 equipamentos, encontrou {len(eqs)}"
    
    # Check if we can read columns properly
    first_eq = eqs[0]
    test_eq_id = first_eq['equipamento_id']
    initial_wear = first_eq['desgaste']
    print(f"Equipamento de teste inicial: ID={test_eq_id}, Tipo={first_eq['tipo']}, Desgaste={initial_wear}")
    assert initial_wear > 0.0, "Desgaste inicial deve ser maior que 0"
    
    # Run exactly 5 simulated hours
    sim_time = datetime.now()
    producer = KafkaProducerWrapper(Config.KAFKA_BOOTSTRAP_SERVERS)
    
    print("\nExecutando 5 horas simuladas de teste...")
    for hour in range(1, 6):
        sim_time += timedelta(hours=1)
        sim_time_str = sim_time.isoformat()
        print(f"\n--- Hora Simulada #{hour} ({sim_time_str}) ---")
        
        for eq in eqs:
            eq_id = eq["equipamento_id"]
            tipo_eq = eq["tipo"]
            desgaste = eq["desgaste"]
            estado_op = eq["estado_operacional_interno"]
            modo_falha = eq["modo_falha_ativo"]
            intensidade_falha = eq["intensidade_falha"]
            estado_fisico = eq["ultimo_estado_temporal"]
            
            # Simple simulation step
            uso = ciclo_uso_hospitalar(sim_time, tipo_eq)
            
            # Mock entering pre-failure on hour 2 for equipment 1 to test degradation
            if hour == 2 and eq_id == test_eq_id:
                estado_op = "PRE_FALHA"
                modo_falha = "superaquecimento do tubo"
                intensidade_falha = 0.5
                print(f"[TEST MOCK] Forçando anomalia no Equipamento {eq_id} ({tipo_eq})")
                
            estado_fisico, desgaste_novo = atualizar_estado_temporal(
                tipo_eq=tipo_eq,
                estado=estado_fisico,
                desgaste=desgaste,
                uso=uso,
                operational_state=estado_op,
                modo_falha=modo_falha,
                intensidade_falha=intensidade_falha
            )
            
            # Check limits
            falha_fisica = detectar_falha(tipo_eq, estado_fisico)
            if falha_fisica:
                print(f"[TEST DETECT] Limite crítico ultrapassado no equipamento {eq_id}: {falha_fisica}")
                
            # Log style assertion
            logger.info(eq_id, "publicando_telemetria")
                
            # Update local list for next iteration
            eq["desgaste"] = desgaste_novo
            eq["ultimo_estado_temporal"] = estado_fisico
            eq["estado_operacional_interno"] = estado_op
            eq["modo_falha_ativo"] = modo_falha
            eq["intensidade_falha"] = intensidade_falha
            
            # Update DB
            db.update_equipment(eq)
            
        time.sleep(float(Config.SIMULATION_INTERVAL_SEC))
        
    # Verify database updates
    updated_eqs = db.get_all_equipments()
    eq1_updated = next(e for e in updated_eqs if e["equipamento_id"] == test_eq_id)
    
    print("\n=== Verificação pós-simulação ===")
    print(f"Equipamento 1 Desgaste Inicial: {initial_wear} -> Atual: {eq1_updated['desgaste']}")
    print(f"Equipamento 1 Estado Operacional: {eq1_updated['estado_operacional_interno']}")
    print(f"Equipamento 1 Último Estado Físico: {eq1_updated['ultimo_estado_temporal']}")
    
    assert eq1_updated["desgaste"] != initial_wear, "O desgaste deveria ter evoluído."
    print("\n[TEST] Todos os testes passaram com sucesso!")

if __name__ == "__main__":
    test_offline_run()
