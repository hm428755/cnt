"""
Gilson FC-203B 위치 티칭 프로그램

기능:
- 키보드로 헤드 이동 (WASD)
- 금속/반도체/폐기 위치 저장
- 저장된 위치 테스트 이동

저장 파일: cnt_positions.json
→ cnt_auto_collection.py에서 이 파일 사용함
"""

import json
import os
from gilson_fc203b import GilsonFC203B


# ============================================================
#                    [설정] - 여기만 수정하세요!
# ============================================================

GILSON_PORT = 'COM3'          # Gilson 포트 (장치관리자에서 확인)
GILSON_UNIT_ID = 6            # Gilson Unit ID (기본값 6)
POSITIONS_FILE = 'cnt_positions.json'  # 저장 파일명

# ============================================================
#                    [설정 끝] - 아래는 건드리지 마세요
# ============================================================


class PositionTeaching:
    """위치 티칭 클래스"""
    
    def __init__(self, port=GILSON_PORT, unit_id=GILSON_UNIT_ID):
        self.gilson = GilsonFC203B(port=port, unit_id=unit_id)
        
        # 현재 위치
        self.x = 0.0
        self.y = 0.0
        self.step = 10.0  # 이동 단위 (mm)
        
        # 저장된 위치 (3 class)
        self.positions = {
            "금속": {"x": 0.0, "y": 0.0},
            "반도체": {"x": 0.0, "y": 0.0},
            "폐기": {"x": 0.0, "y": 0.0},
        }
        
        self.load_positions()
    
    def load_positions(self):
        """저장된 위치 로드"""
        if os.path.exists(POSITIONS_FILE):
            try:
                with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
                    self.positions = json.load(f)
                print(f"✅ 저장된 위치 로드됨: {POSITIONS_FILE}")
            except:
                print("⚠️ 저장된 위치 없음, 새로 시작")
    
    def save_positions(self):
        """위치 저장"""
        with open(POSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.positions, f, indent=2, ensure_ascii=False)
        print(f"✅ 저장됨: {POSITIONS_FILE}")
    
    def show_positions(self):
        """저장된 위치 출력"""
        print("\n" + "="*45)
        print("  저장된 위치")
        print("="*45)
        for name, pos in self.positions.items():
            marker = "●" if pos['x'] != 0 or pos['y'] != 0 else "○"
            print(f"  {marker} {name:8}: ({pos['x']:6.1f}, {pos['y']:6.1f}) mm")
        print("="*45 + "\n")
    
    def move(self, dx=0, dy=0):
        """상대 이동"""
        self.x = max(0, self.x + dx)
        self.y = max(0, self.y + dy)
        self.gilson.move_to_xy(self.x, self.y)
    
    def goto(self, x, y):
        """절대 이동"""
        self.x = max(0, x)
        self.y = max(0, y)
        self.gilson.move_to_xy(self.x, self.y)
    
    def save_position(self, name):
        """현재 위치를 저장"""
        self.positions[name] = {"x": self.x, "y": self.y}
        self.save_positions()
        print(f"\n  ★ {name} = ({self.x:.1f}, {self.y:.1f}) mm 저장됨!\n")
    
    def goto_saved(self, name):
        """저장된 위치로 이동"""
        if name in self.positions:
            pos = self.positions[name]
            self.goto(pos['x'], pos['y'])
            print(f"  → {name} 위치로 이동")
    
    def connect(self):
        """장비 연결"""
        if self.gilson.connect():
            # 현재 위치 읽기
            x, y = self.gilson.get_position()
            if x is not None:
                self.x = x
            if y is not None:
                self.y = y
            return True
        else:
            print("\n[!] Gilson 연결 실패")
            return False
    
    def disconnect(self):
        """연결 해제"""
        self.gilson.disconnect()
    
    def run(self):
        """티칭 모드 실행"""
        print("\n" + "="*50)
        print("  Gilson FC-203B 위치 티칭")
        print("="*50)
        print(f"""
  [이동]
    W = 앞 (Y+)      A = 왼쪽 (X-)
    S = 뒤 (Y-)      D = 오른쪽 (X+)
    H = 홈 (0, 0)

  [이동 단위]
    1 = 1mm    2 = 5mm    3 = 10mm    4 = 20mm

  [위치 저장] ← 현재 위치를 저장
    M = 금속
    B = 반도체
    T = 폐기

  [확인/테스트]
    L = 저장된 위치 목록
    G = 저장된 위치로 이동 (테스트)

  [종료]
    Q = 종료
""")
        print("-"*50)
        self.show_positions()
        
        while True:
            prompt = f"({self.x:.1f}, {self.y:.1f}) [{self.step:.0f}mm] >> "
            cmd = input(prompt).strip().lower()
            
            if not cmd:
                continue
            
            # 이동
            if cmd == 'w':
                self.move(dy=self.step)
            elif cmd == 's':
                self.move(dy=-self.step)
            elif cmd == 'a':
                self.move(dx=-self.step)
            elif cmd == 'd':
                self.move(dx=self.step)
            elif cmd == 'h':
                self.goto(0, 0)
                print("  → 홈 (0, 0)")
            
            # 이동 단위
            elif cmd == '1':
                self.step = 1.0
                print(f"  이동 단위: {self.step}mm")
            elif cmd == '2':
                self.step = 5.0
                print(f"  이동 단위: {self.step}mm")
            elif cmd == '3':
                self.step = 10.0
                print(f"  이동 단위: {self.step}mm")
            elif cmd == '4':
                self.step = 20.0
                print(f"  이동 단위: {self.step}mm")
            
            # 위치 저장 (3 class)
            elif cmd == 'm':
                self.save_position("금속")
            elif cmd == 'b':
                self.save_position("반도체")
            elif cmd == 't':
                self.save_position("폐기")
            
            # 목록
            elif cmd == 'l':
                self.show_positions()
            
            # 테스트 이동
            elif cmd == 'g':
                print("\n  이동할 위치:")
                print("    1=금속  2=반도체  3=폐기")
                choice = input("  선택 >> ").strip()
                mapping = {'1': '금속', '2': '반도체', '3': '폐기'}
                if choice in mapping:
                    self.goto_saved(mapping[choice])
            
            # 종료
            elif cmd == 'q':
                print("\n티칭 종료")
                break
            
            else:
                print("  ? 알 수 없는 명령")


# ============================================================
#                    메인
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  위치 티칭 프로그램 (3 class)")
    print("  금속 / 반도체 / 폐기")
    print("="*50)
    
    # 포트 설정
    port = input(f"\nGilson 포트 [{GILSON_PORT}]: ").strip()
    if not port:
        port = GILSON_PORT
    
    # 티칭 시작
    teaching = PositionTeaching(port=port)
    
    if not teaching.connect():
        print("연결 실패. 종료합니다.")
        exit(1)
    
    try:
        teaching.run()
    except KeyboardInterrupt:
        print("\n\n중단됨")
    finally:
        teaching.disconnect()
        print("\n최종 저장된 위치:")
        teaching.show_positions()
