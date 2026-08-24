# Architecture

## 1. System Layers

```text
Application Layer
+---------------------------------------+
| Classification / AI Application      |
+---------------------------------------+

Adaptive Runtime Layer
+---------------------------------------+
| QoS Controller                       |
| Resource Monitor                     |
+---------------------------------------+

AI Runtime Layer
+---------------------------------------+
| Preprocess                            |
| AI Inference                          |
| Postprocess                           |
| STM32 AI Runtime / Neural-ART NPU     |
+---------------------------------------+

RTOS Layer
+---------------------------------------+
| FreeRTOS                              |
| Task / Queue / Semaphore / Timer      |
+---------------------------------------+

Hardware
+---------------------------------------+
| STM32N657                             |
| Cortex-M55 / Neural-ART               |
| SRAM / Flash                          |
| Camera / UART / GPIO                  |
+---------------------------------------+
```

---

## 2. Initial Task Model

초기 target 값이며 실제 보드 profiling 후 변경한다.

| Task | Period | Relative Deadline | Priority | 역할 |
|---|---:|---:|---:|---|
| Capture | 33 ms | 33 ms | High | frame acquisition |
| Preprocess | 33 ms | 33 ms | High | resize/normalize |
| Inference | 33 ms | 33 ms | Medium-High | CNN inference |
| Communication | 100 ms | 100 ms | Medium | UART/network output |
| Monitor | 100 ms | 100 ms | Medium | runtime metrics |
| Logging | 1000 ms | 1000 ms | Low | statistics output |

초기에는 Capture 대신 preloaded test vector를 사용할 수 있다.

---

## 3. Inter-task Communication

### Queue

```text
Capture
   |
frame_queue
   v
Preprocess
   |
input_queue
   v
Inference
   |
result_queue
   v
Output
```

### Synchronization

- DMA complete -> binary semaphore
- shared statistics -> mutex 또는 critical section
- inference completion -> queue/event notification

---

## 4. Timing Measurement

우선순위:

1. Cortex cycle counter(DWT CYCCNT)
2. high-resolution hardware timer
3. FreeRTOS tick

FreeRTOS tick만으로 짧은 inference latency를 측정하지 않는다.

측정 항목:

```text
T_capture
T_preprocess
T_inference
T_postprocess
T_end_to_end
```

---

## 5. QoS Definition

예시:

### QoS 0 - Low
- input: 96x96
- inference period: 100 ms

### QoS 1 - Medium
- input: 96x96
- inference period: 66 ms

### QoS 2 - High
- input: 96x96
- inference period: 33 ms

현재 NPU 검증 모델의 입력 shape가 static `1x3x96x96`이므로 초기 구현에서는
inference period만 조절한다. 입력 해상도나 모델 variant는 별도 모델을 생성하고
memory mapping을 다시 검증한 뒤 확장한다.

---

## 6. Controller Input

```text
state = {
    cpu_utilization,
    inference_latency,
    deadline_miss_ratio,
    queue_occupancy
}
```

### Initial Heuristic

```text
if deadline_miss_ratio > 0.05:
    qos = max(qos - 1, MIN_QOS)

else if cpu_utilization < 0.60 and deadline_miss_ratio == 0:
    qos = min(qos + 1, MAX_QOS)
```

히스테리시스를 두어 빈번한 QoS oscillation을 방지한다.

---

## 7. Firmware Module Proposal

```text
firmware/App/
    app_main.c

firmware/RTOS/
    task_capture.c
    task_preprocess.c
    task_inference.c
    task_monitor.c
    task_output.c

firmware/AI/
    ai_model.c
    ai_preprocess.c
    ai_postprocess.c

firmware/System/
    profiler.c
    qos_controller.c
    system_metrics.c
```

각 모듈은 hardware-dependent code와 application logic을 가능한 분리한다.
