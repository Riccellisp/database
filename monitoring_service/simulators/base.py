import math
import random
from datetime import datetime

# Failure thresholds copied from historical data generator
FAILURE_THRESHOLDS = {
    "tc": [
        ("superaquecimento do tubo", "tube_temp", ">", 79),
        ("falha no slip ring", "slip_ring_error_rate", ">", 0.075),
        ("desalinhamento do gantry", "gantry_vibration_fft", ">", 1.85),
        ("desgaste do anodo", "anode_rotation_speed", "<", 8500),
    ],
    "raio x": [
        ("superaquecimento do tubo", "tube_heat_units", ">", 790000),
        ("desgaste do filamento", "filament_current", ">", 5.8),
        ("queda de tensao", "tube_voltage", "<", 107),
        ("arco eletrico", "line_voltage_drop", ">", 3.2),
    ],
    "ressonancia magnetica": [
        ("quench", "magnet_temp", ">", 7.0),
        ("perda de helio", "helium_level", "<", 55),
        ("falha de criogenia", "cold_head_efficiency", "<", 74),
        ("falha de gradiente", "gradient_coil_temp", ">", 49),
    ],
    "pet": [
        ("falha HV", "hv_power_stability", "<", 91),
        ("degradacao detector", "coincidence_timing", ">", 430),
        ("aquecimento do cintilador", "scintillator_temp", ">", 38),
    ],
    "ultrassom": [
        ("elemento da sonda queimado", "probe_element_status", "<", 63),
        ("falha da fonte", "psu_voltage_rails", "<", 11.35),
        ("superaquecimento", "transducer_temp", ">", 46),
    ],
    "arco cirurgico": [
        ("travamento mecanico", "vibration", ">", 1.45),
        ("falha de motor", "c_arm_motor_torque", ">", 68),
        ("superaquecimento do gerador", "continuous_heat_rate", ">", 48),
    ],
    "angiografia": [
        ("desgaste mecanico", "vibration", ">", 1.45),
        ("superaquecimento", "continuous_heat_rate", ">", 54),
        ("falha do gerador", "generator_current", ">", 126),
    ],
}

FAILURE_ORIGINS = {
    "superaquecimento do tubo": ("hardware", "alto"),
    "falha no slip ring": ("hardware", "alto"),
    "desalinhamento do gantry": ("hardware", "medio"),
    "desgaste do anodo": ("hardware", "medio"),
    "desgaste do filamento": ("hardware", "medio"),
    "arco eletrico": ("eletrica", "alto"),
    "queda de tensao": ("eletrica", "medio"),
    "quench": ("criogenia", "critico"),
    "perda de helio": ("criogenia", "alto"),
    "falha de criogenia": ("criogenia", "alto"),
    "falha de gradiente": ("hardware", "alto"),
    "falha HV": ("eletrica", "alto"),
    "degradacao detector": ("hardware", "medio"),
    "aquecimento do cintilador": ("hardware", "medio"),
    "elemento da sonda queimado": ("hardware", "medio"),
    "falha da fonte": ("eletrica", "alto"),
    "superaquecimento": ("hardware", "medio"),
    "travamento mecanico": ("mecanica", "alto"),
    "falha de motor": ("mecanica", "medio"),
    "superaquecimento do gerador": ("hardware", "alto"),
    "desgaste mecanico": ("mecanica", "medio"),
    "falha do gerador": ("eletrica", "alto"),
}

LIMITES_FISICOS = {
    "tc": {
        "tube_temp": (25, 105),
        "tube_current": (250, 520),
        "anode_rotation_speed": (7800, 10200),
        "detector_temp_drift": (0, 4.5),
        "slip_ring_error_rate": (0, 0.16),
        "gantry_vibration_fft": (0, 3.2),
        "gantry_rotation": (0.25, 0.62),
    },
    "raio x": {
        "exposure_time": (0.04, 0.45),
        "filament_current": (3.2, 7.4),
        "line_voltage_drop": (0, 5.5),
        "tube_heat_units": (200000, 1200000),
        "tube_voltage": (95, 130),
    },
    "ressonancia magnetica": {
        "cold_head_efficiency": (58, 99.5),
        "gradient_coil_temp": (18, 72),
        "helium_level": (35, 100),
        "helium_pressure": (3.6, 7.8),
        "helium_pressure_psi": (52, 113),
        "magnet_temp": (3.6, 9.5),
        "rf_power_reflection": (0, 18),
        "vibration": (0, 2.6),
    },
    "pet": {
        "coincidence_rate": (25000, 180000),
        "coincidence_timing": (300, 520),
        "count_rate": (20000, 160000),
        "detector_temp": (20, 48),
        "fdg_activity": (1, 35),
        "hv_power_stability": (86, 100),
        "minutes_since_injection": (0, 179),
        "scintillator_temp": (20, 52),
    },
    "ultrassom": {
        "depth": (4, 32),
        "frequency": (2, 15),
        "gain": (5, 95),
        "probe_element_status": (35, 100),
        "psu_voltage_rails": (10.8, 12.6),
        "system_fan_rpm": (900, 4200),
        "transducer_temp": (24, 58),
    },
    "arco cirurgico": {
        "angle_target": (0, 180),
        "c_arm_motor_torque": (25, 86),
        "continuous_heat_rate": (8, 72),
        "generator_current": (55, 155),
        "inverter_frequency": (46, 54),
        "rotation_angle": (0, 360),
        "vibration": (0, 2.8),
    },
    "angiografia": {
        "c_arm_motor_torque": (28, 92),
        "continuous_heat_rate": (10, 78),
        "frame_rate": (7.5, 60),
        "generator_current": (70, 165),
        "inverter_frequency": (46, 54),
        "vibration": (0, 2.8),
    },
}

def clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))

def aproximar(valor: float, alvo: float, taxa: float) -> float:
    return valor + (alvo - valor) * taxa

def aplicar_limites_fisicos(tipo_eq: str, estado: dict) -> dict:
    limites = LIMITES_FISICOS.get(tipo_eq, {})
    for chave, (minimo, maximo) in limites.items():
        if chave in estado:
            estado[chave] = clamp(float(estado[chave]), minimo, maximo)
    return estado

def ciclo_uso_hospitalar(ts: datetime, tipo_eq: str) -> float:
    hora = ts.hour
    dia_util = ts.weekday() < 5
    if 7 <= hora <= 18:
        base = 0.78 if dia_util else 0.38
    elif 19 <= hora <= 22:
        base = 0.44 if dia_util else 0.25
    elif 0 <= hora <= 5:
        base = 0.10 if dia_util else 0.06
    else:
        base = 0.24 if dia_util else 0.14

    multiplicador_tipo = {
        "tc": 1.15,
        "raio x": 1.25,
        "ressonancia magnetica": 0.80,
        "pet": 0.70,
        "ultrassom": 1.10,
        "arco cirurgico": 0.65,
        "angiografia": 0.75,
    }.get(tipo_eq, 1.0)
    sazonalidade = 1.0 + 0.12 * math.sin(2 * math.pi * ts.timetuple().tm_yday / 365)
    ruido = random.gauss(0, 0.04)
    return clamp(base * multiplicador_tipo * sazonalidade + ruido, 0.0, 1.0)

def escolher_modo_de_falha(tipo_eq: str) -> str:
    return random.choice(FAILURE_THRESHOLDS[tipo_eq])[0]

def inicializar_estado_temporal(tipo_eq: str, desgaste: float) -> dict:
    if tipo_eq == "tc":
        return {
            "scan_count": random.randint(12000, 95000),
            "tube_temp": 37 + desgaste * 20,
            "tube_current": 330 + desgaste * 45,
            "anode_rotation_speed": 9800 - desgaste * 900,
            "detector_temp_drift": 0.08 + desgaste * 0.35,
            "slip_ring_error_rate": 0.002 + desgaste * 0.018,
            "gantry_vibration_fft": 0.28 + desgaste * 0.95,
            "gantry_rotation": 0.39 + random.gauss(0, 0.015),
        }
    if tipo_eq == "raio x":
        return {
            "exposure_count": random.randint(8000, 120000),
            "exposure_time": 0.08 + desgaste * 0.08,
            "filament_current": 3.8 + desgaste * 1.25,
            "line_voltage_drop": 0.25 + desgaste * 2.2,
            "tube_heat_units": 310000 + desgaste * 360000,
            "tube_voltage": 121 - desgaste * 6,
        }
    if tipo_eq == "ressonancia magnetica":
        return {
            "cold_head_efficiency": 96 - desgaste * 18,
            "gradient_coil_temp": 25 + desgaste * 12,
            "helium_level": 96 - desgaste * 26,
            "helium_pressure": 4.45 + random.gauss(0, 0.04),
            "helium_pressure_psi": 64 + random.gauss(0, 0.8),
            "magnet_temp": 4.1 + desgaste * 1.8,
            "rf_power_reflection": 1.0 + desgaste * 4.0,
            "vibration": 0.24 + desgaste * 0.55,
        }
    if tipo_eq == "pet":
        return {
            "coincidence_rate": 65000 + desgaste * 9000,
            "coincidence_timing": 350 + desgaste * 35,
            "count_rate": 42000 + desgaste * 20000,
            "detector_temp": 24 + desgaste * 9,
            "fdg_activity": 8 + random.random() * 8,
            "hv_power_stability": 99 - desgaste * 6,
            "minutes_since_injection": random.randint(15, 90),
            "scintillator_temp": 24 + desgaste * 7,
        }
    if tipo_eq == "ultrassom":
        return {
            "depth": random.uniform(6, 26),
            "frequency": random.uniform(3, 12),
            "gain": random.uniform(35, 75),
            "probe_element_status": 99 - desgaste * 28,
            "psu_voltage_rails": 12.1 - desgaste * 0.3,
            "system_fan_rpm": 3350 - desgaste * 850,
            "transducer_temp": 29 + desgaste * 9,
        }
    if tipo_eq == "arco cirurgico":
        return {
            "angle_target": random.uniform(0, 180),
            "c_arm_motor_torque": 38 + desgaste * 18,
            "continuous_heat_rate": 18 + desgaste * 18,
            "generator_current": 78 + desgaste * 9,
            "inverter_frequency": 50 + random.gauss(0, 0.25),
            "rotation_angle": random.uniform(0, 360),
            "vibration": 0.22 + desgaste * 0.72,
        }
    # For "angiografia" or default
    return {
        "c_arm_motor_torque": 40 + desgaste * 20,
        "continuous_heat_rate": 22 + desgaste * 22,
        "frame_rate": random.choice([15.0, 30.0]),
        "generator_current": 92 + desgaste * 14,
        "inverter_frequency": 50 + random.gauss(0, 0.2),
        "vibration": 0.25 + desgaste * 0.78,
    }

def aplicar_rampa_falha(params: dict, tipo_eq: str, modo_falha: str | None, intensidade: float) -> None:
    if not modo_falha:
        return
    intensidade = clamp(intensidade, 0.0, 1.0)
    if tipo_eq == "tc":
        if modo_falha == "falha no slip ring":
            params["gantry_vibration_fft"] += 0.9 * intensidade
            params["slip_ring_error_rate"] += 0.07 * intensidade
        elif modo_falha == "superaquecimento do tubo":
            params["tube_temp"] += 36 * intensidade
            params["detector_temp_drift"] += 1.2 * intensidade
        elif modo_falha == "desalinhamento do gantry":
            params["gantry_vibration_fft"] += 1.1 * intensidade
            params["gantry_rotation"] += 0.11 * intensidade
        else: # desgaste do anodo
            params["anode_rotation_speed"] -= 650 * intensidade
            params["tube_current"] += 38 * intensidade
    elif tipo_eq == "raio x":
        if modo_falha == "queda de tensao":
            params["line_voltage_drop"] += 2.0 * intensidade
            params["tube_voltage"] -= 13 * intensidade
        elif modo_falha == "arco eletrico":
            params["line_voltage_drop"] += 2.4 * intensidade
            params["filament_current"] += 0.9 * intensidade
        elif modo_falha == "desgaste do filamento":
            params["filament_current"] += 1.4 * intensidade
        else: # superaquecimento do tubo
            params["tube_heat_units"] += 260000 * intensidade
            params["filament_current"] += 0.7 * intensidade
    elif tipo_eq == "ressonancia magnetica":
        if modo_falha in ("perda de helio", "quench"):
            params["helium_level"] -= 24 * intensidade
            params["magnet_temp"] += 2.8 * intensidade
        elif modo_falha == "falha de criogenia":
            params["cold_head_efficiency"] -= 18 * intensidade
            params["magnet_temp"] += 1.6 * intensidade
        else: # falha de gradiente (superaquecimento da bobina gradiente)
            params["gradient_coil_temp"] += 18 * intensidade
            params["rf_power_reflection"] += 4 * intensidade
    elif tipo_eq == "pet":
        if modo_falha == "falha HV":
            params["hv_power_stability"] -= 9 * intensidade
        elif modo_falha == "degradacao detector":
            params["detector_temp"] += 8 * intensidade
            params["coincidence_timing"] += 55 * intensidade
        else: # aquecimento do cintilador
            params["scintillator_temp"] += 11 * intensidade
            params["coincidence_timing"] += 25 * intensidade
    elif tipo_eq == "ultrassom":
        if modo_falha == "falha da fonte":
            params["psu_voltage_rails"] -= 0.8 * intensidade
            params["system_fan_rpm"] -= 500 * intensidade
        elif modo_falha == "superaquecimento":
            params["system_fan_rpm"] -= 850 * intensidade
            params["transducer_temp"] += 12 * intensidade
        else: # falha da sonda / elemento da sonda queimado
            params["transducer_temp"] += 8 * intensidade
            params["probe_element_status"] -= 24 * intensidade
    elif tipo_eq in ("arco cirurgico", "angiografia"):
        if modo_falha in ("travamento mecanico", "desgaste mecanico"):
            params["c_arm_motor_torque"] += 16 * intensidade
            params["vibration"] += 0.8 * intensidade
        elif modo_falha == "falha de motor":
            params["c_arm_motor_torque"] += 20 * intensidade
            params["vibration"] += 0.45 * intensidade
        else: # superaquecimento do gerador / superaquecimento
            params["continuous_heat_rate"] += 20 * intensidade
            params["generator_current"] += 23 * intensidade

def detectar_falha(tipo_eq: str, log: dict) -> tuple | None:
    for nome, parametro, operador, limite in FAILURE_THRESHOLDS.get(tipo_eq, []):
        valor = log.get(parametro)
        if valor is None:
            continue
        excedeu = valor > limite if operador == ">" else valor < limite
        if excedeu:
            origem, severidade = FAILURE_ORIGINS.get(nome, ("hardware", "medio"))
            sentido = "acima" if operador == ">" else "abaixo"
            return (
                nome,
                origem,
                severidade,
                f"{parametro} {sentido} do limite operacional ({round(valor, 3)} vs {limite})."
            )
    return None
