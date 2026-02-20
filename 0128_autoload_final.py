"""
JASCO UV-Vis 자동 측정 스크립트 (하이브리드 버전)

기능:
- Cancel 버튼 색깔 감지 (회색/빨간색)
- Sample 버튼 자동 클릭 (마우스 안 움직임! - invoke 사용)
- CSV 파일 자동 복사
"""

#######################################################################
#                                                                     #
#                    ★★★ 설정 영역 ★★★                              #
#                    (여기만 수정하세요!)                              #
#                                                                     #
#######################################################################

# ----------------------------------------------------------------------
# CSV 파일 설정
# ----------------------------------------------------------------------

# CSV 파일이 복사될 최종 폴더 (원하는 경로로 변경)
OUTPUT_DIR = r"C:\Users\Nagroup\Desktop\UV_test_0128"

# Spectra Manager가 CSV를 저장하는 폴더 (Spectra Manager 저장 경로)
WATCH_DIR = r"C:\Users\Nagroup\Documents"  # ← 실제 경로로 변경!

# ----------------------------------------------------------------------
# 이미지 인식 설정
# ----------------------------------------------------------------------

# 이미지 매칭 신뢰도 (0.0 ~ 1.0, 낮을수록 관대함)
CONFIDENCE = 0.7

# ----------------------------------------------------------------------
# 측정 간격 설정
# ----------------------------------------------------------------------

# 상태 체크 간격 (초)
CHECK_INTERVAL = 2.0

# Sample 클릭 후 쿨다운 시간 (초) - 이 시간 동안 버튼을 누르지 않음
COOLDOWN = 60.0

# ----------------------------------------------------------------------
# Spectra Manager 창 설정
# ----------------------------------------------------------------------

# 창 제목 (일부만 입력해도 됨)
WINDOW_TITLE = "Spectra Measurement"

# 클릭할 버튼 이름
SAMPLE_BUTTON = "Sample"

#######################################################################
#                                                                     #
#                    ★★★ 코드 영역 ★★★                              #
#                    (아래는 건드리지 마세요!)                          #
#                                                                     #
#######################################################################

import sys
import time
import shutil
import threading
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("pyautogui 설치 필요!")
    print("pip install pyautogui opencv-python")
    sys.exit(1)

try:
    from pywinauto import Application
except ImportError:
    print("pywinauto 설치 필요!")
    print("pip install pywinauto")
    sys.exit(1)

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("watchdog 설치 필요!")
    print("pip install watchdog")
    sys.exit(1)

# PyAutoGUI 설정
pyautogui.FAILSAFE = True

# UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except:
    pass

# 스크립트 폴더
SCRIPT_DIR = Path(__file__).parent.absolute()


class CSVHandler(FileSystemEventHandler):
    """CSV 파일 감지 및 자동 복사"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seen = set()

    def on_created(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() != '.csv':
            return

        if path in self.seen:
            return

        time.sleep(1.5)  # 파일 쓰기 완료 대기
        self.copy_file(path)

    def copy_file(self, path: Path):
        try:
            self.seen.add(path)
            dest = self.output_dir / path.name

            # 중복 처리
            counter = 1
            while dest.exists():
                dest = self.output_dir / f"{path.stem}_{counter}{path.suffix}"
                counter += 1

            shutil.copy2(str(path), str(dest))
            print(f"\n[CSV] ✅ 복사 완료: {dest.name}")
        except Exception as e:
            print(f"\n[CSV] ❌ 복사 실패: {e}")


def find_image(image_name: str) -> bool:
    """이미지가 화면에 있는지 확인"""
    image_path = SCRIPT_DIR / image_name

    if not image_path.exists():
        return False

    try:
        location = pyautogui.locateOnScreen(str(image_path), confidence=CONFIDENCE)
        return location is not None
    except:
        return False


def find_window():
    """Spectra Measurement 창 찾기"""
    try:
        app = Application(backend="uia").connect(title_re=f".*{WINDOW_TITLE}.*")
        window = app.window(title_re=f".*{WINDOW_TITLE}.*")
        return window
    except:
        return None


def click_sample(window):
    """Sample 버튼 클릭 (마우스 안 움직임! - invoke 사용)"""
    try:
        toolbar = window.child_window(title="Measure", control_type="ToolBar")
        button = toolbar.child_window(title=SAMPLE_BUTTON, control_type="Button")

        if button.exists():
            # invoke()는 UIA Invoke 패턴을 사용하므로 마우스 커서가 움직이지 않음
            try:
                button.invoke()
            except Exception:
                # invoke 패턴이 지원되지 않는 경우 fallback
                from pywinauto.keyboard import send_keys
                button.set_focus()
                send_keys('{ENTER}')
            return True
    except Exception as e:
        print(f"[오류] {e}")
    return False


def main():
    print("=" * 60)
    print("JASCO UV-Vis 자동 측정 (하이브리드)")
    print("=" * 60)
    print("✅ 마우스 안 움직임! (invoke 방식)")
    print("✅ CSV 자동 복사!")
    print("=" * 60)
    print(f"CSV 저장 경로: {OUTPUT_DIR}")
    print(f"CSV 감시 경로: {WATCH_DIR}")
    print(f"이미지 폴더: {SCRIPT_DIR}")
    print("=" * 60)
    print("종료: Ctrl+C")
    print("=" * 60)

    # 이미지 파일 확인
    print("\n이미지 파일:")
    for img in ["jascostop.png", "jascostart.png"]:
        path = SCRIPT_DIR / img
        status = "✅" if path.exists() else "❌"
        print(f"  {status} {img}")

    # 창 찾기
    print("\nSpectra Measurement 창 찾는 중...")
    window = find_window()

    if not window:
        print("❌ 창을 찾을 수 없습니다!")
        return

    print(f"✅ 창 발견: {window.window_text()}")

    # CSV 감시 시작
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    watch_dir = Path(WATCH_DIR)
    observer = None

    if watch_dir.exists():
        handler = CSVHandler(output_dir)
        observer = Observer()
        observer.schedule(handler, str(watch_dir), recursive=False)
        observer.start()
        print(f"\n[CSV] 👀 감시 시작: {watch_dir}")
    else:
        print(f"\n[CSV] ⚠️ 감시 폴더 없음: {watch_dir}")
        print("     CSV 자동 복사 기능이 비활성화됩니다.")

    print("\n5초 후 시작...")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    print("\n🚀 자동 측정 시작!\n")

    count = 0

    try:
        while True:
            # 1. 회색 Cancel (jascostop) 감지 → 측정 완료 → Sample 클릭
            if find_image("jascostop.png"):
                print("[상태] ✅ 측정 완료! (회색 Cancel 감지)")

                count += 1
                print(f"[측정 #{count}] Sample 버튼 클릭 중...")

                if click_sample(window):
                    print(f"[측정 #{count}] ✅ 새 측정 시작!")
                    print(f"[대기] ⏸️  {int(COOLDOWN)}초 쿨다운 (이 동안 다른 작업 가능)\n")
                    time.sleep(COOLDOWN)
                else:
                    print(f"[측정 #{count}] ❌ 클릭 실패\n")
                    time.sleep(CHECK_INTERVAL)

                continue

            # 2. 빨간색 Cancel (jascostart) 감지 → 측정 중
            if find_image("jascostart.png"):
                print("[상태] ⏳ 측정 진행 중...")
                time.sleep(CHECK_INTERVAL)
                continue

            # 둘 다 안 보이면 대기
            print("[상태] 👀 화면 감시 중...")
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(f"\n\n⛔ 종료! 총 {count}회 측정")

    finally:
        if observer:
            observer.stop()
            observer.join()
            print("[CSV] 감시 종료")


if __name__ == "__main__":
    main()
