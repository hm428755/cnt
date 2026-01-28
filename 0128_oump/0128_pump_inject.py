"""
EMS Tech EMP-2000W 펌프 제어 코드
주입용 펌프 (샘플, 일루션 정량 주입)

순환용 펌프 먼저 실행한 후 이거 실행하세요!
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
PUMP_ID = 2              # 주입용 펌프 Slave ID
BAUDRATE = 9600          # 통신 속도 (9600 기본)

# --- 정량 주입 설정 ---
SAMPLE_VOLUME = 10       # 샘플 용액 주입량 (ml)
SAMPLE_FLOW_RATE = 0.8   # 샘플 용액 유속 (ml/min)

ELUTION1_VOLUME = 10     # 1차 일루션 주입량 (ml)
ELUTION1_FLOW_RATE = 0.8 # 1차 일루션 유속 (ml/min)

ELUTION2_VOLUME = 50     # 2차 일루션 주입량 (ml)
ELUTION2_FLOW_RATE = 0.8 # 2차 일루션 유속 (ml/min)

# ============================================================
#                    [설정 끝] - 아래는 건드리지 마세요
# ============================================================


# Modbus 레지스터 주소 (EMP-2000WC 매뉴얼 기준)
ADDR_MODE      = 0x2000  # 모드 (0=RPM, 1=Revolution)
ADDR_SPEED_INT = 0x2002  # 속도 정수부
ADDR_SPEED_DEC = 0x2003  # 속도 소수부
ADDR_REV_INT   = 0x2004  # 회전수 정수부
ADDR_REV_DEC   = 0x2005  # 회전수 소수부
ADDR_RUN_STOP  = 0x200C  # 동작 (0=Stop, 1=Run)
ADDR_CAL_INT   = 0x2009  # 1ml당 회전수 정수부
ADDR_CAL_DEC   = 0x200A  # 1ml당 회전수 소수부

MODE_REV = 1  # 정량 회전


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
    
    def inject_volume(self, volume_ml, flow_rate_ml_min, wait_complete=True):
        """정량 주입 (지정량 주입 후 자동 정지)"""
        # 계산
        target_rpm = flow_rate_ml_min * self.rev_per_ml
        target_rev = volume_ml * self.rev_per_ml
        expected_time = (volume_ml / flow_rate_ml_min) * 60
        
        print(f"\n💉 [{self.port}] 정량 주입")
        print(f"   목표: {volume_ml}ml @ {flow_rate_ml_min}ml/min")
        print(f"   계산: {target_rpm:.2f} RPM / {target_rev:.2f} Rev")
        print(f"   예상: {expected_time:.1f}초")
        
        try:
            # 설정
            self.instrument.write_register(ADDR_MODE, MODE_REV)
            self.instrument.write_registers(ADDR_SPEED_INT, self._split_float(target_rpm))
            self.instrument.write_registers(ADDR_REV_INT, self._split_float(target_rev))
            
            # 시작
            self.on()
            
            # 완료 대기
            if wait_complete:
                time.sleep(expected_time + 2)
                print(f"✅ 주입 완료 ({volume_ml}ml)")
                
        except Exception as e:
            print(f"❌ 주입 에러: {e}")


# ============================================================
#                         메인 프로세스
# ============================================================

def main():
    """주입용 펌프 메인 루프"""
    
    print("\n" + "="*50)
    print("       주입용 펌프 (정량 주입)")
    print("="*50)
    print("\n[현재 설정]")
    print(f"  샘플 주입: {SAMPLE_VOLUME}ml @ {SAMPLE_FLOW_RATE}ml/min")
    print(f"  1차 일루션: {ELUTION1_VOLUME}ml @ {ELUTION1_FLOW_RATE}ml/min")
    print(f"  2차 일루션: {ELUTION2_VOLUME}ml @ {ELUTION2_FLOW_RATE}ml/min")
    print("  Ctrl+C로 정지")
    print("="*50 + "\n")
    
    # 펌프 연결
    pump = EMPPump(PUMP_PORT, PUMP_ID)
    
    print("\n--- 🚀 공정 시작 ---")
    
    loop_count = 1
    
    try:
        while True:
            print(f"\n{'='*20} [Cycle {loop_count}] {'='*20}")
            
            # [Step 1] 샘플 주입
            input("\n[Enter] 샘플 주입 시작...")
            print("🕹️ [Solenoid] 샘플 밸브 OPEN")
            pump.inject_volume(SAMPLE_VOLUME, SAMPLE_FLOW_RATE)
            
            # [Step 2] 1차 일루션
            input("\n[Enter] 1차 일루션 시작...")
            print("🕹️ [Solenoid] 일루션 밸브 OPEN")
            pump.inject_volume(ELUTION1_VOLUME, ELUTION1_FLOW_RATE)
            
            # [Step 3] 2차 일루션
            input("\n[Enter] 2차 일루션 시작...")
            pump.inject_volume(ELUTION2_VOLUME, ELUTION2_FLOW_RATE)
            
            print(f"\n✅ Cycle {loop_count} 완료!")
            loop_count += 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자 중단!")
    finally:
        pump.off()
        print("🛑 시스템 종료")


if __name__ == "__main__":
    main()
