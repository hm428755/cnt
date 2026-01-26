"""
3-Class CNT 분류기 (업데이트 버전)
- 반도체: 950-1050nm 피크 유무
- 금속/TRASH: 850-930nm 곡률

분류 순서: TRASH → 금속 → TRASH → 반도체 → TRASH
"""
import numpy as np
from scipy.interpolate import interp1d
from typing import Dict, Tuple, Optional


class CNTClassifier3Class:
    """
    3-Class CNT 분류기
    
    분류 클래스:
    - 반도체 (Semiconductor): 950-1050nm 피크 존재
    - 금속 (Metal): 850-930nm 평탄 (곡률 낮음)
    - TRASH: 피크 없고 평탄하지도 않음
    """
    
    def __init__(self, 
                 resolution: float = 1.0,
                 prominence_threshold: float = 0.012,
                 curvature_threshold: float = 125e-9):
        """
        Args:
            resolution: 리샘플링 해상도 (nm 간격)
            prominence_threshold: 반도체 피크 prominence 임계값
            curvature_threshold: 금속/TRASH 구분 곡률 임계값
        """
        self.resolution = resolution
        self.prominence_threshold = prominence_threshold
        self.curvature_threshold = curvature_threshold
    
    def resample_spectrum(self, wavelength: np.ndarray, absorbance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """스펙트럼을 지정된 해상도로 리샘플링"""
        valid = ~np.isnan(wavelength) & ~np.isnan(absorbance)
        x_raw = wavelength[valid]
        y_raw = absorbance[valid]
        
        if len(x_raw) < 2:
            return np.array([]), np.array([])
        
        new_x = np.arange(400, 1301, self.resolution)
        
        if len(new_x) < 2:
            return np.array([]), np.array([])
        
        f_interp = interp1d(x_raw, y_raw, kind='linear', bounds_error=False, fill_value=np.nan)
        new_y = f_interp(new_x)
        
        valid_mask = ~np.isnan(new_y)
        new_x = new_x[valid_mask]
        new_y = new_y[valid_mask]
        
        return new_x, new_y
    
    def get_peak_prominence(self, wavelength: np.ndarray, absorbance: np.ndarray,
                            start: float = 950, end: float = 1050) -> float:
        """
        특정 구간의 피크 prominence 계산
        
        prominence = 피크 최대값 - 베이스라인
        베이스라인 = (구간 시작값 + 구간 끝값) / 2
        
        Args:
            wavelength: 파장 배열
            absorbance: 흡광도 배열
            start: 시작 파장
            end: 끝 파장
        
        Returns:
            피크 prominence 값
        """
        mask = (wavelength >= start) & (wavelength <= end)
        wl_region = wavelength[mask]
        abs_region = absorbance[mask]
        
        if len(abs_region) < 3:
            return 0.0
        
        max_val = np.max(abs_region)
        baseline = (abs_region[0] + abs_region[-1]) / 2
        prominence = max_val - baseline
        
        return prominence
    
    def get_curvature(self, wavelength: np.ndarray, absorbance: np.ndarray,
                      start: float = 850, end: float = 930) -> float:
        """
        특정 구간의 곡률 계산 (2차 다항식 피팅)
        
        곡률 = 2 * a (y = ax² + bx + c 에서)
        
        양수: 아래로 볼록 (U자)
        음수: 위로 볼록 (∩자)
        0: 직선 (평탄)
        
        Args:
            wavelength: 파장 배열
            absorbance: 흡광도 배열
            start: 시작 파장
            end: 끝 파장
        
        Returns:
            곡률 값
        """
        mask = (wavelength >= start) & (wavelength <= end)
        wl_region = wavelength[mask]
        abs_region = absorbance[mask]
        
        if len(abs_region) < 3:
            return 0.0
        
        # 2차 다항식 피팅: y = ax² + bx + c
        coeffs = np.polyfit(wl_region, abs_region, 2)
        curvature = coeffs[0] * 2  # 2차 미분 = 2a
        
        return curvature
    
    def extract_features(self, wavelength: np.ndarray, absorbance: np.ndarray) -> Dict:
        """
        분류에 필요한 특징 추출
        
        Returns:
            특징 dict
        """
        features = {}
        
        # 1. 반도체 피크 prominence (950-1050nm)
        features['semi_peak_prominence'] = self.get_peak_prominence(
            wavelength, absorbance, 950, 1050
        )
        
        # 2. 평탄 구간 곡률 (850-930nm)
        features['flat_region_curvature'] = self.get_curvature(
            wavelength, absorbance, 850, 930
        )
        
        # 추가 정보 (디버깅/분석용)
        # 평탄 구간 통계
        mask_flat = (wavelength >= 850) & (wavelength <= 930)
        abs_flat = absorbance[mask_flat]
        if len(abs_flat) > 0:
            features['flat_region_mean'] = np.mean(abs_flat)
            features['flat_region_std'] = np.std(abs_flat)
        else:
            features['flat_region_mean'] = 0.0
            features['flat_region_std'] = 0.0
        
        # 반도체 피크 구간 통계
        mask_semi = (wavelength >= 950) & (wavelength <= 1050)
        abs_semi = absorbance[mask_semi]
        if len(abs_semi) > 0:
            features['semi_peak_max'] = np.max(abs_semi)
            features['semi_peak_mean'] = np.mean(abs_semi)
        else:
            features['semi_peak_max'] = 0.0
            features['semi_peak_mean'] = 0.0
        
        return features
    
    def classify(self, wavelength: np.ndarray, absorbance: np.ndarray,
                 use_korean: bool = True) -> str:
        """
        CNT 3-Class 분류
        
        분류 로직:
        1단계: 950-1050nm 피크 prominence > threshold → 반도체
        2단계: 850-930nm 곡률 < threshold → 금속
        3단계: 나머지 → TRASH
        
        Args:
            wavelength: 원본 파장 배열
            absorbance: 원본 흡광도 배열
            use_korean: 한글 라벨 사용 여부
        
        Returns:
            예측 라벨: '반도체', '금속', 'TRASH'
        """
        # 1. 리샘플링
        resampled_wl, resampled_abs = self.resample_spectrum(wavelength, absorbance)
        
        if len(resampled_wl) < 10:
            return 'TRASH'
        
        # 2. 특징 추출
        features = self.extract_features(resampled_wl, resampled_abs)
        
        # 3. 1단계: 반도체 피크 확인
        if features['semi_peak_prominence'] > self.prominence_threshold:
            return '반도체' if use_korean else 'Semiconductor'
        
        # 4. 2단계: 곡률로 금속 vs TRASH
        if features['flat_region_curvature'] < self.curvature_threshold:
            return '금속' if use_korean else 'Metal'
        else:
            return 'TRASH'
    
    def classify_with_details(self, wavelength: np.ndarray, absorbance: np.ndarray,
                              use_korean: bool = True) -> Dict:
        """
        상세 정보와 함께 분류
        
        Returns:
            dict: 분류 결과, 특징, 판별 이유 포함
        """
        resampled_wl, resampled_abs = self.resample_spectrum(wavelength, absorbance)
        
        if len(resampled_wl) < 10:
            return {
                'label': 'TRASH',
                'reason': 'insufficient_data',
                'features': {},
                'thresholds': {
                    'prominence_threshold': self.prominence_threshold,
                    'curvature_threshold': self.curvature_threshold
                }
            }
        
        features = self.extract_features(resampled_wl, resampled_abs)
        
        # 분류 로직
        if features['semi_peak_prominence'] > self.prominence_threshold:
            label = '반도체' if use_korean else 'Semiconductor'
            reason = f"semi_peak_prominence ({features['semi_peak_prominence']:.4f}) > threshold ({self.prominence_threshold})"
        elif features['flat_region_curvature'] < self.curvature_threshold:
            label = '금속' if use_korean else 'Metal'
            reason = f"flat_region_curvature ({features['flat_region_curvature']:.2e}) < threshold ({self.curvature_threshold:.2e})"
        else:
            label = 'TRASH'
            reason = f"flat_region_curvature ({features['flat_region_curvature']:.2e}) >= threshold ({self.curvature_threshold:.2e})"
        
        return {
            'label': label,
            'reason': reason,
            'features': features,
            'thresholds': {
                'prominence_threshold': self.prominence_threshold,
                'curvature_threshold': self.curvature_threshold
            }
        }


# 테스트 코드
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    print("="*60)
    print("3-Class CNT Classifier Test")
    print("="*60)
    
    # 분류기 생성
    classifier = CNTClassifier3Class(
        resolution=1.0,
        prominence_threshold=0.012,
        curvature_threshold=125e-9
    )
    
    print("\n분류 규칙:")
    print("─"*60)
    print("1단계: 반도체 피크 확인 (950-1050nm)")
    print(f"   → prominence > {classifier.prominence_threshold} 이면 반도체")
    print("\n2단계: 평탄 구간 곡률 확인 (850-930nm)")
    print(f"   → curvature < {classifier.curvature_threshold:.2e} 이면 금속")
    print(f"   → curvature >= {classifier.curvature_threshold:.2e} 이면 TRASH")
    print("─"*60)
    
    # CSV 로드 함수
    def load_spectrum(filepath):
        wavelength = []
        absorbance = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            data_started = False
            for line in f:
                line = line.strip()
                if line == 'XYDATA':
                    data_started = True
                    continue
                if data_started:
                    if line.startswith('#') or line == '' or ',' not in line:
                        break
                    try:
                        parts = line.split(',')
                        wl = float(parts[0])
                        ab = float(parts[1])
                        wavelength.append(wl)
                        absorbance.append(ab)
                    except:
                        continue
        return np.array(wavelength), np.array(absorbance)
    
    # 테스트 파일 경로
    upload_dir = Path("/mnt/user-data/uploads")
    
    test_files = [
        # 금속 (5개)
        ("금속", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_2수집.csv"),
        ("금속", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_3수집.csv"),
        ("금속", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_4수집.csv"),
        ("금속", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_5수집.csv"),
        ("금속", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_6수집.csv"),
        # TRASH (6개)
        ("TRASH", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_7큰통.csv"),
        ("TRASH", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_8큰통__2_.csv"),
        ("TRASH", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_8큰통.csv"),
        ("TRASH", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_9큰통.csv"),
        ("TRASH", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250806_10큰통.csv"),
        ("TRASH", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250710_control분리_C1S2_250807_2큰통.csv"),
        # 반도체 (5개)
        ("반도체", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250415_control분리_C1S2_elution_따뜻하게_사용_250425_6반도체확인.csv"),
        ("반도체", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250415_control분리_C1S2_elution_따뜻하게_사용_250425_7반도체확인.csv"),
        ("반도체", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250415_control분리_C1S2_elution_따뜻하게_사용_250425_8반도체확인.csv"),
        ("반도체", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250516_control분리_150mlgel_C1S2_250626_반도체.csv"),
        ("반도체", "_한화_AST_ArcSWCNT_1mg1mL_1wt_SDS대SC_3대2_30_amplitude_Tipsonic10min_20000rpm_14_C_U_C3h_250516_control분리_C1S2_250619_11반도체.csv"),
    ]
    
    print("\n테스트 결과:")
    print("─"*60)
    
    correct = 0
    total = 0
    
    for true_label, filename in test_files:
        filepath = upload_dir / filename
        if filepath.exists():
            wl, ab = load_spectrum(filepath)
            result = classifier.classify_with_details(wl, ab)
            pred_label = result['label']
            
            match = "✓" if pred_label == true_label else "✗"
            if pred_label == true_label:
                correct += 1
            total += 1
            
            # 짧은 파일명
            short_name = filename.split('_')[-1][:20]
            print(f"  {true_label:6} → {pred_label:6} {match}  ({short_name}...)")
    
    print("─"*60)
    print(f"정확도: {correct}/{total} = {correct/total*100:.1f}%")
