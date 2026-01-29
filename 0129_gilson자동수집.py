"""
CNT 자동 수집 시스템
UV-Vis 분류 결과에 따라 Gilson FC-203B 헤드 위치 자동 이동

사용 전:
1. position_teaching.py로 위치 티칭 (cnt_positions.json 생성)
2. 아래 [설정] 값들 확인 및 수정
"""

import json
import os
import time


# ============================================================
#                    [설정] - 여기만 수정하세요!
# ============================================================

# --- Gilson 통신 설정 ---
GILSON_PORT = 'COM3'          # Gilson 연결 포트 (장치관리자에서 확인)
GILSON_UNIT_ID = 6            # Gilson Unit ID (기본값 6)

# --- 딜레이 시간 설정 (초) ---
UV_MEASURE_TIME = 70          # UV-Vis 측정 시간 (초)
TUBING_DELAY = 343            # UV → Gilson 입구 튜빙 이동 시간 (초) [측정됨]
GILSON_INTERNAL_DELAY = 0     # Gilson 내부 이동 시간 (초) [TODO: 회사 문의 후 수정]

# --- 위치 파일 ---
POSITIONS_FILE = 'cnt_positions.json'  # 티칭된 위치 파일 (position_teaching.py로 생성)

# --- UV-Vis 설정 ---
# UV_PORT = 'COM4'            # UV-Vis 포트 (필요시 추가)

# ============================================================
#                    [설정 끝] - 아래는 건드리지 마세요
# ============================================================


# 라이브러리 import
from gilson_fc203b import GilsonFC203B

# TODO: UV-Vis 분류 함수 import (이미 만들어놓은 코드에서)
# from uv_classifier import classify_spectrum


# ============================================================
#                    자동 계산 값
# ============================================================

# 총 딜레이 = 튜빙 + Gilson 내부
TOTAL_DELAY = TUBING_DELAY + GILSON_INTERNAL_DELAY

# 실제 대기 시간 = 총 딜레이 - UV 측정 시간
# (UV 측정하는 동안 샘플이 이미 이동 중이므로)
WAIT_TIME = TOTAL_DELAY - UV_MEASURE_TIME


# ============================================================
#                    위치 관리
# ============================================================

def load_positions():
    """
    티칭된 위치 불러오기
    
    Returns:
        dict: 위치 딕셔너리 {"금속": {"x": 0, "y": 0}, ...}
    """
    if not os.path.exists(POSITIONS_FILE):
        print(f"❌ 위치 파일 없음: {POSITIONS_FILE}")
        print("   → position_teaching.py로 먼저 위치 티칭하세요!")
        return None
    
    with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
        positions = json.load(f)
    
    print(f"✅ 위치 파일 로드: {POSITIONS_FILE}")
    for name, pos in positions.items():
        print(f"   {name}: ({pos['x']}, {pos['y']}) mm")
    
    return positions


# ============================================================
#                    UV-Vis 분류 (연동 필요)
# ============================================================

def get_uv_classification():
    """
    UV-Vis 스펙트럼 측정 및 분류
    
    TODO: 이미 만들어놓은 UV-Vis 분류 코드와 연동
    
    Returns:
        str: "금속", "반도체", "폐기" 중 하나
    """
    # ============================================
    # TODO: 여기에 UV-Vis 분류 코드 연동
    # 예시:
    # spectrum = measure_spectrum()
    # result = classify_spectrum(spectrum)
    # return result
    # ============================================
    
    # 임시: 수동 입력 (테스트용)
    print("\n" + "="*40)
    print("[UV-Vis 분류 결과 입력]")
    print("  1 = 금속")
    print("  2 = 반도체") 
    print("  3 = 폐기")
    print("="*40)
    
    choice = input("분류 결과 (1-3): ").strip()
    
    mapping = {
        '1': '금속',
        '2': '반도체',
        '3': '폐기'
    }
    
    return mapping.get(choice, '폐기')


# ============================================================
#                    대기 함수 (Ctrl+C 가능)
# ============================================================

def safe_wait(seconds, message="대기 중"):
    """
    Ctrl+C로 중단 가능한 대기 함수
    
    Args:
        seconds: 대기 시간 (초)
        message: 표시할 메시지
    """
    print(f"\n⏳ {message}: {seconds}초")
    
    for remaining in range(int(seconds), 0, -1):
        print(f"\r   남은 시간: {remaining}초   ", end='', flush=True)
        time.sleep(1)
    
    print(f"\r   완료!                    ")


# ============================================================
#                    메인 자동 수집 루프
# ============================================================

def main():
    """CNT 자동 수집 메인 루프"""
    
    print("\n" + "="*60)
    print("          CNT 자동 수집 시스템")
    print("="*60)
    
    # 설정 출력
    print("\n[현재 설정]")
    print(f"  Gilson 포트: {GILSON_PORT}")
    print(f"  Gilson Unit ID: {GILSON_UNIT_ID}")
    print(f"  UV 측정 시간: {UV_MEASURE_TIME}초")
    print(f"  튜빙 딜레이: {TUBING_DELAY}초")
    print(f"  Gilson 내부 딜레이: {GILSON_INTERNAL_DELAY}초")
    print(f"  총 딜레이: {TOTAL_DELAY}초")
    print(f"  실제 대기 시간: {WAIT_TIME}초")
    print("="*60)
    
    # 위치 파일 확인
    positions = load_positions()
    if positions is None:
        return
    
    # Gilson 연결
    print("\n[Gilson 연결]")
    gilson = GilsonFC203B(port=GILSON_PORT, unit_id=GILSON_UNIT_ID)
    
    if not gilson.connect():
        print("❌ Gilson 연결 실패. 종료합니다.")
        return
    
    # 시작 확인
    input("\n[Enter]를 누르면 자동 수집을 시작합니다...")
    
    cycle_count = 1
    
    try:
        while True:
            print(f"\n{'='*20} [Cycle {cycle_count}] {'='*20}")
            
            # ----- Step 1: UV-Vis 측정 및 분류 -----
            print("\n[Step 1] UV-Vis 측정 및 분류")
            classification = get_uv_classification()
            print(f"   → 분류 결과: {classification}")
            
            # ----- Step 2: 대기 (샘플이 Gilson까지 이동) -----
            print(f"\n[Step 2] 샘플 이동 대기")
            safe_wait(WAIT_TIME, "샘플이 Gilson으로 이동 중")
            
            # ----- Step 3: Gilson 헤드 이동 -----
            print(f"\n[Step 3] Gilson 헤드 이동 → {classification}")
            
            if classification in positions:
                pos = positions[classification]
                gilson.move_to_xy(pos['x'], pos['y'])
                print(f"   → 이동 완료: ({pos['x']}, {pos['y']}) mm")
            else:
                print(f"   ⚠️ '{classification}' 위치 없음 → 폐기로 이동")
                if '폐기' in positions:
                    pos = positions['폐기']
                    gilson.move_to_xy(pos['x'], pos['y'])
            
            # ----- Step 4: 수집 완료 -----
            print(f"\n✅ Cycle {cycle_count} 완료: {classification} 수집")
            
            cycle_count += 1
            
            # 다음 사이클
            cont = input("\n다음 사이클? [Enter=계속 / q=종료]: ").strip().lower()
            if cont == 'q':
                break
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자 중단!")
    
    finally:
        # Gilson 연결 해제
        gilson.disconnect()
        print("\n🛑 자동 수집 종료")
        print(f"   총 {cycle_count - 1} 사이클 완료")


# ============================================================
#                    실행
# ============================================================

if __name__ == "__main__":
    main()
