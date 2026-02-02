"""
실험 설정 파일 - 여기만 수정하세요!
"""

# === 펌프 하드웨어 설정 ===
PUMP_CIRCULATION = {
    "port": "COM4",
    "slave_id": 3,
    "name": "순환펌프"
}

PUMP_INJECTION = {
    "port": "COM3",
    "slave_id": 2,
    "name": "주입펌프"
}

BAUDRATE = 9600

# === 실험 파라미터 ===
CONDITIONING_VOLUME = 400       # 컨디셔닝 주입량 (ml)
CONDITIONING_FLOW_RATE = 5    # 컨디셔닝 유속 (ml/min)
SLOW_FLOW_RATE = 0.13           # 샘플/일루션 유속 (ml/min)
SAMPLE_VOLUME = 10              # 샘플 주입량 (ml)
ELUTION_VOLUME = 50             # 일루션 주입량 (ml) - 추후 업데이트

# === 캘리브레이션 ===
# None이면 펌프에서 자동으로 읽어옴 (rev/mL)
# 수동 지정하려면 숫자 입력 (예: 12.54)
REV_PER_ML = None
