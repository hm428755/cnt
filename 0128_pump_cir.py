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

# --- 연속 순환 설정 ---
FLOW_RATE = 0.13         # 유속 (ml/min)

# ============================================================
#                    [설정 끝] - 아래는 건드리지 마세요
# ============================================================


# Modbus 레지스터 주소 (EMP-2000WC 매뉴얼 기준)
ADDR_MODE      = 0x2000  # 모드 (0=RPM, 1=Revolution)
ADDR_SPEED_INT = 0x2002  # 속도 정수부
ADDR_SPEED_DEC = 0x2003  # 속도 소수부
ADDR_RUN_STOP  = 0x200C  # 동작 (0=Stop, 1=Run)
ADDR_CAL_INT   = 0x2009  # 1ml당 회전수 정수부
ADDR_CAL_DEC   = 0x200A  # 1ml당 회전수 소수부

MODE_RPM = 0  # 연속 회전


class EMPPump:
    """EMS Tech 펌프 제어 클래스"""
    
    def __init__(self, port, slave_id):
        self.port = port
        self.slave_id = slave_id
        self.instrument = None
        self.rev_per_ml = 1.0  # 1ml당 회전수 (캘리브레이션)
        self.connect()
    
    def connect(self):
        """펌프 연결"""
        try:
            self.instrument = minimalmodbus.Instrument(self.port, self.slave_id)
            self.instrument.serial.baudrate = BAUDRATE
            self.instrument.serial.timeout = 1.0
            print(f"✅ [{self.port}/ID:{self.slave_id}] 연결 성공")
            self.read_calibration()
        except Exception as e:
            print(f"❌ [{self.port}] 연결 실패: {e}")
            sys.exit(1)
    
    def read_calibration(self):
        """캘리브레이션 값 읽기 (1ml당 회전수)"""
        try:
            vals = self.instrument.read_registers(ADDR_CAL_INT, 2)
            self.rev_per_ml = vals[0] + (vals[1] / 1000.0)
            print(f"   📊 캘리브레이션: {self.rev_per_ml:.3f} rev/ml")
        except Exception as e:
            print(f"   ⚠️ 캘리브레이션 읽기 실패 (기본값 1.0): {e}")
            self.rev_per_ml = 1.0
    
    def _split_float(self, value):
        """실수를 [정수, 소수*100] 리스트로 변환"""
        int_part = int(value)
        dec_part = int(round((value - int_part) * 100))
        return [int_part, dec_part]
    
    # ========== 기본 제어 ==========
    
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
    
    def set_flow_rate(self, ml_per_min):
        """유속 설정 (ml/min → RPM 자동 변환)"""
        rpm = ml_per_min * self.rev_per_ml
        self.instrument.write_register(ADDR_MODE, MODE_RPM)
        self.instrument.write_registers(ADDR_SPEED_INT, self._split_float(rpm))
        print(f"⚡ [{self.port}] 유속: {ml_per_min} ml/min → {rpm:.2f} RPM")
    
    def start_continuous(self, flow_rate_ml_min):
        """연속 운전 시작 (계속 돌림)"""
        self.set_flow_rate(flow_rate_ml_min)
        self.on()


# ============================================================
#                         메인 프로세스
# ============================================================

def main():
    """순환용 펌프 연속 운전"""
    
    print("\n" + "="*50)
    print("       순환용 펌프 (연속 운전)")
    print("="*50)
    print(f"\n  유속: {FLOW_RATE} ml/min")
    print("  Ctrl+C로 정지")
    print("="*50 + "\n")
    
    # 펌프 연결
    pump = EMPPump(PUMP_PORT, PUMP_ID)
    
    print("\n--- 🚀 순환 시작 ---")
    
    try:
        # 연속 운전 시작
        pump.start_continuous(FLOW_RATE)
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
