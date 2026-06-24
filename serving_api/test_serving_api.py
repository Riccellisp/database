import unittest
from unittest.mock import MagicMock
from fastapi import status
from fastapi.testclient import TestClient

# Mock database dependencies and imports before importing app to avoid local postgres attempts
import sys
from datetime import datetime

# Setup mock DB dependency
mock_db = MagicMock()

def mock_get_db():
    yield mock_db

# Patch dependency in connection
import serving_api.database.connection
serving_api.database.connection.get_db = mock_get_db

from serving_api.main import app
from data_pipeline.database.models import SilverTelemetry, GoldEquipmentFeatures

class TestServingAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        mock_db.reset_mock()

    def test_health_check_healthy(self):
        print("\n=== [API TEST] Testando Endpoint /health (Saudável) ===")
        # Setup mock db query to execute successfully
        mock_db.execute.return_value = MagicMock()
        
        response = self.client.get("/api/v1/health")
        print("Response:", response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "healthy")

    def test_health_check_unhealthy(self):
        print("\n=== [API TEST] Testando Endpoint /health (Instável) ===")
        # Setup mock db query to fail
        mock_db.execute.side_effect = Exception("Conexão falhou")
        
        response = self.client.get("/api/v1/health")
        print("Response status:", response.status_code)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_get_telemetry_not_found(self):
        print("\n=== [API TEST] Testando Endpoint /telemetry (Equipamento não encontrado) ===")
        # Setup query chain to return empty list
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        response = self.client.get("/api/v1/equipments/999/telemetry")
        print("Response:", response.json())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_telemetry_success(self):
        print("\n=== [API TEST] Testando Endpoint /telemetry (Sucesso) ===")
        # Mock records
        t_now = datetime(2026, 6, 7, 12, 0, 0)
        mock_record = SilverTelemetry(
            timestamp=t_now,
            equipamento_id=1,
            hospital_id=1,
            tipo="tc",
            is_interpolated=False,
            tube_temp=42.5,
            gantry_vibration_fft=0.31
        )
        
        # Setup query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_record]
        
        response = self.client.get("/api/v1/equipments/1/telemetry")
        print("Response:", response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()[0]
        self.assertEqual(data["equipamento_id"], 1)
        self.assertEqual(data["tube_temp"], 42.5)
        self.assertEqual(data["timestamp"], t_now.isoformat())
        self.assertNotIn("exposure_count", data, "Campos nulos não deveriam ser enviados no payload")

    def test_get_features_success(self):
        print("\n=== [API TEST] Testando Endpoint /features (Sucesso) ===")
        # Mock record
        t_now = datetime(2026, 6, 7, 12, 0, 0)
        mock_feature_record = GoldEquipmentFeatures(
            timestamp=t_now,
            equipamento_id=1,
            is_interpolated=True,
            features={"tube_temp_mean_6h": 44.0, "vibration_std_12h": 0.05}
        )
        
        # Setup query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_feature_record
        
        response = self.client.get("/api/v1/equipments/1/features")
        print("Response:", response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data["equipamento_id"], 1)
        self.assertTrue(data["is_interpolated"])
        self.assertEqual(data["features"]["tube_temp_mean_6h"], 44.0)

    def test_get_hospital_telemetry_success(self):
        print("\n=== [API TEST] Testando Endpoint /hospitals/{id}/telemetry (Sucesso) ===")
        t_now = datetime(2026, 6, 7, 12, 0, 0)
        mock_record = SilverTelemetry(
            timestamp=t_now,
            equipamento_id=1,
            hospital_id=1,
            tipo="tc",
            is_interpolated=False,
            tube_temp=42.5
        )
        
        # Setup query chain
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_record]
        
        response = self.client.get("/api/v1/hospitals/1/telemetry")
        print("Response:", response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]["hospital_id"], 1)

    def test_get_hospital_features_success(self):
        print("\n=== [API TEST] Testando Endpoint /hospitals/{id}/features (Sucesso) ===")
        t_now = datetime(2026, 6, 7, 12, 0, 0)
        mock_feature_record = GoldEquipmentFeatures(
            timestamp=t_now,
            equipamento_id=1,
            is_interpolated=False,
            features={"tube_temp_mean_6h": 44.0}
        )
        
        # Mocking db.query.filter.distinct.all() to return [(1,)] for equipment IDs
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = [(1,)]
        
        # Mocking the subsequent loop query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_feature_record
        
        response = self.client.get("/api/v1/hospitals/1/features")
        print("Response:", response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()[0]["equipamento_id"], 1)
        self.assertEqual(response.json()[0]["features"]["tube_temp_mean_6h"], 44.0)

    def test_get_hospital_equipment_data_success(self):
        print("\n=== [API TEST] Testando Endpoint /hospitals/{h_id}/equipments/{e_id} (Sucesso) ===")
        t_now = datetime(2026, 6, 7, 12, 0, 0)
        mock_record = SilverTelemetry(
            timestamp=t_now,
            equipamento_id=1,
            hospital_id=1,
            tipo="tc",
            is_interpolated=False,
            tube_temp=42.5
        )
        mock_feature_record = GoldEquipmentFeatures(
            timestamp=t_now,
            equipamento_id=1,
            is_interpolated=False,
            features={"tube_temp_mean_6h": 44.0}
        )

        # Mocking the telemetry query
        mock_query_telemetry = MagicMock()
        mock_db.query.return_value = mock_query_telemetry
        mock_query_telemetry.filter.return_value = mock_query_telemetry
        mock_query_telemetry.order_by.return_value = mock_query_telemetry
        mock_query_telemetry.limit.return_value = mock_query_telemetry
        mock_query_telemetry.all.return_value = [mock_record]

        # Mocking the features query (first)
        mock_query_telemetry.first.return_value = mock_feature_record

        response = self.client.get("/api/v1/hospitals/1/equipments/1")
        print("Response:", response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertEqual(data["hospital_id"], 1)
        self.assertEqual(data["equipamento_id"], 1)
        self.assertEqual(len(data["telemetry"]), 1)
        self.assertEqual(data["telemetry"][0]["tube_temp"], 42.5)
        self.assertEqual(data["features"]["features"]["tube_temp_mean_6h"], 44.0)

    def test_get_hospital_equipment_data_not_found(self):
        print("\n=== [API TEST] Testando Endpoint /hospitals/{h_id}/equipments/{e_id} (Não Encontrado) ===")
        # Setup telemetry query chain to return empty list
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        response = self.client.get("/api/v1/hospitals/1/equipments/999")
        print("Response:", response.json())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

if __name__ == "__main__":
    unittest.main()

