"""
EMS Tech EMP-2000W 펌프 제어 코드
순환용 펌프 (0.13 ml/min 연속 운전)

실행하면 계속 돌아감. Ctrl+C로 정지.
"""

import sys
import subprocess
import time

# 라이브러리 자동 설치
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

# --- 통신 설정 ---
PUMP_PORT = 'COM3'       # 펌프 포트 (장치관리자에서 확인)
PUMP_ID = 3              # 순환용 펌프 Slave ID
BAUDRATE = 9600          # 통신 속도 (9600 기본)

# --- 순환 설정 ---
TARGET_RPM = 163         # 0.13 ml/min에 해당하는 RPM (측정값 기준)

# ============================================================
#                    [설정 끝] - 아래는 건드리지 마세요
# ============================================================


# Modbus 레지스터 주소 (EMP-2000WC 매뉴얼 기준)
ADDR_MODE      = 0x2000
ADDR_SPEED_INT = 0x2002
ADDR_RUN_STOP  = 0x200C
MODE_RPM = 0


class EMPPump:
    """EMS Tech 펌프 제어 클래스"""
    
    def __init__(self, port, slave_id):
        self.port = port
        self.slave_id = slave_id
        self.instrument = None
        self.connect()
    
    def connect(self):
        """펌프 연결"""
        try:
            self.instrument = minimalmodbus.Instrument(self.port, self.slave_id)
            self.instrument.serial.baudrate = BAUDRATE
            self.instrument.serial.timeout = 1.0
            print(f"✅ [{self.port}/ID:{self.slave_id}] 연결 성공")
        except Exception as e:
            print(f"❌ [{self.port}] 연결 실패: {e}")
            sys.exit(1)
    
    def _split_float(self, value):
        """실수를 [정수, 소수*100] 리스트로 변환"""
        int_part = int(value)
        dec_part = int(round((value - int_part) * 100))
        return [int_part, dec_part]
    
    def on(self):
        """펌프 시작"""
        self.instrument.write_register(ADDR_RUN_STOP, 1)
        print(f"▶️ [{self.port}] ON")
    
    def off(self):
        """펌프 정지"""
        try:
            self.instrument.write_register(ADDR_RUN_STOP, 0)
            print(f"⏹️ [{self.port}] OFF")
        except:
            pass
    
    def set_rpm(self, rpm):
        """RPM 직접 설정"""
        self.instrument.write_register(ADDR_MODE, MODE_RPM)
        self.instrument.write_registers(ADDR_SPEED_INT, self._split_float(rpm))
        print(f"⚡ [{self.port}] RPM 설정: {rpm}")
    
    def start_continuous(self, rpm):
        """연속 운전 시작"""
        self.set_rpm(rpm)
        self.on()


# ============================================================
#                         메인 프로세스
# ============================================================

def main():
    """순환용 펌프 연속 운전"""
    
    print("\n" + "="*50)
    print("       순환용 펌프 (연속 운전)")
    print("="*50)
    print(f"\n  설정 RPM: {TARGET_RPM}")
    print(f"  예상 유속: 약 0.13 ml/min")
    print("  Ctrl+C로 정지")
    print("="*50 + "\n")
    
    # 펌프 연결
    pump = EMPPump(PUMP_PORT, PUMP_ID)
    
    print("\n--- 🚀 순환 시작 ---")
    
    try:
        # 연속 운전 시작
        pump.start_continuous(TARGET_RPM)
        print("\n🔄 순환 중... (Ctrl+C로 정지)\n")
        
        # 계속 대기
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자 중단!")
    finally:
        pump.off()
        print("🛑 시스템 종료")


if __name__ == "__main__":
    main()

