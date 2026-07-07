import os
import json
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from monitoring_service.config import Config

# Initialize connection URL based on Config
if Config.USE_MYSQL:
    DATABASE_URL = f"mysql+pymysql://{Config.DB_USER}:{Config.DB_PASSWORD}@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}"
    engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
else:
    # SQLite local file fallback for offline testing/development
    db_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(db_dir, "..", "persistence"), exist_ok=True)
    sqlite_path = os.path.join(db_dir, "..", "persistence", "simulation.db")
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    from data_pipeline.database.models import Base, SimEquipment
    
    # Create the simulation tables in the target database
    Base.metadata.create_all(bind=engine)
    
    # Check if table already contains data
    session = SessionLocal()
    try:
        # 1. Load/merge from CSV if CSV_PATH is set and exists
        csv_path = getattr(Config, "CSV_PATH", None)
        if csv_path and os.path.exists(csv_path):
            print(f"Importando/sincronizando equipamentos a partir do CSV: {csv_path}")
            try:
                import_equipments_from_csv(session, csv_path)
            except Exception as e:
                print(f"Erro ao importar equipamentos do CSV: {e}")
                
        # 2. Fallback: if table is still empty, generate dynamically
        count = session.query(SimEquipment).count()
        if count == 0:
            print("Banco de simulação vazio. Inicializando equipamentos gerados dinamicamente...")
            generate_default_equipments_in_db(session)
    finally:
        session.close()

def import_equipments_from_csv(session, csv_path):
    import csv
    from data_pipeline.database.models import SimEquipment
    from monitoring_service.simulators.base import inicializar_estado_temporal
    
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        equipamentos_importados = 0
        for row in reader:
            eq_id = str(row["equipamento_id"])
            
            # Check if equipment already exists in DB
            exists = session.query(SimEquipment).filter(SimEquipment.equipamento_id == eq_id).first()
            if exists:
                continue # Skip existing to preserve simulation state
                
            tipo = row["tipo_equipamento"].lower().strip()
            modelo = row["modelo"]
            fabricante = row["fabricante"]
            desgaste = float(row["desgaste_acumulado"])
            data_manut = row["data_ultima_manutencao"]
            
            # Initialize temporal physics parameters
            estado_fisico = inicializar_estado_temporal(tipo, desgaste)
            
            if "scan_count" in estado_fisico:
                carga_acumulada = estado_fisico["scan_count"]
            elif "exposure_count" in estado_fisico:
                carga_acumulada = estado_fisico["exposure_count"]
            else:
                carga_acumulada = random.randint(100, 10000)
                
            estado_op = "DEGRADANDO" if desgaste >= 0.55 else "NORMAL"
            
            # Generate network credentials for simulation (defaults for CSV import)
            protocols_map = {
                "tc": ("DICOM", 11112),
                "raio x": ("DICOM", 11112),
                "ressonancia magnetica": ("DICOM", 11112),
                "pet": ("DICOM", 11112),
                "ultrassom": ("DICOM", 11112),
                "arco cirurgico": ("DICOM", 11112)
            }
            protocolo, porta = protocols_map.get(tipo, ("HTTP", 80))
            ip_address = f"192.168.1.{100 + random.randint(1, 150)}"
            mac_address = f"00:25:90:01:{random.randint(1, 254):02X}:FF"
            
            # Get IP and port from CSV if they exist (just in case they are added in CSV)
            if "ip_address" in row and row["ip_address"]:
                ip_address = row["ip_address"]
            if "porta_conexao" in row and row["porta_conexao"]:
                porta = int(row["porta_conexao"])
            if "endereco_mac" in row and row["endereco_mac"]:
                mac_address = row["endereco_mac"]
            if "protocolo" in row and row["protocolo"]:
                protocolo = row["protocolo"]

            eq = SimEquipment(
                equipamento_id=eq_id,
                tipo=tipo,
                modelo=modelo,
                fabricante=fabricante,
                idade_dias=0,
                desgaste=desgaste,
                carga_acumulada=carga_acumulada,
                ultima_manutencao=data_manut,
                estado_operacional_interno=estado_op,
                modo_falha_ativo=None,
                intensidade_falha=0.0,
                horas_falha_restantes=0,
                ultimo_estado_temporal=estado_fisico,
                ip_address=ip_address,
                porta_conexao=porta,
                endereco_mac=mac_address,
                protocolo=protocolo
            )
            session.add(eq)
            equipamentos_importados += 1
            
        session.commit()
        if equipamentos_importados > 0:
            print(f"Importados/sincronizados {equipamentos_importados} novos equipamentos a partir do CSV.")

def generate_default_equipments_in_db(session):
    from data_pipeline.database.models import SimEquipment
    from monitoring_service.simulators.base import inicializar_estado_temporal
    
    eq_specs = [
        ("tc", "SOMATOM go.Top", "Siemens Healthineers"),
        ("tc", "Aquilion One", "Canon Medical Systems"),
        ("raio x", "DigitalDiagnost C90", "Philips"),
        ("raio x", "Brivo XR115", "GE HealthCare"),
        ("ressonancia magnetica", "Magnetom Altea", "Siemens Healthineers"),
        ("ressonancia magnetica", "Signa Pioneer", "GE HealthCare"),
        ("ultrassom", "EPIQ Elite", "Philips"),
        ("ultrassom", "LOGIQ E10", "GE HealthCare"),
        ("pet", "Biograph Vision", "Siemens Healthineers"),
        ("arco cirurgico", "Azurion 7", "Philips")
    ]
    
    hoje = datetime.now()
    equipamentos_gerados = 0
    
    for idx, (tipo, modelo, fabricante) in enumerate(eq_specs):
        # Unique equipment ID using a standard serial number format
        eq_id = f"SN-{tipo.upper().replace(' ', '')}-{idx+1:02d}"
        
        # Random wear and age
        desgaste = random.uniform(0.05, 0.95)
        idade_dias = random.randint(30, 1800)
        data_manut = (hoje - timedelta(days=random.randint(10, 180))).strftime("%Y-%m-%d")
        
        # Initialize temporal physics parameters
        estado_fisico = inicializar_estado_temporal(tipo, desgaste)
        
        if "scan_count" in estado_fisico:
            carga_acumulada = estado_fisico["scan_count"]
        elif "exposure_count" in estado_fisico:
            carga_acumulada = estado_fisico["exposure_count"]
        else:
            carga_acumulada = random.randint(100, 10000)
            
        # Generate network credentials for simulation
        protocols_map = {
            "tc": ("DICOM", 11112),
            "raio x": ("DICOM", 11112),
            "ressonancia magnetica": ("DICOM", 11112),
            "pet": ("DICOM", 11112),
            "ultrassom": ("DICOM", 11112),
            "arco cirurgico": ("DICOM", 11112)
        }
        protocolo, porta = protocols_map.get(tipo, ("HTTP", 80))
        ip_address = f"192.168.1.{10 + idx}"
        mac_address = f"00:25:90:01:{idx+1:02X}:FF"
        
        estado_op = "DEGRADANDO" if desgaste >= 0.55 else "NORMAL"
        
        eq = SimEquipment(
            equipamento_id=eq_id,
            tipo=tipo,
            modelo=modelo,
            fabricante=fabricante,
            idade_dias=idade_dias,
            desgaste=desgaste,
            carga_acumulada=carga_acumulada,
            ultima_manutencao=data_manut,
            estado_operacional_interno=estado_op,
            modo_falha_ativo=None,
            intensidade_falha=0.0,
            horas_falha_restantes=0,
            ultimo_estado_temporal=estado_fisico,
            ip_address=ip_address,
            porta_conexao=porta,
            endereco_mac=mac_address,
            protocolo=protocolo
        )
        session.add(eq)
        equipamentos_gerados += 1
        
    session.commit()
    print(f"Banco de dados de simulação inicializado com {equipamentos_gerados} equipamentos dinâmicos.")

def get_all_equipments():
    session = SessionLocal()
    from data_pipeline.database.models import SimEquipment
    
    try:
        if Config.EQUIPAMENTO_ID is not None:
            query = session.query(SimEquipment).filter(SimEquipment.equipamento_id == Config.EQUIPAMENTO_ID)
        else:
            query = session.query(SimEquipment)
            
        rows = query.all()
        equipments = []
        for r in rows:
            # Convert to dictionary for backward compatibility with main.py
            eq_dict = {
                "equipamento_id": r.equipamento_id,
                "tipo": r.tipo,
                "modelo": r.modelo,
                "fabricante": r.fabricante,
                "idade_dias": r.idade_dias,
                "desgaste": r.desgaste,
                "carga_acumulada": r.carga_acumulada,
                "ultima_manutencao": r.ultima_manutencao,
                "estado_operacional_interno": r.estado_operacional_interno,
                "modo_falha_ativo": r.modo_falha_ativo,
                "intensidade_falha": r.intensidade_falha,
                "horas_falha_restantes": r.horas_falha_restantes,
                "ultimo_estado_temporal": r.ultimo_estado_temporal,
                "ip_address": r.ip_address,
                "porta_conexao": r.porta_conexao,
                "endereco_mac": r.endereco_mac,
                "protocolo": r.protocolo
            }
            equipments.append(eq_dict)
        return equipments
    finally:
        session.close()

def update_equipment(eq):
    session = SessionLocal()
    from data_pipeline.database.models import SimEquipment
    
    try:
        db_eq = session.query(SimEquipment).filter(SimEquipment.equipamento_id == eq["equipamento_id"]).first()
        if db_eq:
            db_eq.idade_dias = eq["idade_dias"]
            db_eq.desgaste = eq["desgaste"]
            db_eq.carga_acumulada = eq["carga_acumulada"]
            db_eq.ultima_manutencao = eq["ultima_manutencao"]
            db_eq.estado_operacional_interno = eq["estado_operacional_interno"]
            db_eq.modo_falha_ativo = eq["modo_falha_ativo"]
            db_eq.intensidade_falha = eq["intensidade_falha"]
            db_eq.horas_falha_restantes = eq["horas_falha_restantes"]
            db_eq.ultimo_estado_temporal = eq["ultimo_estado_temporal"]
            session.commit()
    finally:
        session.close()
