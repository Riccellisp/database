import random
from monitoring_service.simulators.base import (
    clamp, aproximar, aplicar_limites_fisicos, aplicar_rampa_falha
)

def atualizar_estado_temporal(
    tipo_eq: str,
    estado: dict,
    desgaste: float,
    uso: float,
    operational_state: str,
    modo_falha: str | None,
    intensidade_falha: float,
) -> tuple[dict, float]:
    estado = dict(estado)
    em_manutencao = (operational_state == "EM_MANUTENCAO")
    
    # Calculate wear factor based on operational state
    fator_estado = {
        "NORMAL": 1.0, 
        "DEGRADANDO": 1.35, 
        "PRE_FALHA": 2.2, 
        "FALHA": 2.9, 
        "EM_MANUTENCAO": -3.0
    }[operational_state]
    
    # Update wear (desgaste)
    desgaste = clamp(desgaste + 0.00002 + uso * 0.00022 * max(0.2, fator_estado), 0.0, 1.0)
    if em_manutencao:
        desgaste = clamp(desgaste - 0.0012, 0.0, 1.0)
        uso = 0.0

    if tipo_eq == "tc":
        scans = int(round(uso * random.randint(2, 12)))
        estado["scan_count"] += scans
        alvo_temp = 35 + uso * 32 + desgaste * 18 + (10 * intensidade_falha if modo_falha == "superaquecimento do tubo" else 0)
        estado["tube_temp"] = aproximar(estado["tube_temp"], alvo_temp, 0.12) + random.gauss(0, 0.18)
        estado["tube_current"] = aproximar(estado["tube_current"], 330 + uso * 85 + desgaste * 55, 0.10) + random.gauss(0, 1.2)
        estado["anode_rotation_speed"] -= uso * (0.08 + desgaste * 0.08) + random.random() * 0.02
        estado["gantry_vibration_fft"] += uso * desgaste * 0.003 + random.gauss(0, 0.01)
        estado["slip_ring_error_rate"] += max(0, estado["gantry_vibration_fft"] - 0.7) * 0.00008 + desgaste * 0.00002
        estado["detector_temp_drift"] = aproximar(estado["detector_temp_drift"], 0.1 + max(0, estado["tube_temp"] - 42) * 0.035 + desgaste * 0.4, 0.04)
        estado["gantry_rotation"] += random.gauss(0, 0.006) + estado["gantry_vibration_fft"] * 0.0004
        
    elif tipo_eq == "raio x":
        exposicoes = int(round(uso * random.randint(4, 24)))
        estado["exposure_count"] += exposicoes
        estado["exposure_time"] = clamp(estado["exposure_time"] + random.gauss(0, 0.004), 0.04, 0.45)
        estado["tube_heat_units"] += exposicoes * (700 + desgaste * 900) - (12000 if uso < 0.2 or em_manutencao else 4200)
        estado["filament_current"] = 3.7 + desgaste * 1.15 + max(0, estado["tube_heat_units"] - 450000) * 0.000002 + random.gauss(0, 0.025)
        estado["line_voltage_drop"] += uso * desgaste * 0.006 + random.gauss(0, 0.01)
        estado["tube_voltage"] = 122 - estado["line_voltage_drop"] * 3.5 + random.gauss(0, 0.35)
        
    elif tipo_eq == "ressonancia magnetica":
        estado["helium_level"] -= 0.0015 + desgaste * 0.002 + uso * 0.001
        estado["cold_head_efficiency"] -= desgaste * 0.003 + random.gauss(0, 0.01)
        alvo_magnet = 4.1 + max(0, 82 - estado["cold_head_efficiency"]) * 0.035 + max(0, 72 - estado["helium_level"]) * 0.045
        estado["magnet_temp"] = aproximar(estado["magnet_temp"], alvo_magnet, 0.05) + random.gauss(0, 0.012)
        alvo_gradiente = 25 + uso * 18 + max(0, estado["magnet_temp"] - 4.5) * 4.0 + desgaste * 7
        estado["gradient_coil_temp"] = aproximar(estado["gradient_coil_temp"], alvo_gradiente, 0.08) + random.gauss(0, 0.08)
        estado["vibration"] += desgaste * 0.0008 + random.gauss(0, 0.004)
        estado["rf_power_reflection"] += max(0, estado["vibration"] - 0.55) * 0.018 + random.gauss(0, 0.015)
        estado["helium_pressure"] = 4.4 + (estado["magnet_temp"] - 4.2) * 0.2 + random.gauss(0, 0.04)
        estado["helium_pressure_psi"] = estado["helium_pressure"] * 14.5
        
    elif tipo_eq == "pet":
        estado["minutes_since_injection"] = (estado["minutes_since_injection"] + 60) % 180
        estado["fdg_activity"] = max(1.0, estado["fdg_activity"] * 0.82 + (5 + 8 * uso if estado["minutes_since_injection"] < 60 else 0))
        estado["count_rate"] = 26000 + estado["fdg_activity"] * 3500 + random.gauss(0, 1200)
        estado["coincidence_rate"] = estado["count_rate"] * (1.15 + random.gauss(0, 0.03))
        estado["detector_temp"] = aproximar(estado["detector_temp"], 24 + uso * 8 + desgaste * 8, 0.07) + random.gauss(0, 0.05)
        estado["scintillator_temp"] = aproximar(estado["scintillator_temp"], 24 + max(0, estado["count_rate"] - 50000) * 0.00012 + desgaste * 7, 0.08) + random.gauss(0, 0.04)
        estado["coincidence_timing"] = aproximar(estado["coincidence_timing"], 350 + max(0, estado["detector_temp"] - 28) * 4.2 + desgaste * 26, 0.06) + random.gauss(0, 0.8)
        estado["hv_power_stability"] -= desgaste * 0.004 + uso * 0.002 + random.gauss(0, 0.01)
        
    elif tipo_eq == "ultrassom":
        estado["system_fan_rpm"] = aproximar(estado["system_fan_rpm"], 3350 - desgaste * 900 - intensidade_falha * 450, 0.035) + random.gauss(0, 4)
        estado["transducer_temp"] = aproximar(estado["transducer_temp"], 29 + uso * 12 + max(0, 2600 - estado["system_fan_rpm"]) * 0.004 + desgaste * 8, 0.09) + random.gauss(0, 0.07)
        estado["probe_element_status"] -= max(0, estado["transducer_temp"] - 38) * 0.004 + desgaste * 0.006
        estado["psu_voltage_rails"] -= desgaste * 0.0006 + random.gauss(0, 0.006)
        estado["depth"] = clamp(estado["depth"] + random.gauss(0, 0.08), 4, 32)
        estado["frequency"] = clamp(estado["frequency"] + random.gauss(0, 0.03), 2, 15)
        estado["gain"] = clamp(estado["gain"] + random.gauss(0, 0.25), 5, 95)
        
    elif tipo_eq == "arco cirurgico":
        estado["angle_target"] = (estado["angle_target"] + random.gauss(0, 10) * uso) % 180
        estado["rotation_angle"] = (estado["rotation_angle"] + uso * random.uniform(3, 22)) % 360
        estado["c_arm_motor_torque"] += uso * desgaste * 0.08 + random.gauss(0, 0.08)
        estado["vibration"] += max(0, estado["c_arm_motor_torque"] - 48) * 0.0015 + random.gauss(0, 0.006)
        estado["continuous_heat_rate"] = aproximar(estado["continuous_heat_rate"], 18 + uso * 28 + desgaste * 16, 0.10) + random.gauss(0, 0.08)
        estado["generator_current"] = aproximar(estado["generator_current"], 78 + max(0, estado["continuous_heat_rate"] - 25) * 1.05 + desgaste * 8, 0.10) + random.gauss(0, 0.09)
        estado["inverter_frequency"] += random.gauss(0, 0.03)
        
    else:  # "angiografia" or default
        estado["frame_rate"] = random.choices([7.5, 15.0, 30.0, 60.0], weights=[0.05, 0.25, 0.55, 0.15], k=1)[0] if uso > 0.25 else 7.5
        estado["continuous_heat_rate"] = aproximar(estado["continuous_heat_rate"], 22 + uso * estado["frame_rate"] * 0.45 + desgaste * 16, 0.10) + random.gauss(0, 0.08)
        estado["generator_current"] = aproximar(estado["generator_current"], 92 + max(0, estado["continuous_heat_rate"] - 35) * 1.2 + desgaste * 10, 0.10) + random.gauss(0, 0.12)
        estado["c_arm_motor_torque"] += uso * desgaste * 0.09 + random.gauss(0, 0.08)
        estado["vibration"] += desgaste * uso * 0.003 + max(0, estado["c_arm_motor_torque"] - 50) * 0.001 + random.gauss(0, 0.006)
        estado["inverter_frequency"] += random.gauss(0, 0.03)

    # Apply failures ramps if any
    aplicar_rampa_falha(estado, tipo_eq, modo_falha, intensidade_falha)
    
    # Cooldown effect during maintenance
    if em_manutencao:
        for chave in ("tube_temp", "gradient_coil_temp", "detector_temp", "scintillator_temp", "transducer_temp", "continuous_heat_rate"):
            if chave in estado:
                estado[chave] *= 0.985
        for chave in ("hv_power_stability", "cold_head_efficiency", "probe_element_status"):
            if chave in estado:
                # Recover slightly
                estado[chave] = min(99.5, estado[chave] + 0.05)

    # Force physical limits clamping
    estado = aplicar_limites_fisicos(tipo_eq, estado)
    return estado, desgaste

def formatar_parametros(tipo_eq: str, estado: dict) -> dict:
    """
    Returns only the clean observable physical parameters, stripping away
    any simulation states or internal metadata, to represent raw telemetry.
    """
    estado = aplicar_limites_fisicos(tipo_eq, dict(estado))
    params = {}
    for chave, valor in estado.items():
        if chave in ("scan_count", "exposure_count", "minutes_since_injection"):
            params[chave] = int(max(0, round(valor)))
        elif chave == "frame_rate":
            params[chave] = float(valor)
        else:
            params[chave] = round(float(valor), 3)
    return params
