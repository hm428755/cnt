"""
젤 흡수 감지 - 통합 자동화

흐름:
1. 투명 용액 흡수 대기 (Line Bend)
2. CNT 넣으세요 → 자동 감지
3. CNT 흡수 대기 (밝기)
4. 투명 넣으세요 → 자동 감지
5. 반복...

설치: pip install opencv-python numpy
"""

import cv2
import numpy as np
import time
import json
import os
import winsound  # 윈도우 알림음


# ============================================================
#                    [설정] - 여기만 수정하세요!
# ============================================================

CAMERA_INDEX = 1              # 카메라 번호

# 플리커 제거
ANTI_FLICKER = True
FRAME_AVG_COUNT = 5

# --- 투명 용액 감지 (Line Bend) ---
LINE_BEND_THRESHOLD = 20      # 이하 = 흡수 완료

# --- CNT 감지 (밝기) ---
CNT_THRESHOLD = 87            # 이상 = 흡수 완료

# --- 파일 ---
ROI_FILE = 'roi_settings.json'

# --- 타이밍 ---
CHECK_INTERVAL = 0.5          # 체크 간격 (초)
STABLE_COUNT = 3              # 연속 N번 감지되면 확정

# ============================================================
#                    [설정 끝]
# ============================================================


drawing = False
start_point = None
end_point = None
roi_rect = None


def mouse_callback(event, x, y, flags, param):
    global drawing, start_point, end_point, roi_rect
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_point = (x, y)
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        end_point = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        end_point = (x, y)
        x1, y1 = min(start_point[0], end_point[0]), min(start_point[1], end_point[1])
        x2, y2 = max(start_point[0], end_point[0]), max(start_point[1], end_point[1])
        roi_rect = (x1, y1, x2, y2)


def save_roi(roi):
    with open(ROI_FILE, 'w') as f:
        json.dump({'roi': roi}, f)


def load_roi():
    if os.path.exists(ROI_FILE):
        with open(ROI_FILE, 'r') as f:
            return tuple(json.load(f)['roi'])
    return None


def init_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("❌ 카메라 연결 실패!")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


def read_frame(cap):
    if not ANTI_FLICKER:
        ret, frame = cap.read()
        return ret, frame
    
    frames = []
    for _ in range(FRAME_AVG_COUNT):
        ret, frame = cap.read()
        if ret:
            frames.append(frame.astype(np.float32))
    
    if not frames:
        return False, None
    
    return True, np.mean(frames, axis=0).astype(np.uint8)


def get_brightness(gray):
    return gray.mean()


def get_line_bend(gray):
    threshold = gray.mean() + 30
    bright_mask = gray > threshold
    
    y_coords, x_coords = np.where(bright_mask)
    
    if len(y_coords) < 10:
        return 0
    
    x_unique = np.unique(x_coords)
    y_means = []
    
    for x in x_unique:
        y_at_x = y_coords[x_coords == x]
        if len(y_at_x) > 0:
            y_means.append(y_at_x.mean())
    
    if len(y_means) < 5:
        return 0
    
    return np.std(y_means)


def beep_alert():
    """알림음"""
    try:
        winsound.Beep(1000, 500)  # 1000Hz, 0.5초
    except:
        print("\a")  # 기본 비프음


def select_roi():
    """ROI 설정"""
    global roi_rect
    print("\n" + "="*50)
    print("  ROI 설정")
    print("  마우스로 패턴 보이는 영역 선택!")
    print("  Enter=확정 | R=리셋 | Q=취소")
    print("="*50)
    
    cap = init_camera()
    if not cap:
        return
    
    cv2.namedWindow("Select ROI")
    cv2.setMouseCallback("Select ROI", mouse_callback)
    roi_rect = None
    
    while True:
        ret, frame = read_frame(cap)
        if not ret:
            break
        
        display = frame.copy()
        
        if drawing and start_point and end_point:
            cv2.rectangle(display, start_point, end_point, (0, 255, 0), 2)
        
        if roi_rect:
            x1, y1, x2, y2 = roi_rect
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            roi_frame = frame[y1:y2, x1:x2]
            gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
            line_bend = get_line_bend(gray)
            brightness = get_brightness(gray)
            
            cv2.putText(display, f"Line Bend: {line_bend:.1f}", (x1, y1-35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(display, f"Brightness: {brightness:.1f}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        cv2.imshow("Select ROI", display)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 13 and roi_rect:
            save_roi(roi_rect)
            print(f"✅ ROI 저장됨: {roi_rect}")
            break
        elif key == ord('r'):
            roi_rect = None
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def live_view():
    """실시간 영상"""
    print("\n" + "="*50)
    print("  실시간 영상")
    print("  Q=종료")
    print("="*50)
    
    cap = init_camera()
    if not cap:
        return
    
    roi = load_roi()
    
    while True:
        ret, frame = read_frame(cap)
        if not ret:
            break
        
        display = frame.copy()
        
        if roi:
            x1, y1, x2, y2 = roi
            roi_frame = frame[y1:y2, x1:x2]
            gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
            
            line_bend = get_line_bend(gray)
            brightness = get_brightness(gray)
            
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            cv2.putText(display, f"Line Bend: {line_bend:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(display, f"Brightness: {brightness:.1f}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 상태 표시
            if line_bend > LINE_BEND_THRESHOLD:
                status = "투명 용액 있음"
                color = (0, 255, 255)
            elif brightness < CNT_THRESHOLD:
                status = "CNT 있음"
                color = (0, 0, 255)
            else:
                status = "비어있음 (젤만)"
                color = (0, 255, 0)
            
            cv2.putText(display, f"Status: {status}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        cv2.imshow("Live View", display)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def calibrate():
    """캘리브레이션"""
    print("\n" + "="*50)
    print("  캘리브레이션")
    print("  [1] = 용액 있음 (투명)")
    print("  [2] = 용액 없음 (빈 상태)")
    print("  [3] = CNT 있음")
    print("  [4] = CNT 흡수 후 (젤만)")
    print("  [Q] = 종료")
    print("="*50)
    
    roi = load_roi()
    if not roi:
        print("❌ ROI 없음!")
        return
    
    cap = init_camera()
    if not cap:
        return
    
    x1, y1, x2, y2 = roi
    
    vals = {}
    
    while True:
        ret, frame = read_frame(cap)
        if not ret:
            break
        
        roi_frame = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        
        line_bend = get_line_bend(gray)
        brightness = get_brightness(gray)
        
        display = frame.copy()
        cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        cv2.putText(display, f"Line Bend: {line_bend:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(display, f"Brightness: {brightness:.1f}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        y_pos = 100
        for key, val in vals.items():
            cv2.putText(display, f"[{key}] {val}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_pos += 20
        
        cv2.imshow("Calibration", display)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('1'):
            vals['1'] = f"투명 있음: Bend={line_bend:.1f}"
            print(f"✅ [1] 투명 있음: Line Bend = {line_bend:.1f}")
        elif key == ord('2'):
            vals['2'] = f"빈 상태: Bend={line_bend:.1f}"
            print(f"✅ [2] 빈 상태: Line Bend = {line_bend:.1f}")
        elif key == ord('3'):
            vals['3'] = f"CNT 있음: Bright={brightness:.1f}"
            print(f"✅ [3] CNT 있음: Brightness = {brightness:.1f}")
        elif key == ord('4'):
            vals['4'] = f"CNT 후: Bright={brightness:.1f}"
            print(f"✅ [4] CNT 후: Brightness = {brightness:.1f}")
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "="*40)
    print("  코드 상단 [설정]에 입력하세요!")
    print("="*40)


def full_cycle_test():
    """전체 사이클 테스트"""
    print("\n" + "="*50)
    print("  🔄 전체 사이클 테스트")
    print("="*50)
    print("""
  [흐름]
    1. "투명 넣으세요" → 넣음 감지 → "확인!"
    2. 투명 흡수 대기 → "흡수 완료!"
    3. "CNT 넣으세요" → 넣음 감지 → "확인!"
    4. CNT 흡수 대기 → "흡수 완료!"
    5. 반복...

  [Q] = 종료 (영상 창에서)
""")
    
    roi = load_roi()
    if not roi:
        print("❌ ROI 없음!")
        return
    
    cap = init_camera()
    if not cap:
        return
    
    x1, y1, x2, y2 = roi
    
    # 상태:
    # 'wait_transparent_add' = 투명 넣기 대기
    # 'wait_transparent_absorb' = 투명 흡수 대기
    # 'wait_cnt_add' = CNT 넣기 대기
    # 'wait_cnt_absorb' = CNT 흡수 대기
    
    state = 'wait_transparent_add'
    stable_counter = 0
    cycle_count = 0
    
    print("\n🚀 시작! 투명 용액을 넣으세요...")
    
    while True:
        ret, frame = read_frame(cap)
        if not ret:
            break
        
        roi_frame = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        
        line_bend = get_line_bend(gray)
        brightness = get_brightness(gray)
        
        display = frame.copy()
        
        # ============================================
        # 상태 1: 투명 용액 넣기 대기
        # ============================================
        if state == 'wait_transparent_add':
            # Line Bend 증가 = 투명 용액 넣음
            if line_bend > LINE_BEND_THRESHOLD:
                stable_counter += 1
            else:
                stable_counter = 0
            
            if stable_counter >= STABLE_COUNT:
                beep_alert()
                print(f"\n✅ 투명 용액 확인!")
                print(f"⏳ 흡수 대기 중...")
                state = 'wait_transparent_absorb'
                stable_counter = 0
            
            status = f"[투명 넣기 대기] Line Bend: {line_bend:.1f}"
            color = (255, 255, 0)  # 시안
            instruction = ">>> 투명 용액을 넣으세요! <<<"
        
        # ============================================
        # 상태 2: 투명 용액 흡수 대기
        # ============================================
        elif state == 'wait_transparent_absorb':
            # Line Bend 감소 = 흡수 완료
            if line_bend < LINE_BEND_THRESHOLD:
                stable_counter += 1
            else:
                stable_counter = 0
            
            if stable_counter >= STABLE_COUNT:
                beep_alert()
                print(f"\n✅ 투명 용액 흡수 완료!")
                print(f"🔔 CNT를 넣으세요!")
                state = 'wait_cnt_add'
                stable_counter = 0
                cycle_count += 1
            
            status = f"[투명 흡수 중] Line Bend: {line_bend:.1f}"
            color = (0, 255, 255)  # 노랑
            instruction = "투명 용액 흡수 중..."
        
        # ============================================
        # 상태 3: CNT 넣기 대기
        # ============================================
        elif state == 'wait_cnt_add':
            # 밝기 감소 = CNT 넣음
            if brightness < CNT_THRESHOLD:
                stable_counter += 1
            else:
                stable_counter = 0
            
            if stable_counter >= STABLE_COUNT:
                beep_alert()
                print(f"\n✅ CNT 확인!")
                print(f"⏳ 흡수 대기 중...")
                state = 'wait_cnt_absorb'
                stable_counter = 0
            
            status = f"[CNT 넣기 대기] Brightness: {brightness:.1f}"
            color = (0, 165, 255)  # 주황
            instruction = ">>> CNT를 넣으세요! <<<"
        
        # ============================================
        # 상태 4: CNT 흡수 대기
        # ============================================
        elif state == 'wait_cnt_absorb':
            # 밝기 증가 = 흡수 완료
            if brightness > CNT_THRESHOLD:
                stable_counter += 1
            else:
                stable_counter = 0
            
            if stable_counter >= STABLE_COUNT:
                beep_alert()
                print(f"\n✅ CNT 흡수 완료!")
                print(f"🔔 투명 용액을 넣으세요!")
                state = 'wait_transparent_add'
                stable_counter = 0
            
            status = f"[CNT 흡수 중] Brightness: {brightness:.1f}"
            color = (0, 0, 255)  # 빨강
            instruction = "CNT 흡수 중..."
        
        # 화면 표시
        cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
        
        cv2.putText(display, status, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(display, instruction, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display, f"Cycle: {cycle_count}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(display, f"Stable: {stable_counter}/{STABLE_COUNT}", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # 값 표시
        cv2.putText(display, f"Line Bend: {line_bend:.1f}", (10, display.shape[0]-50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(display, f"Brightness: {brightness:.1f}", (10, display.shape[0]-30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(display, "Q=Quit", (10, display.shape[0]-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        cv2.imshow("Full Cycle Test", display)
        
        if cv2.waitKey(int(CHECK_INTERVAL * 1000)) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\n종료! 총 {cycle_count} 사이클 완료")


def monitor_transparent():
    """투명 용액만 모니터링"""
    print("\n" + "="*50)
    print("  투명 용액 모니터링")
    print("  Q=종료")
    print("="*50)
    
    roi = load_roi()
    if not roi:
        print("❌ ROI 없음!")
        return
    
    cap = init_camera()
    if not cap:
        return
    
    x1, y1, x2, y2 = roi
    
    while True:
        ret, frame = read_frame(cap)
        if not ret:
            break
        
        roi_frame = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        line_bend = get_line_bend(gray)
        
        if line_bend < LINE_BEND_THRESHOLD:
            status = "✅ 흡수 완료!"
            color = (0, 255, 0)
        else:
            status = "💧 용액 있음"
            color = (0, 255, 255)
        
        display = frame.copy()
        cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
        cv2.putText(display, f"Line Bend: {line_bend:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(display, status, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        cv2.imshow("Transparent Monitor", display)
        
        if cv2.waitKey(int(CHECK_INTERVAL * 1000)) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def monitor_cnt():
    """CNT만 모니터링"""
    print("\n" + "="*50)
    print("  CNT 모니터링")
    print("  Q=종료")
    print("="*50)
    
    roi = load_roi()
    if not roi:
        print("❌ ROI 없음!")
        return
    
    cap = init_camera()
    if not cap:
        return
    
    x1, y1, x2, y2 = roi
    
    while True:
        ret, frame = read_frame(cap)
        if not ret:
            break
        
        roi_frame = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        brightness = get_brightness(gray)
        
        if brightness > CNT_THRESHOLD:
            status = "✅ CNT 흡수 완료!"
            color = (0, 255, 0)
        else:
            status = "⚫ CNT 있음"
            color = (0, 0, 255)
        
        display = frame.copy()
        cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
        cv2.putText(display, f"Brightness: {brightness:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(display, status, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        cv2.imshow("CNT Monitor", display)
        
        if cv2.waitKey(int(CHECK_INTERVAL * 1000)) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


# ============================================================
#                    자동화용 함수
# ============================================================

def wait_for_transparent_absorbed(timeout=300):
    """투명 용액 흡수 완료 대기 (자동화용)"""
    roi = load_roi()
    if not roi:
        return False
    
    cap = init_camera()
    if not cap:
        return False
    
    x1, y1, x2, y2 = roi
    stable_counter = 0
    
    print("⏳ 투명 용액 흡수 대기...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ret, frame = read_frame(cap)
        if not ret:
            continue
        
        roi_frame = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        line_bend = get_line_bend(gray)
        
        if line_bend < LINE_BEND_THRESHOLD:
            stable_counter += 1
        else:
            stable_counter = 0
        
        elapsed = time.time() - start_time
        print(f"\r   경과: {elapsed:.0f}초 | Line Bend: {line_bend:.1f} | Stable: {stable_counter}/{STABLE_COUNT}    ", 
              end='', flush=True)
        
        if stable_counter >= STABLE_COUNT:
            print(f"\n✅ 투명 용액 흡수 완료!")
            cap.release()
            return True
        
        time.sleep(CHECK_INTERVAL)
    
    print(f"\n⚠️ 타임아웃")
    cap.release()
    return False


def wait_for_cnt_absorbed(timeout=300):
    """CNT 흡수 완료 대기 (자동화용)"""
    roi = load_roi()
    if not roi:
        return False
    
    cap = init_camera()
    if not cap:
        return False
    
    x1, y1, x2, y2 = roi
    stable_counter = 0
    
    print("⏳ CNT 흡수 대기...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ret, frame = read_frame(cap)
        if not ret:
            continue
        
        roi_frame = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        brightness = get_brightness(gray)
        
        if brightness > CNT_THRESHOLD:
            stable_counter += 1
        else:
            stable_counter = 0
        
        elapsed = time.time() - start_time
        print(f"\r   경과: {elapsed:.0f}초 | Brightness: {brightness:.1f} | Stable: {stable_counter}/{STABLE_COUNT}    ", 
              end='', flush=True)
        
        if stable_counter >= STABLE_COUNT:
            print(f"\n✅ CNT 흡수 완료!")
            cap.release()
            return True
        
        time.sleep(CHECK_INTERVAL)
    
    print(f"\n⚠️ 타임아웃")
    cap.release()
    return False


# ============================================================
#                    메인 메뉴
# ============================================================

def main():
    while True:
        print("\n" + "="*50)
        print("  🧪 젤 흡수 감지 - 통합")
        print("="*50)
        
        roi = load_roi()
        print(f"  ROI: {roi if roi else '❌ 없음'}")
        print(f"  LINE_BEND_THRESHOLD: {LINE_BEND_THRESHOLD}")
        print(f"  CNT_THRESHOLD: {CNT_THRESHOLD}")
        
        print("""
  [설정]
    1. ROI 설정
    2. 실시간 영상
    3. 캘리브레이션

  [개별 테스트]
    4. 투명 용액 모니터링
    5. CNT 모니터링

  [통합 테스트] ⭐
    6. 전체 사이클 테스트

    q. 종료
""")
        
        choice = input("선택 >> ").strip().lower()
        
        if choice == '1':
            select_roi()
        elif choice == '2':
            live_view()
        elif choice == '3':
            calibrate()
        elif choice == '4':
            monitor_transparent()
        elif choice == '5':
            monitor_cnt()
        elif choice == '6':
            full_cycle_test()
        elif choice == 'q':
            print("종료")
            break


if __name__ == "__main__":
    main()
