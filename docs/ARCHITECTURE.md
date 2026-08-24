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

## 2. Target Task Model

전체 pipeline 확장 시의 target 값이며 실제 보드 profiling 후 변경한다.

| Task | Period | Relative Deadline | Priority | 역할 |
|---|---:|---:|---:|---|
| Capture | 33 ms | 33 ms | High | frame acquisition |
| Preprocess | 33 ms | 33 ms | High | resize/normalize |
| Inference | 33 ms | 33 ms | Medium-High | CNN inference |
| Communication | 100 ms | 100 ms | Medium | UART/network output |
| Monitor | 100 ms | 100 ms | Medium | runtime metrics |
| Logging | 1000 ms | 1000 ms | Low | statistics output |

### Pre-board and first bring-up task set

보드 도착 전과 최초 bring-up에서는 Capture를 만들지 않고 preloaded test vector를
사용한다. 초기 구현 대상은 Inference, Background, Monitor, Logger 네 task다.

| Initial task | Period | Relative deadline | Priority | 역할 |
|---|---:|---:|---:|---|
| Inference | 33 ms | 33 ms | High | test-vector AI inference |
| Background | experiment-defined | experiment-defined | Medium | synthetic CPU workload |
| Monitor | 100 ms | 100 ms | Medium | metrics aggregation |
| Logger | 1000 ms | 1000 ms | Low | UART CSV output |

Capture/Preprocess/Communication은 단일 inference와 timing 검증 이후 추가한다.

---

## 3. Inter-task Communication

최초 test-vector 단계에서는 Inference task가 주기적으로 직접 입력을 읽고,
Monitor/Logger는 공유 metrics snapshot만 사용한다. 이 단계의 최소 동기화는
metrics snapshot을 보호하는 mutex 또는 짧은 critical section이다.

Capture pipeline을 추가한 뒤 아래 queue 구조로 확장한다.

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

보드 도착 전 profiler contract에는 다음을 포함한다.

- 32-bit DWT CYCCNT wrap-around를 unsigned subtraction으로 처리
- CPU clock 주파수를 주입받아 cycle을 microsecond로 변환
- instrumentation overhead를 별도로 측정
- mean/min/max는 streaming aggregate로 유지
- p95는 고정 크기 sample window 또는 histogram으로 계산

공통 metrics record:

```text
release_timestamp
start_timestamp
end_timestamp
execution_time
response_time
deadline_miss
iteration
background_load
queue_backlog
qos_level
```

UART CSV 초안:

```csv
timestamp_ms,task_name,iteration,period_ms,execution_us,response_us,deadline_miss,background_load,qos_level
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
    task_inference.c
    task_background.c
    task_monitor.c
    task_logger.c

firmware/AI/
    ai_model_adapter.c
    ai_preprocess.c
    ai_postprocess.c

firmware/System/
    profiler.c
    qos_controller.c
    system_metrics.c
```

각 모듈은 hardware-dependent code와 application logic을 가능한 분리한다.

## 8. Pre-board Implementation Boundary

보드 도착 전에는 portable state/metrics/QoS logic과 interface를 작성한다. 다음 값은
board/CubeMX 프로젝트에서 확인하기 전까지 hardcode하지 않는다.

- CPU clock과 DWT 가용성
- HAL peripheral handle
- UART instance와 baud rate
- Neural-ART generated symbol과 memory address
- FreeRTOS heap implementation과 static allocation policy
- external Flash/RAM linker section

FreeRTOS API와 HAL 호출은 wrapper/adapter 뒤에 두어 host-side unit test 또는 stub
build가 가능하도록 설계한다.
