# TODO

## 오늘 할 일

오늘 목표는 **보드 없이도 AI deployment 경로가 실제로 성립하는지 확인하는 것**이다.

### P0 - 반드시 완료

- [x] Git repository 생성
- [x] 아래 기본 폴더 생성
  - `training/`
  - `benchmarks/`
  - `firmware/`
  - `docs/`
  - `results/`
- [x] Python venv 생성
- [x] PyTorch / torchvision / ONNX / ONNX Runtime 설치
- [x] 데이터셋 1개 선정
- [x] Student 모델 1개 선정
- [x] pretrained 또는 간단한 baseline inference 실행
- [x] Student 모델을 ONNX로 export
- [x] STM32Cube AI Studio에서 ONNX import/analysis 테스트

### P1 - 가능하면 오늘

- [x] Teacher 모델 선정
- [x] Student 학습 코드 skeleton 작성
- [ ] Knowledge Distillation loss skeleton 작성
- [ ] accuracy / model size benchmark script 작성
- [x] `requirements.txt` 생성

### 오늘 종료 조건

오늘은 학습 정확도를 높이는 것이 목표가 아니다.

아래 흐름이 한 번 연결되면 성공이다.

```text
PyTorch Student
    -> ONNX
    -> ONNX Runtime test
    -> STM32Cube AI Studio validation
```

---

# 보드 도착 전 전체 TODO

## 1. Environment

- [x] Python environment 고정
- [x] requirements.txt 작성
- [x] Git repository 정리
- [x] experiment config 방식 결정

## 2. Dataset

- [x] dataset 결정
- [x] train/validation split
- [x] preprocessing pipeline 작성
- [ ] representative calibration dataset 구성

## 3. Teacher

- [ ] teacher baseline 확보
- [ ] checkpoint 저장
- [ ] validation script 작성

## 4. Student

- [x] student baseline 학습
- [x] parameter count 계산
- [x] model size 계산
- [x] baseline accuracy 저장

## 5. Distillation

- [ ] KD loss 구현
- [ ] temperature 설정
- [ ] alpha 설정
- [ ] baseline vs KD 비교

## 6. Quantization

- [ ] PTQ 실험
- [ ] QAT 실험
- [ ] FP32 vs INT8 accuracy 비교
- [ ] FP32 vs INT8 size 비교

## 7. Export

- [x] ONNX export
- [x] ONNX checker
- [x] ONNX Runtime output validation
- [x] STM32Cube AI Studio import/analyze
- [x] unsupported operator 확인
- [ ] INT8 ONNX의 Neural-ART HW epoch mapping 확인

## 8. Benchmark Tools

- [ ] accuracy benchmark
- [ ] model size benchmark
- [ ] PC latency benchmark
- [x] CSV logger
- [ ] plot script

## 9. RTOS Preparation

- [ ] FreeRTOS task / queue / semaphore 복습
- [ ] initial task architecture 작성
- [ ] task period/deadline 초기값 정하기
- [ ] profiler interface 설계
- [ ] UART log format 설계

## 10. Board Arrival Ready Check

보드가 도착했을 때 다음 파일이 준비되어 있어야 한다.

```text
models/student_baseline_fp32.onnx
models/student_kd_fp32.onnx
models/student_int8.onnx       (가능한 export 방식에 따라 변경)
results/model_comparison.csv
training configs
STM32Cube AI compatibility 결과
```

---

# 보드 도착 후 첫날 TODO

- [ ] ST-LINK firmware 확인
- [ ] CubeIDE sample build
- [ ] LED blink
- [ ] UART printf
- [ ] FreeRTOS single periodic task
- [ ] DWT cycle counter profiler
- [ ] AI model 최소 inference

카메라는 첫날 연결하지 않는다.

---

# 현재 확보된 결과

## Student Baseline

- Dataset: CIFAR-10 (train 50,000 / validation 10,000)
- Model: MobileNetV2, ImageNet V2 pretrained
- Input: FP32 `1x3x96x96`
- Parameters: 2,236,682
- Best validation accuracy: 95.46% (epoch 28/30)
- ONNX size: 8.51 MiB
- PyTorch vs ONNX Runtime max absolute error: 0.00000083

## STM32N6 FP32 Analysis

- ST Edge AI Core: 4.0.1
- ONNX import / Neural-ART compilation: 성공
- Weights: 8.47 MiB
- Activations: 1.58 MiB
- MACC: 55,041,829
- Epoch mapping: SW 100 / HW(EC) 1
- 결론: operator 호환성은 확인했으나 FP32 연산은 대부분 software fallback이다.
- 다음 검증: INT8 모델 생성 후 HW epoch 비율, accuracy, memory 비교
