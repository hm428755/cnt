"""
EMS Tech EMP-2000W 펌프 제어 코드
CNT 분리 자동화 시스템용 (펌프 1대 버전)

수정할 때: 아래 [설정] 부분만 바꾸면 됩니다!
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
PUMP_ID = 3              # 펌프 Slave ID (화면 우측하단 확인)
BAUDRATE = 9600          # 통신 속도 (9600 기본)

# --- 펌프1: 정량 주입 설정 ---
SAMPLE_VOLUME = 10       # 샘플 용액 주입량 (ml)
SAMPLE_FLOW_RATE = 0.8   # 샘플 용액 유속 (ml/min)

ELUTION1_VOLUME = 10     # 1차 일루션 주입량 (ml)
ELUTION1_FLOW_RATE = 0.8 # 1차 일루션 유속 (ml/min)

ELUTION2_VOLUME = 50     # 2차 일루션 주입량 (ml)
ELUTION2_FLOW_RATE = 0.8 # 2차 일루션 유속 (ml/min)

# --- 대기 시간 설정 ---
CAMERA_CHECK_DELAY = 1   # 카메라 확인 대기 (초)
ABSORPTION_WAIT = 5      # 용액 흡수 대기 (초)

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

MODE_RPM = 0  # 연속 회전
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
    
    def set_flow_rate(self, ml_per_min):
        """유속 설정 (ml/min → RPM 자동 변환)"""
        rpm = ml_per_min * self.rev_per_ml
        self.instrument.write_register(ADDR_MODE, MODE_RPM)
        self.instrument.write_registers(ADDR_SPEED_INT, self._split_float(rpm))
        print(f"⚡ [{self.port}] 유속: {ml_per_min} ml/min → {rpm:.2f} RPM")
    
    # ========== 고급 제어 ==========
    
    def start_continuous(self, flow_rate_ml_min):
        """연속 운전 시작 (계속 돌림)"""
        self.set_flow_rate(flow_rate_ml_min)
        self.on()
    
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

def main_process():
    """CNT 분리 자동화 메인 루프 (펌프 1대)"""
    
    print("\n" + "="*50)
    print("       CNT 분리 자동화 시스템 (펌프 1대)")
    print("="*50)
    print("\n[현재 설정]")
    print(f"  샘플 주입: {SAMPLE_VOLUME}ml @ {SAMPLE_FLOW_RATE}ml/min")
    print(f"  1차 일루션: {ELUTION1_VOLUME}ml @ {ELUTION1_FLOW_RATE}ml/min")
    print(f"  2차 일루션: {ELUTION2_VOLUME}ml @ {ELUTION2_FLOW_RATE}ml/min")
    print("="*50 + "\n")
    
    # 펌프 연결
    pump = EMPPump(PUMP_PORT, PUMP_ID)
    
    print("\n--- 🚀 공정 시작 ---")
    
    loop_count = 1
    
    try:
        while True:
            print(f"\n{'='*20} [Cycle {loop_count}] {'='*20}")
            
            # [Step 1] 솔레노이드: 샘플 밸브 OPEN
            print("🕹️ [Solenoid] 샘플 밸브 OPEN")
            # solenoid_sample_open()  # TODO: 실제 코드
            
            # [Step 2] 펌프: 샘플 주입 (설정값 사용)
            pump.inject_volume(SAMPLE_VOLUME, SAMPLE_FLOW_RATE)
            
            # [Step 3] 카메라 확인
            print("📷 [Camera] 샘플 흡수 확인 중...")
            # check_camera()  # TODO: 실제 코드
            time.sleep(CAMERA_CHECK_DELAY)
            
            # [Step 4] 솔레노이드: 일루션 밸브 OPEN
            print("🕹️ [Solenoid] 일루션 밸브 OPEN")
            # solenoid_elution_open()  # TODO: 실제 코드
            
            # [Step 5] 펌프: 1차 일루션 주입
            pump.inject_volume(ELUTION1_VOLUME, ELUTION1_FLOW_RATE)
            
            # [Step 6] 흡수 대기
            print("⏳ 용액 흡수 대기...")
            time.sleep(ABSORPTION_WAIT)
            
            # [Step 7] 카메라 확인
            print("📷 [Camera] 1차 일루션 흡수 확인")
            time.sleep(CAMERA_CHECK_DELAY)
            
            # [Step 8] 펌프: 2차 일루션 주입
            pump.inject_volume(ELUTION2_VOLUME, ELUTION2_FLOW_RATE)
            
            # [Step 9] 최종 확인
            print("📷 [Camera] 최종 확인")
            time.sleep(CAMERA_CHECK_DELAY)
            
            print(f"\n✅ Cycle {loop_count} 완료!")
            loop_count += 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자 중단!")
    finally:
        pump.off()
        print("🛑 시스템 종료")


# ============================================================
#                      간단 테스트용
# ============================================================

def test_pump():
    """펌프 단독 테스트"""
    print("\n[펌프 테스트]")
    
    pump = EMPPump(PUMP_PORT, PUMP_ID)
    
    # 유속 설정
    pump.set_flow_rate(0.5)  # 0.5 ml/min
    
    # 5초간 동작
    pump.on()
    print("5초간 동작...")
    time.sleep(5)
    pump.off()
    
    print("테스트 완료!")


if __name__ == "__main__":
    # 전체 공정 실행
    main_process()
    
    # 또는 테스트만 하려면 위를 주석처리하고 아래 실행
    # test_pump()
