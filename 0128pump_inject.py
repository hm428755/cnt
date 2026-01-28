"""
EMS Tech EMP-2000W 펌프 제어 코드
주입용 펌프 (샘플, 일루션 정량 주입)

순환용 펌프 먼저 실행한 후 이거 실행하세요!
"""

import sys
import subprocess
import time

try:
    import minimalmodbus
except ImportError:
    print("⚠️ minimalmodbus 설치 중...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "minimalmodbus"])
    import minimalmodbus
    print("✅ 설치 완료!")


# ============================================================
#                    [설정] - 여기만 수정하세요!
# ============================================================

PORT = 'COM3'            # 포트
SLAVE_ID = 2             # 주입용 펌프 ID
BAUDRATE = 9600

# --- 정량 주입 설정 ---
SAMPLE_VOLUME = 10       # 샘플 주입량 (ml)
SAMPLE_FLOW_RATE = 0.8   # 샘플 유속 (ml/min)

ELUTION1_VOLUME = 10     # 1차 일루션 주입량 (ml)
ELUTION1_FLOW_RATE = 0.8 # 1차 일루션 유속 (ml/min)

ELUTION2_VOLUME = 50     # 2차 일루션 주입량 (ml)
ELUTION2_FLOW_RATE = 0.8 # 2차 일루션 유속 (ml/min)

# ============================================================

ADDR_MODE      = 0x2000
ADDR_SPEED_INT = 0x2002
ADDR_REV_INT   = 0x2004
ADDR_RUN_STOP  = 0x200C
MODE_REV = 1


def safe_sleep(seconds):
    """Ctrl+C 잘 먹히는 대기"""
    for _ in range(int(seconds)):
        time.sleep(1)
    remaining = seconds - int(seconds)
    if remaining > 0:
        time.sleep(remaining)


class Pump:
    def __init__(self):
        self.instrument = minimalmodbus.Instrument(PORT, SLAVE_ID)
        self.instrument.serial.baudrate = BAUDRATE
        self.instrument.serial.timeout = 2.0
        self.rev_per_ml = 1.0  # 캘리브레이션 (나중에 측정 후 수정)
        print(f"✅ [주입용 펌프] 연결 성공 (ID:{SLAVE_ID})")
    
    def on(self):
        self.instrument.write_register(ADDR_RUN_STOP, 1)
        print("▶️ 펌프 ON")
    
    def off(self):
        try:
            self.instrument.write_register(ADDR_RUN_STOP, 0)
            print("⏹️ 펌프 OFF")
        except:
            pass
    
    def inject(self, volume_ml, flow_rate):
        """정량 주입"""
        rpm = flow_rate * self.rev_per_ml
        rev = volume_ml * self.rev_per_ml
        expected_time = (volume_ml / flow_rate) * 60
        
        print(f"\n💉 정량 주입")
        print(f"   목표: {volume_ml}ml @ {flow_rate}ml/min")
        print(f"   계산: {rpm:.2f} RPM / {rev:.2f} Rev")
        print(f"   예상: {expected_time:.1f}초")
        
        # 모드 설정
        self.instrument.write_register(ADDR_MODE, MODE_REV)
        time.sleep(0.1)
        
        # RPM 설정
        int_part = int(rpm)
        dec_part = int(round((rpm - int_part) * 100))
        self.instrument.write_registers(ADDR_SPEED_INT, [int_part, dec_part])
        time.sleep(0.1)
        
        # 회전수 설정
        int_part = int(rev)
        dec_part = int(round((rev - int_part) * 100))
        self.instrument.write_registers(ADDR_REV_INT, [int_part, dec_part])
        time.sleep(0.1)
        
        # 시작
        self.on()
        
        # 완료 대기
        safe_sleep(expected_time + 2)
        print(f"✅ 주입 완료 ({volume_ml}ml)")


def main():
    print("\n" + "="*40)
    print("   주입용 펌프 (정량 주입)")
    print("="*40)
    print(f"  샘플: {SAMPLE_VOLUME}ml @ {SAMPLE_FLOW_RATE}ml/min")
    print(f"  1차 일루션: {ELUTION1_VOLUME}ml @ {ELUTION1_FLOW_RATE}ml/min")
    print(f"  2차 일루션: {ELUTION2_VOLUME}ml @ {ELUTION2_FLOW_RATE}ml/min")
    print("  Ctrl+C로 정지")
    print("="*40 + "\n")
    
    pump = Pump()
    loop_count = 1
    
    try:
        while True:
            print(f"\n{'='*15} [Cycle {loop_count}] {'='*15}")
            
            # 샘플 주입
            input("\n[Enter] 샘플 주입 시작...")
            pump.inject(SAMPLE_VOLUME, SAMPLE_FLOW_RATE)
            
            # 1차 일루션
            input("\n[Enter] 1차 일루션 시작...")
            pump.inject(ELUTION1_VOLUME, ELUTION1_FLOW_RATE)
            
            # 2차 일루션
            input("\n[Enter] 2차 일루션 시작...")
            pump.inject(ELUTION2_VOLUME, ELUTION2_FLOW_RATE)
            
            print(f"\n✅ Cycle {loop_count} 완료!")
            loop_count += 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Ctrl+C 감지!")
    finally:
        pump.off()
        print("🛑 종료")


if __name__ == "__main__":
    main()
