"""
젤 흡수 감지 (Line Bend 방식)

감지 방법:
- 투명 용액: Line Bend (패턴 꺾임 정도)
- CNT 용액: 밝기 변화 (검정→흰색)

설치: pip install opencv-python numpy
"""

import cv2
import numpy as np
import time
import json
import os


# ============================================================
#                    [설정] - 여기만 수정하세요!
# ============================================================

CAMERA_INDEX = 1              # 카메라 번호 (USB 카메라)
ROI_FILE = 'roi_settings.json'

# 플리커 제거
ANTI_FLICKER = True
FRAME_AVG_COUNT = 5

# --- 투명 용액 감지용 (Line Bend 기준) ---
LINE_BEND_THRESHOLD = 20      # 이 값 이상 = 용액 있음, 이하 = 흡수 완료

# --- CNT 감지용 (밝기 기준) ---
CNT_THRESHOLD = 87            # 이 값 이상 = CNT 흡수 완료

CHECK_INTERVAL = 0.5          # 체크 간격 (초)

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
    print(f"✅ 카메라 연결됨")
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
    """평균 밝기"""
    return gray.mean()


def get_line_bend(gray):
    """패턴 꺾임 정도 (밝은 픽셀 Y좌표 표준편차)"""
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


def select_roi():
    """ROI 영역 선택"""
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
        
        cv2.imshow("Live View", display)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def calibrate():
    """캘리브레이션"""
    print("\n" + "="*50)
    print("  캘리브레이션")
    print("  [1] = 용액 있음 + 패턴")
    print("  [2] = 용액 없음 + 패턴")
    print("  [Q] = 종료")
    print("="*50)
    
    roi = load_roi()
    if not roi:
        print("❌ ROI 없음! 먼저 1번으로 설정하세요")
        return
    
    cap = init_camera()
    if not cap:
        return
    
    x1, y1, x2, y2 = roi
    
    liquid_bend = None
    no_liquid_bend = None
    
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
        if liquid_bend is not None:
            cv2.putText(display, f"[1] Liquid: {liquid_bend:.1f}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y_pos += 25
        if no_liquid_bend is not None:
            cv2.putText(display, f"[2] No Liquid: {no_liquid_bend:.1f}", (10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        cv2.putText(display, "[1]=Liquid [2]=NoLiquid [Q]=Quit",
                   (10, display.shape[0]-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow("Calibration", display)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('1'):
            liquid_bend = line_bend
            print(f"\n✅ [1] 용액 있음: Line Bend = {liquid_bend:.1f}")
        
        elif key == ord('2'):
            no_liquid_bend = line_bend
            print(f"\n✅ [2] 용액 없음: Line Bend = {no_liquid_bend:.1f}")
            
            if liquid_bend is not None:
                threshold = (liquid_bend + no_liquid_bend) / 2
                print(f"\n" + "="*40)
                print(f"  [추천 설정값]")
                print(f"  LINE_BEND_THRESHOLD = {threshold:.0f}")
                print(f"="*40)
        
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def monitor_transparent():
    """투명 용액 흡수 모니터링"""
    print("\n" + "="*50)
    print("  투명 용액 흡수 모니터링")
    print(f"  Line Bend > {LINE_BEND_THRESHOLD} = 용액 있음")
    print(f"  Line Bend < {LINE_BEND_THRESHOLD} = 흡수 완료!")
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
    absorbed = False
    
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
            if not absorbed:
                absorbed = True
                print(f"\n🎉 투명 용액 흡수 완료! (Line Bend: {line_bend:.1f})")
        else:
            status = "💧 용액 있음"
            color = (0, 255, 255)
            absorbed = False
        
        display = frame.copy()
        cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
        
        cv2.putText(display, f"Line Bend: {line_bend:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(display, status, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(display, f"Threshold: {LINE_BEND_THRESHOLD}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow("Transparent Monitor", display)
        
        if cv2.waitKey(int(CHECK_INTERVAL * 1000)) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def monitor_cnt():
    """CNT 용액 흡수 모니터링"""
    print("\n" + "="*50)
    print("  CNT 용액 흡수 모니터링")
    print(f"  밝기 > {CNT_THRESHOLD} = 흡수 완료!")
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
    absorbed = False
    
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
            if not absorbed:
                absorbed = True
                print(f"\n🎉 CNT 흡수 완료! (밝기: {brightness:.1f})")
        else:
            status = "⚫ CNT 있음"
            color = (0, 0, 255)
            absorbed = False
        
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


def wait_for_transparent(timeout=300):
    """투명 용액 흡수 대기 (자동화용)"""
    roi = load_roi()
    if not roi:
        print("❌ ROI 없음!")
        return False
    
    cap = init_camera()
    if not cap:
        return False
    
    x1, y1, x2, y2 = roi
    
    print("⏳ 투명 용액 흡수 대기 중...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ret, frame = read_frame(cap)
        if not ret:
            continue
        
        roi_frame = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        line_bend = get_line_bend(gray)
        
        elapsed = time.time() - start_time
        print(f"\r   경과: {elapsed:.0f}초 | Line Bend: {line_bend:.1f}    ", end='', flush=True)
        
        if line_bend < LINE_BEND_THRESHOLD:
            print(f"\n✅ 투명 용액 흡수 완료! ({elapsed:.0f}초)")
            cap.release()
            return True
        
        time.sleep(CHECK_INTERVAL)
    
    print(f"\n⚠️ 타임아웃 ({timeout}초)")
    cap.release()
    return False


def wait_for_cnt(timeout=300):
    """CNT 흡수 대기 (자동화용)"""
    roi = load_roi()
    if not roi:
        print("❌ ROI 없음!")
        return False
    
    cap = init_camera()
    if not cap:
        return False
    
    x1, y1, x2, y2 = roi
    
    print("⏳ CNT 흡수 대기 중...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ret, frame = read_frame(cap)
        if not ret:
            continue
        
        roi_frame = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        brightness = get_brightness(gray)
        
        elapsed = time.time() - start_time
        print(f"\r   경과: {elapsed:.0f}초 | 밝기: {brightness:.1f}    ", end='', flush=True)
        
        if brightness > CNT_THRESHOLD:
            print(f"\n✅ CNT 흡수 완료! ({elapsed:.0f}초)")
            cap.release()
            return True
        
        time.sleep(CHECK_INTERVAL)
    
    print(f"\n⚠️ 타임아웃 ({timeout}초)")
    cap.release()
    return False


# ============================================================
#                    메인 메뉴
# ============================================================

def main():
    while True:
        print("\n" + "="*50)
        print("  젤 흡수 감지 (Line Bend)")
        print("  투명 = 패턴 꺾임 | CNT = 밝기")
        print("="*50)
        
        roi = load_roi()
        print(f"  ROI: {roi if roi else '❌ 없음'}")
        
        print(f"""
  [설정]
    1. ROI 설정
    2. 실시간 영상
    3. 캘리브레이션

  [모니터링]
    4. 투명 용액 모니터링
    5. CNT 모니터링

  [자동화 테스트]
    6. 투명 용액 흡수 대기
    7. CNT 흡수 대기

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
            wait_for_transparent(timeout=120)
        elif choice == '7':
            wait_for_cnt(timeout=120)
        elif choice == 'q':
            print("종료")
            break


if __name__ == "__main__":
    main()
