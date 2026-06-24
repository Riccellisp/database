from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, JSON
from data_pipeline.database.connection import Base

class StgSilverTelemetry(Base):
    __tablename__ = "stg_silver_telemetry"

    # Composite Primary Key
    timestamp = Column(DateTime, primary_key=True)
    equipamento_id = Column(Integer, primary_key=True)
    
    # Metadata
    hospital_id = Column(Integer, nullable=False)
    tipo = Column(String(50), nullable=False)
    is_interpolated = Column(Boolean, default=False, nullable=False)

    # Sensor Columns (Unified schema - columns not relevant to equipment type will remain NULL)
    # TC
    scan_count = Column(Integer, nullable=True)
    tube_temp = Column(Float, nullable=True)
    tube_current = Column(Float, nullable=True)
    anode_rotation_speed = Column(Float, nullable=True)
    detector_temp_drift = Column(Float, nullable=True)
    slip_ring_error_rate = Column(Float, nullable=True)
    gantry_vibration_fft = Column(Float, nullable=True)
    gantry_rotation = Column(Float, nullable=True)

    # Raio X
    exposure_count = Column(Integer, nullable=True)
    exposure_time = Column(Float, nullable=True)
    filament_current = Column(Float, nullable=True)
    line_voltage_drop = Column(Float, nullable=True)
    tube_heat_units = Column(Float, nullable=True)
    tube_voltage = Column(Float, nullable=True)

    # Ressonancia Magnetica
    cold_head_efficiency = Column(Float, nullable=True)
    gradient_coil_temp = Column(Float, nullable=True)
    helium_level = Column(Float, nullable=True)
    helium_pressure = Column(Float, nullable=True)
    helium_pressure_psi = Column(Float, nullable=True)
    magnet_temp = Column(Float, nullable=True)
    rf_power_reflection = Column(Float, nullable=True)
    vibration = Column(Float, nullable=True)

    # PET
    coincidence_rate = Column(Float, nullable=True)
    coincidence_timing = Column(Float, nullable=True)
    count_rate = Column(Float, nullable=True)
    detector_temp = Column(Float, nullable=True)
    fdg_activity = Column(Float, nullable=True)
    hv_power_stability = Column(Float, nullable=True)
    minutes_since_injection = Column(Integer, nullable=True)
    scintillator_temp = Column(Float, nullable=True)

    # Ultrassom
    depth = Column(Float, nullable=True)
    frequency = Column(Float, nullable=True)
    gain = Column(Float, nullable=True)
    probe_element_status = Column(Float, nullable=True)
    psu_voltage_rails = Column(Float, nullable=True)
    system_fan_rpm = Column(Float, nullable=True)
    transducer_temp = Column(Float, nullable=True)

    # Arco Cirurgico & Angiografia
    angle_target = Column(Float, nullable=True)
    c_arm_motor_torque = Column(Float, nullable=True)
    continuous_heat_rate = Column(Float, nullable=True)
    generator_current = Column(Float, nullable=True)
    inverter_frequency = Column(Float, nullable=True)
    rotation_angle = Column(Float, nullable=True)
    frame_rate = Column(Float, nullable=True)


class SilverTelemetry(Base):
    __tablename__ = "silver_telemetry"

    # Composite Primary Key
    timestamp = Column(DateTime, primary_key=True)
    equipamento_id = Column(Integer, primary_key=True)
    
    # Metadata
    hospital_id = Column(Integer, nullable=False)
    tipo = Column(String(50), nullable=False)
    is_interpolated = Column(Boolean, default=False, nullable=False)

    # Sensor Columns (Unified schema - columns not relevant to equipment type will remain NULL)
    # TC
    scan_count = Column(Integer, nullable=True)
    tube_temp = Column(Float, nullable=True)
    tube_current = Column(Float, nullable=True)
    anode_rotation_speed = Column(Float, nullable=True)
    detector_temp_drift = Column(Float, nullable=True)
    slip_ring_error_rate = Column(Float, nullable=True)
    gantry_vibration_fft = Column(Float, nullable=True)
    gantry_rotation = Column(Float, nullable=True)

    # Raio X
    exposure_count = Column(Integer, nullable=True)
    exposure_time = Column(Float, nullable=True)
    filament_current = Column(Float, nullable=True)
    line_voltage_drop = Column(Float, nullable=True)
    tube_heat_units = Column(Float, nullable=True)
    tube_voltage = Column(Float, nullable=True)

    # Ressonancia Magnetica
    cold_head_efficiency = Column(Float, nullable=True)
    gradient_coil_temp = Column(Float, nullable=True)
    helium_level = Column(Float, nullable=True)
    helium_pressure = Column(Float, nullable=True)
    helium_pressure_psi = Column(Float, nullable=True)
    magnet_temp = Column(Float, nullable=True)
    rf_power_reflection = Column(Float, nullable=True)
    vibration = Column(Float, nullable=True)

    # PET
    coincidence_rate = Column(Float, nullable=True)
    coincidence_timing = Column(Float, nullable=True)
    count_rate = Column(Float, nullable=True)
    detector_temp = Column(Float, nullable=True)
    fdg_activity = Column(Float, nullable=True)
    hv_power_stability = Column(Float, nullable=True)
    minutes_since_injection = Column(Integer, nullable=True)
    scintillator_temp = Column(Float, nullable=True)

    # Ultrassom
    depth = Column(Float, nullable=True)
    frequency = Column(Float, nullable=True)
    gain = Column(Float, nullable=True)
    probe_element_status = Column(Float, nullable=True)
    psu_voltage_rails = Column(Float, nullable=True)
    system_fan_rpm = Column(Float, nullable=True)
    transducer_temp = Column(Float, nullable=True)

    # Arco Cirurgico & Angiografia
    angle_target = Column(Float, nullable=True)
    c_arm_motor_torque = Column(Float, nullable=True)
    continuous_heat_rate = Column(Float, nullable=True)
    generator_current = Column(Float, nullable=True)
    inverter_frequency = Column(Float, nullable=True)
    rotation_angle = Column(Float, nullable=True)
    frame_rate = Column(Float, nullable=True)


class GoldEquipmentFeatures(Base):
    __tablename__ = "gold_equipment_features"

    # Composite Primary Key
    timestamp = Column(DateTime, primary_key=True)
    equipamento_id = Column(Integer, primary_key=True)
    
    # Metadata
    is_interpolated = Column(Boolean, default=False, nullable=False)
    
    # Features Store (Stores all 130+ rolling features as a flat JSON dictionary)
    features = Column(JSON, nullable=False)
