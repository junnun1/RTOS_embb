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
- [ ] 데이터셋 1개 선정
- [ ] Student 모델 1개 선정
- [ ] pretrained 또는 간단한 baseline inference 실행
- [ ] Student 모델을 ONNX로 export
- [ ] STM32Cube AI Studio에서 ONNX import/validation 테스트

### P1 - 가능하면 오늘

- [ ] Teacher 모델 선정
- [ ] Student 학습 코드 skeleton 작성
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
- [ ] experiment config 방식 결정

## 2. Dataset

- [ ] dataset 결정
- [ ] train/validation split
- [ ] preprocessing pipeline 작성
- [ ] representative calibration dataset 구성

## 3. Teacher

- [ ] teacher baseline 확보
- [ ] checkpoint 저장
- [ ] validation script 작성

## 4. Student

- [ ] student baseline 학습
- [ ] parameter count 계산
- [ ] model size 계산
- [ ] baseline accuracy 저장

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

- [ ] ONNX export
- [ ] ONNX checker
- [ ] ONNX Runtime output validation
- [ ] STM32Cube AI Studio import
- [ ] unsupported operator 확인

## 8. Benchmark Tools

- [ ] accuracy benchmark
- [ ] model size benchmark
- [ ] PC latency benchmark
- [ ] CSV logger
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
models/student_fp32.onnx
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
