"""
Gilson FC-203B Fraction Collector GSIOC 통신 라이브러리

통신 방식: RS-232 → 508 Interface Module → GSIOC → FC-203B
프로토콜: GSIOC (Gilson Serial Input/Output Channel)

사용법:
    gilson = GilsonFC203B(port='COM3', unit_id=6)
    gilson.connect()
    gilson.move_to_xy(100.0, 50.0)  # X=100mm, Y=50mm로 이동
    gilson.disconnect()
"""

import serial
import time


class GilsonFC203B:
    """Gilson FC-203B Fraction Collector 제어 클래스"""
    
    # GSIOC 프로토콜 상수
    DISCONNECT_ALL = 0xFF      # 모든 slave 연결 해제
    ACK = 0x06                 # Acknowledge
    LF = 0x0A                  # Line Feed (buffered command 시작)
    CR = 0x0D                  # Carriage Return (buffered command 끝)
    
    def __init__(self, port='COM3', unit_id=6, baudrate=19200):
        """
        초기화
        
        Args:
            port: COM 포트 (Windows: 'COM3', Linux: '/dev/ttyUSB0')
            unit_id: GSIOC Unit ID (기본값 6, 0-63 범위)
            baudrate: 통신 속도 (기본값 19200)
        """
        self.port = port
        self.unit_id = unit_id
        self.baudrate = baudrate
        self.ser = None
        self.connected = False
        self.debug = False  # True면 통신 내용 출력
    
    # ========================================
    # 연결 관리
    # ========================================
    
    def connect(self):
        """
        장비 연결
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            # 시리얼 포트 열기
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )
            
            time.sleep(0.1)
            
            # GSIOC slave 연결
            if self._connect_slave():
                self.connected = True
                print(f"✅ Gilson FC-203B 연결 성공 (Port: {self.port}, ID: {self.unit_id})")
                
                # 버전 확인
                version = self.get_version()
                if version:
                    print(f"   버전: {version}")
                
                return True
            else:
                print(f"❌ Gilson FC-203B 응답 없음")
                self.ser.close()
                return False
                
        except serial.SerialException as e:
            print(f"❌ 포트 열기 실패: {e}")
            return False
    
    def disconnect(self):
        """연결 해제"""
        if self.ser and self.ser.is_open:
            self._disconnect_slave()
            self.ser.close()
            self.connected = False
            print("🔌 Gilson FC-203B 연결 해제")
    
    def _connect_slave(self):
        """
        GSIOC slave 연결 시퀀스
        
        1. 0xFF 전송 (모든 slave 해제)
        2. 20ms 대기
        3. Unit ID + 128 전송
        4. echo 확인
        """
        # 버퍼 비우기
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        # 1. 모든 slave 연결 해제
        self.ser.write(bytes([self.DISCONNECT_ALL]))
        time.sleep(0.02)  # 20ms 대기
        
        # 2. 원하는 slave 연결 (Unit ID + 128)
        binary_name = self.unit_id + 128
        self.ser.write(bytes([binary_name]))
        
        # 3. echo 확인 (20ms 이내 응답)
        time.sleep(0.02)
        if self.ser.in_waiting > 0:
            response = self.ser.read(1)
            if response and response[0] == binary_name:
                return True
        
        return False
    
    def _disconnect_slave(self):
        """GSIOC slave 연결 해제"""
        if self.ser and self.ser.is_open:
            self.ser.write(bytes([self.DISCONNECT_ALL]))
            time.sleep(0.02)
    
    # ========================================
    # GSIOC 명령 전송
    # ========================================
    
    def _send_immediate(self, command_char):
        """
        Immediate Command 전송 (상태 요청)
        
        Args:
            command_char: 단일 문자 명령
            
        Returns:
            str: 응답 문자열 (없으면 None)
        """
        if not self.connected:
            return None
        
        # slave 재연결
        self._connect_slave()
        
        # 명령 전송
        self.ser.write(command_char.encode())
        
        if self.debug:
            print(f"[TX] Immediate: {command_char}")
        
        # 응답 수신
        response = []
        timeout = time.time() + 1.0
        
        while time.time() < timeout:
            if self.ser.in_waiting > 0:
                byte = self.ser.read(1)[0]
                
                # MSB가 1이면 마지막 문자
                if byte >= 128:
                    response.append(chr(byte - 128))
                    break
                else:
                    response.append(chr(byte))
                    # ACK 전송
                    self.ser.write(bytes([self.ACK]))
            else:
                time.sleep(0.01)
        
        result = ''.join(response) if response else None
        
        if self.debug:
            print(f"[RX] {result}")
        
        return result
    
    def _send_buffered(self, command_str):
        """
        Buffered Command 전송 (동작 명령)
        
        Args:
            command_str: 명령 문자열 (예: "X1000", "Y0500")
            
        Returns:
            bool: 성공 여부
        """
        if not self.connected:
            return False
        
        # slave 재연결
        self._connect_slave()
        
        if self.debug:
            print(f"[TX] Buffered: {command_str}")
        
        # 1. Line Feed 전송
        self.ser.write(bytes([self.LF]))
        time.sleep(0.02)
        
        # 응답 확인 (LF echo 또는 # = busy)
        if self.ser.in_waiting > 0:
            response = self.ser.read(1)[0]
            if response == ord('#'):
                # busy - 잠시 대기 후 재시도
                time.sleep(0.1)
                self.ser.write(bytes([self.LF]))
                time.sleep(0.02)
        
        # 2. 명령 문자열 전송 (문자별로 echo 확인)
        for char in command_str:
            self.ser.write(char.encode())
            time.sleep(0.01)
            
            # echo 확인
            if self.ser.in_waiting > 0:
                self.ser.read(1)
        
        # 3. Carriage Return 전송
        self.ser.write(bytes([self.CR]))
        time.sleep(0.05)
        
        return True
    
    # ========================================
    # 위치 제어
    # ========================================
    
    def move_to_xy(self, x_mm, y_mm):
        """
        X, Y 좌표로 이동
        
        Args:
            x_mm: X 위치 (mm)
            y_mm: Y 위치 (mm)
        """
        # mm → 0.1mm 단위 변환
        x_units = int(x_mm * 10)
        y_units = int(y_mm * 10)
        
        # 범위 체크 (0-9999)
        x_units = max(0, min(9999, x_units))
        y_units = max(0, min(9999, y_units))
        
        # X 이동
        x_cmd = f"X{x_units:04d}"
        self._send_buffered(x_cmd)
        
        time.sleep(0.1)
        
        # Y 이동
        y_cmd = f"Y{y_units:04d}"
        self._send_buffered(y_cmd)
        
        if self.debug:
            print(f"→ 이동: X={x_mm}mm, Y={y_mm}mm")
        
        # 이동 완료 대기
        self._wait_motion_complete()
    
    def move_to_tube(self, tube_number):
        """
        튜브 번호로 이동
        
        Args:
            tube_number: 튜브 번호 (1-999)
        """
        tube_number = max(1, min(999, tube_number))
        cmd = f"T{tube_number:03d}"
        self._send_buffered(cmd)
        self._wait_motion_complete()
    
    def home(self):
        """홈 위치 (0, 0)으로 이동"""
        self.move_to_xy(0, 0)
    
    def _wait_motion_complete(self, timeout=10.0):
        """
        모터 이동 완료 대기
        
        X/Y 상태가 'S' (stationary)가 될 때까지 대기
        """
        start = time.time()
        
        while time.time() - start < timeout:
            x_pos = self._send_immediate('X')
            y_pos = self._send_immediate('Y')
            
            if x_pos and y_pos:
                # 첫 문자가 'S'면 정지 상태
                x_stationary = x_pos[0] == 'S' if x_pos else False
                y_stationary = y_pos[0] == 'S' if y_pos else False
                
                if x_stationary and y_stationary:
                    return True
            
            time.sleep(0.1)
        
        return False
    
    # ========================================
    # 위치 읽기
    # ========================================
    
    def get_position(self):
        """
        현재 X, Y 위치 읽기
        
        Returns:
            tuple: (x_mm, y_mm) 또는 (None, None)
        """
        x_pos = self._send_immediate('X')
        y_pos = self._send_immediate('Y')
        
        x_mm = None
        y_mm = None
        
        if x_pos and len(x_pos) >= 5:
            # 형식: "Xaxxxx" (a=M/S, xxxx=0.1mm 단위)
            try:
                x_mm = int(x_pos[2:]) / 10.0
            except:
                pass
        
        if y_pos and len(y_pos) >= 5:
            try:
                y_mm = int(y_pos[2:]) / 10.0
            except:
                pass
        
        return (x_mm, y_mm)
    
    def get_tube(self):
        """
        현재 튜브 번호 읽기
        
        Returns:
            int: 튜브 번호 (0 = 정의 안 됨)
        """
        response = self._send_immediate('T')
        if response:
            try:
                return int(response)
            except:
                pass
        return 0
    
    # ========================================
    # 기타 명령
    # ========================================
    
    def get_version(self):
        """
        펌웨어 버전 읽기
        
        Returns:
            str: 버전 문자열 (예: "203Bv2.0")
        """
        return self._send_immediate('%')
    
    def reset(self):
        """장비 리셋 (전원 재시작과 동일)"""
        self._send_immediate('$')
        time.sleep(2.0)  # 리셋 대기
        self._connect_slave()
    
    def beep(self, duration_sec=0.5):
        """
        비프음
        
        Args:
            duration_sec: 비프 시간 (초, 0.1초 단위)
        """
        # duration은 0.1초 단위, 0-100
        d = int(duration_sec * 10)
        d = max(0, min(100, d))
        cmd = f"G{d:03d}"
        self._send_buffered(cmd)
    
    def set_divert(self, enable):
        """
        Diverter valve 제어
        
        Args:
            enable: True = divert, False = no divert
        """
        cmd = "V1" if enable else "V0"
        self._send_buffered(cmd)
    
    def relax_motors(self):
        """모터 릴랙스 (수동 이동 가능하게)"""
        self._send_buffered("Mxy")


# ============================================================
# 테스트 코드
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Gilson FC-203B 연결 테스트")
    print("="*50)
    
    # 포트 설정
    port = input("\nCOM 포트 입력 [COM3]: ").strip()
    if not port:
        port = 'COM3'
    
    # 연결
    gilson = GilsonFC203B(port=port, unit_id=6)
    gilson.debug = True  # 디버그 출력
    
    if not gilson.connect():
        print("\n연결 실패. 종료합니다.")
        exit(1)
    
    try:
        # 현재 위치 읽기
        print("\n[현재 위치]")
        x, y = gilson.get_position()
        print(f"  X = {x} mm, Y = {y} mm")
        
        # 테스트 이동
        print("\n[테스트 이동]")
        input("Enter를 누르면 (50, 50)으로 이동합니다...")
        gilson.move_to_xy(50.0, 50.0)
        
        x, y = gilson.get_position()
        print(f"  이동 후 위치: X = {x} mm, Y = {y} mm")
        
        # 홈으로
        input("\nEnter를 누르면 홈(0, 0)으로 이동합니다...")
        gilson.home()
        
        print("\n✅ 테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n\n중단됨")
    
    finally:
        gilson.disconnect()
