import os
import json
import sqlite3
import random
from datetime import datetime
from pathlib import Path
from monitoring_service.config import Config
from monitoring_service.simulators.base import inicializar_estado_temporal

DB_PATH = Config.SIMULATION_DB_PATH

def init_db():
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create the simulation table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sim_equipamentos (
            equipamento_id INTEGER PRIMARY KEY,
            hospital_id INTEGER NOT NULL DEFAULT 1,
            tipo TEXT NOT NULL,
            modelo TEXT NOT NULL,
            fabricante TEXT NOT NULL,
            idade_dias INTEGER NOT NULL,
            desgaste REAL NOT NULL,
            carga_acumulada REAL NOT NULL,
            ultima_manutencao TEXT,
            estado_operacional_interno TEXT NOT NULL,
            modo_falha_ativo TEXT,
            intensidade_falha REAL NOT NULL,
            horas_falha_restantes INTEGER NOT NULL,
            ultimo_estado_temporal TEXT NOT NULL
        )
    """)
    conn.commit()
    
    # Check if table already contains data
    cur.execute("SELECT COUNT(*) FROM sim_equipamentos")
    count = cur.fetchone()[0]
    if count == 0:
        print("Banco de simulação local vazio. Inicializando a partir do arquivo CSV...")
        initialize_equipments_from_csv(conn)
        
    conn.close()
 
def initialize_equipments_from_csv(sim_conn):
    import csv
    
    csv_path = Config.CSV_PATH
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Arquivo CSV de equipamentos não encontrado em: {csv_path}")
        
    sim_cur = sim_conn.cursor()
    hoje = datetime.now()
    equipamentos_carregados = 0
    
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            h_id = int(row["hospital_id"])
            if h_id in Config.HOSPITAL_IDS:
                eq_id = int(row["equipamento_id"])
                tipo = row["tipo_equipamento"]
                modelo = row["modelo"]
                fabricante = row["fabricante"]
                desgaste = float(row["desgaste_acumulado"])
                data_instalacao_str = row["data_instalacao"]
                data_ultima_manut_str = row["data_ultima_manutencao"]
                
                # Parse age in days
                try:
                    data_inst = datetime.strptime(data_instalacao_str, "%Y-%m-%d")
                    idade_dias = (hoje - data_inst).days
                except Exception:
                    idade_dias = random.randint(100, 1000)
                    
                # Initialize temporal physics parameters
                estado_fisico = inicializar_estado_temporal(tipo, desgaste)
                
                # Set workload counter
                if "scan_count" in estado_fisico:
                    carga_acumulada = estado_fisico["scan_count"]
                elif "exposure_count" in estado_fisico:
                    carga_acumulada = estado_fisico["exposure_count"]
                else:
                    carga_acumulada = random.randint(100, 10000)
                    
                # Store starting operational state internally based on wear
                estado_op = "DEGRADANDO" if desgaste >= 0.55 else "NORMAL"
                
                sim_cur.execute("""
                    INSERT INTO sim_equipamentos (
                        equipamento_id, hospital_id, tipo, modelo, fabricante, idade_dias, desgaste, carga_acumulada,
                        ultima_manutencao, estado_operacional_interno, modo_falha_ativo,
                        intensidade_falha, horas_falha_restantes, ultimo_estado_temporal
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0.0, 0, ?)
                """, (
                    eq_id, h_id, tipo, modelo, fabricante, idade_dias, desgaste, carga_acumulada,
                    data_ultima_manut_str, estado_op, json.dumps(estado_fisico)
                ))
                equipamentos_carregados += 1
                
    sim_conn.commit()
    print(f"Banco de dados de simulação local inicializado com {equipamentos_carregados} equipamentos de {len(Config.HOSPITAL_IDS)} hospitais a partir do arquivo CSV.")

def get_all_equipments():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM sim_equipamentos")
    rows = cur.fetchall()
    
    equipments = []
    for r in rows:
        eq = dict(r)
        eq["ultimo_estado_temporal"] = json.loads(eq["ultimo_estado_temporal"])
        equipments.append(eq)
        
    conn.close()
    return equipments

def update_equipment(eq):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE sim_equipamentos
        SET idade_dias = ?,
            desgaste = ?,
            carga_acumulada = ?,
            ultima_manutencao = ?,
            estado_operacional_interno = ?,
            modo_falha_ativo = ?,
            intensidade_falha = ?,
            horas_falha_restantes = ?,
            ultimo_estado_temporal = ?
        WHERE equipamento_id = ?
    """, (
        eq["idade_dias"],
        eq["desgaste"],
        eq["carga_acumulada"],
        eq["ultima_manutencao"],
        eq["estado_operacional_interno"],
        eq["modo_falha_ativo"],
        eq["intensidade_falha"],
        eq["horas_falha_restantes"],
        json.dumps(eq["ultimo_estado_temporal"]),
        eq["equipamento_id"]
    ))
    conn.commit()
    conn.close()
