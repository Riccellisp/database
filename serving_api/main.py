from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from serving_api.database.connection import get_db
from data_pipeline.database.models import SilverTelemetry, GoldEquipmentFeatures, SimEquipment

app = FastAPI(
    title="Equipment Telemetry Serving API",
    description="Interface de serving de dados para expor tabelas Silver (telemetrias tratadas) e Gold (features de MLOps) de equipamentos.",
    version="1.0.0"
)

@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    """
    Checks database connectivity and service health.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service unhealthy. Database connection failed: {str(e)}"
        )

@app.get("/api/v1/equipments/{id}/telemetry")
def get_equipment_telemetry(id: str, limit: int = 48, db: Session = Depends(get_db)):
    """
    Retorna o historico de telemetrias limpas (camada Silver) para um determinado equipamento,
    ordenado do mais recente para o mais antigo.
    """
    records = db.query(SilverTelemetry).filter(
        SilverTelemetry.equipamento_id == id
    ).order_by(SilverTelemetry.timestamp.desc()).limit(limit).all()

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhuma telemetria encontrada para o equipamento com ID {id}."
        )

    result = []
    for r in records:
        row_dict = {}
        for col in r.__table__.columns:
            val = getattr(r, col.name)
            if val is not None:
                if col.name == "timestamp":
                    row_dict[col.name] = val.isoformat()
                else:
                    row_dict[col.name] = val
        result.append(row_dict)

    return result

@app.get("/api/v1/equipments/{id}/features")
def get_latest_ml_features(id: str, db: Session = Depends(get_db)):
    """
    Retorna o vetor de features agregadas mais recente (camada Gold) para servir a predicao de MLOps online.
    """
    latest_record = db.query(GoldEquipmentFeatures).filter(
        GoldEquipmentFeatures.equipamento_id == id
    ).order_by(GoldEquipmentFeatures.timestamp.desc()).first()

    if not latest_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhuma feature de MLOps calculada encontrada para o equipamento com ID {id}."
        )

    return {
        "timestamp": latest_record.timestamp.isoformat(),
        "equipamento_id": latest_record.equipamento_id,
        "is_interpolated": latest_record.is_interpolated,
        "features": latest_record.features
    }

@app.get("/api/v1/telemetry")
def get_all_telemetry(limit: int = 100, db: Session = Depends(get_db)):
    """
    Retorna o histórico geral de telemetrias limpas (camada Silver) de todos os equipamentos.
    """
    records = db.query(SilverTelemetry).order_by(SilverTelemetry.timestamp.desc()).limit(limit).all()
    result = []
    for r in records:
        row_dict = {}
        for col in r.__table__.columns:
            val = getattr(r, col.name)
            if val is not None:
                if col.name == "timestamp":
                    row_dict[col.name] = val.isoformat()
                else:
                    row_dict[col.name] = val
        result.append(row_dict)

    return result

@app.get("/api/v1/features")
def get_all_latest_features(db: Session = Depends(get_db)):
    """
    Retorna o vetor de features agregadas mais recente de todas as máquinas.
    """
    equipments = db.query(SimEquipment.equipamento_id).all()
    eq_ids = [e[0] for e in equipments]
    result = []

    for eq_id in eq_ids:
        latest_record = db.query(GoldEquipmentFeatures).filter(
            GoldEquipmentFeatures.equipamento_id == eq_id
        ).order_by(GoldEquipmentFeatures.timestamp.desc()).first()
        
        if latest_record:
            result.append({
                "timestamp": latest_record.timestamp.isoformat(),
                "equipamento_id": latest_record.equipamento_id,
                "is_interpolated": latest_record.is_interpolated,
                "features": latest_record.features
            })
            
    return result

@app.get("/api/v1/equipments/{equipment_id}")
def get_equipment_data(equipment_id: str, limit: int = 48, db: Session = Depends(get_db)):
    """
    Retorna o histórico de telemetrias limpas (camada Silver) e as features
    agregadas mais recentes (camada Gold) de um equipamento específico.
    """
    records = db.query(SilverTelemetry).filter(
        SilverTelemetry.equipamento_id == equipment_id
    ).order_by(SilverTelemetry.timestamp.desc()).limit(limit).all()

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum registro encontrado para o equipamento {equipment_id}."
        )

    telemetry_list = []
    for r in records:
        row_dict = {}
        for col in r.__table__.columns:
            val = getattr(r, col.name)
            if val is not None:
                if col.name == "timestamp":
                    row_dict[col.name] = val.isoformat()
                else:
                    row_dict[col.name] = val
        telemetry_list.append(row_dict)

    latest_features = db.query(GoldEquipmentFeatures).filter(
        GoldEquipmentFeatures.equipamento_id == equipment_id
    ).order_by(GoldEquipmentFeatures.timestamp.desc()).first()

    features_dict = None
    if latest_features:
        features_dict = {
            "timestamp": latest_features.timestamp.isoformat(),
            "equipamento_id": latest_features.equipamento_id,
            "is_interpolated": latest_features.is_interpolated,
            "features": latest_features.features
        }

    return {
        "equipamento_id": equipment_id,
        "telemetry": telemetry_list,
        "features": features_dict
    }

from pydantic import BaseModel, Field
from typing import Optional

class EquipmentCreate(BaseModel):
    equipamento_id: str = Field(..., description="ID ou número de série do equipamento (pode ser IPv6)")
    tipo: str = Field(..., description="Tipo do equipamento (ex: tc, raio x, ressonancia magnetica, etc.)")
    modelo: str = Field(..., description="Modelo do equipamento")
    fabricante: str = Field(..., description="Fabricante do equipamento")
    desgaste_acumulado: Optional[float] = Field(0.0, description="Desgaste acumulado inicial")
    data_instalacao: Optional[str] = Field(None, description="Data de instalação (YYYY-MM-DD)")
    data_ultima_manutencao: Optional[str] = Field(None, description="Data da última manutenção (YYYY-MM-DD)")
    ip_address: Optional[str] = Field(None, description="Endereço IP (IPv4 ou IPv6)")
    porta_conexao: Optional[int] = Field(None, description="Porta de conexão de rede")
    endereco_mac: Optional[str] = Field(None, description="Endereço MAC físico")
    protocolo: Optional[str] = Field(None, description="Protocolo de comunicação (ex: DICOM, HL7, HTTP)")

@app.post("/api/v1/equipments", status_code=status.HTTP_201_CREATED)
def register_equipment(eq: EquipmentCreate, db: Session = Depends(get_db)):
    """
    Cadastra um novo equipamento no banco de dados de simulação centralizado (MySQL).
    Permite que o simulador comece a gerar telemetrias para o novo ativo dinamicamente.
    """
    from datetime import datetime
    from monitoring_service.simulators.base import inicializar_estado_temporal

    # Normalizar valores
    tipo_norm = eq.tipo.lower().strip()
    data_manut = eq.data_ultima_manutencao or datetime.today().strftime("%Y-%m-%d")
    desgaste = eq.desgaste_acumulado if eq.desgaste_acumulado is not None else 0.0

    # 1. Verificar duplicidade no banco
    exists = db.query(SimEquipment).filter(SimEquipment.equipamento_id == eq.equipamento_id).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Equipamento com ID '{eq.equipamento_id}' já está cadastrado no simulador."
        )

    # 2. Inicializar estado físico temporal
    try:
        estado_fisico = inicializar_estado_temporal(tipo_norm, desgaste)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de equipamento '{eq.tipo}' não é suportado pelo simulador."
        )

    if "scan_count" in estado_fisico:
        carga_acumulada = estado_fisico["scan_count"]
    elif "exposure_count" in estado_fisico:
        carga_acumulada = estado_fisico["exposure_count"]
    else:
        carga_acumulada = 0.0

    estado_op = "DEGRADANDO" if desgaste >= 0.55 else "NORMAL"

    try:
        new_eq = SimEquipment(
            equipamento_id=eq.equipamento_id,
            tipo=tipo_norm,
            modelo=eq.modelo,
            fabricante=eq.fabricante,
            idade_dias=0,
            desgaste=desgaste,
            carga_acumulada=carga_acumulada,
            ultima_manutencao=data_manut,
            estado_operacional_interno=estado_op,
            modo_falha_ativo=None,
            intensidade_falha=0.0,
            horas_falha_restantes=0,
            ultimo_estado_temporal=estado_fisico,
            ip_address=eq.ip_address,
            porta_conexao=eq.porta_conexao,
            endereco_mac=eq.endereco_mac,
            protocolo=eq.protocolo
        )
        db.add(new_eq)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar no banco de dados: {str(e)}"
        )

    return {
        "status": "created",
        "detail": "Equipamento cadastrado com sucesso no banco de dados.",
        "equipment": eq
    }
