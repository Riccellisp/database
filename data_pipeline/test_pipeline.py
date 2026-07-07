import unittest
import io
import json
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Force offline config overrides for testing
import os
os.environ["S3_ENDPOINT_URL"] = "http://mock-endpoint"

from data_pipeline.config import Config
from data_pipeline.processors.bronze_to_silver import process_bronze_to_silver
from data_pipeline.processors.silver_to_gold import process_silver_to_gold

class MockS3Client:
    def __init__(self):
        self.storage = {}

    def put_object(self, Bucket, Key, Body):
        self.storage[(Bucket, Key)] = Body
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.storage:
            from botocore.exceptions import ClientError
            error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
            raise ClientError(error_response, 'GetObject')
        
        # S3 Body has a read() method
        body_bytes = self.storage[(Bucket, Key)]
        if isinstance(body_bytes, str):
            body_bytes = body_bytes.encode('utf-8')
            
        mock_body = MagicMock()
        mock_body.read.return_value = body_bytes
        return {"Body": mock_body}

    def head_bucket(self, Bucket):
        return {}

    def create_bucket(self, Bucket):
        return {}

class TestDataPipeline(unittest.TestCase):
    @patch("data_pipeline.processors.bronze_to_silver.get_s3_client")
    @patch("data_pipeline.processors.silver_to_gold.get_s3_client")
    def test_pipeline_interpolation_and_aggregates(self, mock_s3_gold, mock_s3_silver):
        print("\n=== [TEST] Iniciar Teste de Validação da Pipeline Medalhão ===")
        
        # 0. Clean and Initialize local SQL Serving DB
        from data_pipeline.database.connection import init_sql_db, get_db_session
        from data_pipeline.database.models import SilverTelemetry, GoldEquipmentFeatures, SimEquipment
        
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "serving_database.db"))
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f"Limpando banco de serving de teste anterior: {db_path}")
            except PermissionError:
                pass
        init_sql_db()
        
        hospital_id = 1
        equipamento_id = "1"
        tipo_eq = "tc"
        
        # Insert a mock SimEquipment so pipeline lookup resolves hospital_id correctly
        session = get_db_session()
        mock_eq = SimEquipment(
            equipamento_id=equipamento_id,
            hospital_id=hospital_id,
            tipo=tipo_eq,
            modelo="Test Model",
            fabricante="Test Manufacturer",
            desgaste=0.1,
            carga_acumulada=1000.0,
            ultimo_estado_temporal={}
        )
        session.add(mock_eq)
        session.commit()
        session.close()
        
        # Instantiate a single mock storage client shared by both patches
        mock_s3 = MockS3Client()
        mock_s3_silver.return_value = mock_s3
        mock_s3_gold.return_value = mock_s3
        
        base_time = datetime(2026, 6, 7, 12, 0, 0)
        
        # We will simulate 4 hours of telemetry:
        # Hour 0: Normal
        # Hour 1: Normal
        # Hour 2: MISSING (gap of 2 hours until hour 3)
        # Hour 3: Normal
        # Hour 4: Normal
        telemetries = [
            {
                "timestamp": (base_time + timedelta(hours=0)).isoformat(),
                "equipamento_id": equipamento_id,
                "tipo": tipo_eq,
                "telemetria": {
                    "scan_count": 1000,
                    "tube_temp": 40.0,
                    "tube_current": 330.0,
                    "anode_rotation_speed": 9800.0,
                    "detector_temp_drift": 0.1,
                    "slip_ring_error_rate": 0.002,
                    "gantry_vibration_fft": 0.28,
                    "gantry_rotation": 0.39
                }
            },
            {
                "timestamp": (base_time + timedelta(hours=1)).isoformat(),
                "equipamento_id": equipamento_id,
                "tipo": tipo_eq,
                "telemetria": {
                    "scan_count": 1005,
                    "tube_temp": 42.0,  # +2 degrees
                    "tube_current": 330.0,
                    "anode_rotation_speed": 9800.0,
                    "detector_temp_drift": 0.1,
                    "slip_ring_error_rate": 0.002,
                    "gantry_vibration_fft": 0.28,
                    "gantry_rotation": 0.39
                }
            },
            # HOUR 2 is missing here!
            {
                "timestamp": (base_time + timedelta(hours=3)).isoformat(),
                "equipamento_id": equipamento_id,
                "tipo": tipo_eq,
                "telemetria": {
                    "scan_count": 1015,
                    "tube_temp": 46.0,  # expected interpolation value at hour 2 is (42 + 46) / 2 = 44.0
                    "tube_current": 330.0,
                    "anode_rotation_speed": 9800.0,
                    "detector_temp_drift": 0.1,
                    "slip_ring_error_rate": 0.002,
                    "gantry_vibration_fft": 0.28,
                    "gantry_rotation": 0.39
                }
            },
            {
                "timestamp": (base_time + timedelta(hours=4)).isoformat(),
                "equipamento_id": equipamento_id,
                "tipo": tipo_eq,
                "telemetria": {
                    "scan_count": 1020,
                    "tube_temp": 48.0,
                    "tube_current": 330.0,
                    "anode_rotation_speed": 9800.0,
                    "detector_temp_drift": 0.1,
                    "slip_ring_error_rate": 0.002,
                    "gantry_vibration_fft": 9.9, # Exceeds limit (safety clamp check: max is 3.2)
                    "gantry_rotation": 0.39
                }
            }
        ]
        
        # Run Bronze -> Silver -> Gold sequentially for each telemetry packet
        last_df_silver = None
        for i, t_msg in enumerate(telemetries):
            print(f"Enviando telemetria {i+1}/4 para processamento...")
            # 1. Run Bronze-to-Silver
            last_df_silver = process_bronze_to_silver(hospital_id, equipamento_id, tipo_eq, t_msg)
            
            # 2. Run Silver-to-Gold
            process_silver_to_gold(hospital_id, equipamento_id, tipo_eq, last_df_silver)
            
        print("\n--- [VALIDATION] Verificando resultados da Silver ---")
        self.assertIsNotNone(last_df_silver)
        
        # Verify that we have 5 records in total (due to hour 2 interpolation)
        print(f"Linhas geradas na camada Silver: {len(last_df_silver)}")
        self.assertEqual(len(last_df_silver), 5, "Deveria ter interpolado a hora faltante, resultando em 5 registros")
        
        # Verify interpolation value (Hour 2 temperature should be 44.0)
        row_hour_2 = last_df_silver.iloc[2]
        print(f"Hora 2 (Interpolada): Timestamp={row_hour_2['timestamp']}, Temp={row_hour_2['tube_temp']}, is_interpolated={row_hour_2['is_interpolated']}")
        self.assertEqual(row_hour_2["tube_temp"], 44.0, "Temperatura interpolada incorreta")
        self.assertTrue(row_hour_2["is_interpolated"], "Linha interpolada não foi marcada com flag is_interpolated=True")
        
        # Verify clamping (gantry_vibration_fft at Hour 4 was sent as 9.9, should be clamped to 3.2 max)
        row_hour_4 = last_df_silver.iloc[4]
        print(f"Hora 4 (Clamped): Vibration={row_hour_4['gantry_vibration_fft']}, Original=9.9, Max=3.2")
        self.assertEqual(row_hour_4["gantry_vibration_fft"], 3.2, "O valor de vibração não foi limitado fisicamente")
        
        print("\n--- [VALIDATION] Verificando resultados da Gold ---")
        # Read gold features from mock S3
        gold_key = f"gold/features/hospital_id={hospital_id}/equipment_id={equipamento_id}/features.parquet"
        self.assertIn((Config.GOLD_BUCKET, gold_key), mock_s3.storage, "O arquivo Gold não foi gerado no bucket")
        
        gold_bytes = mock_s3.storage[(Config.GOLD_BUCKET, gold_key)]
        df_gold = pd.read_parquet(io.BytesIO(gold_bytes))
        
        print(f"Colunas de features agregadas na Gold: {len(df_gold.columns)}")
        self.assertTrue(any("mean_6h" in c for c in df_gold.columns), "Não foram encontrados agregados de 6h na Gold")
        
        # Verify rolling mean of tube_temp over 6h at hour 4 (which is index 4).
        # Temps in 6h window: [40, 42, 44, 46, 48] -> Mean: 44.0
        expected_mean = df_gold.loc[4, "tube_temp_mean_6h"]
        print(f"Média Móvel de Temperatura de 6h no último registro: {expected_mean}")
        self.assertEqual(expected_mean, 44.0)
        
        print("\n--- [VALIDATION] Verificando resultados no Banco SQL (SQLite Fallback) ---")
        session = get_db_session()
        
        # Query Silver table in SQL
        sql_silver = session.query(SilverTelemetry).order_by(SilverTelemetry.timestamp).all()
        print(f"Linhas gravadas no banco SQL (SilverTelemetry): {len(sql_silver)}")
        self.assertEqual(len(sql_silver), 5, "Deveria ter 5 registros gravados no banco SQL (Silver)")
        
        db_hour_2 = sql_silver[2]
        print(f"SQL Hora 2: Temp={db_hour_2.tube_temp}, is_interpolated={db_hour_2.is_interpolated}")
        self.assertEqual(db_hour_2.tube_temp, 44.0)
        self.assertTrue(db_hour_2.is_interpolated)
        
        db_hour_4 = sql_silver[4]
        print(f"SQL Hora 4: Vibration={db_hour_4.gantry_vibration_fft}")
        self.assertEqual(db_hour_4.gantry_vibration_fft, 3.2)
        
        # Query Gold table in SQL
        sql_gold = session.query(GoldEquipmentFeatures).order_by(GoldEquipmentFeatures.timestamp).all()
        print(f"Linhas gravadas no banco SQL (GoldEquipmentFeatures): {len(sql_gold)}")
        self.assertEqual(len(sql_gold), 5, "Deveria ter 5 registros gravados no banco SQL (Gold)")
        
        db_gold_last = sql_gold[4]
        print(f"SQL Gold Últimas Features (Qtd={len(db_gold_last.features)}):")
        self.assertIn("tube_temp_mean_6h", db_gold_last.features)
        self.assertEqual(db_gold_last.features["tube_temp_mean_6h"], 44.0)
        
        session.close()
        print("\n=== [SUCCESS] Todos os testes da pipeline (MinIO + SQL) passaram! ===")

if __name__ == "__main__":
    unittest.main()
