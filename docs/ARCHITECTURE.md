# FreeRTOS and QoS Architecture

## 1. Purpose and Current Decision

이 문서는 STM32N657의 단일 Neural-ART NPU를 여러 periodic inference task가 공유하는
초기 RTOS/QoS 구조의 기준 문서다. 보드 도착 전에는 contract와 portable logic을
확정하고, 실제 period와 execution time은 on-target profiling 후 결정한다.

초기 설계 결정은 다음과 같다.

- synthetic `BackgroundTask`를 핵심 실험에서 제거한다.
- 동일한 INT8 MobileNetV2를 실행하는 periodic `InferenceTask`를 여러 개 둔다.
- task 생성, Ready/Blocked 전환, 선점, priority inheritance는 FreeRTOS에 맡긴다.
- 별도의 RM dispatcher나 application-level ready queue scheduler를 만들지 않는다.
- NPU는 하나의 공유 자원이며 application-level mutex로 보호한다.
- 한 task가 mutex를 얻으면 input binding부터 output copy까지 full inference를 끝낸 뒤
  mutex를 반환한다. 초기 실험에는 epoch-level inference interleaving을 사용하지 않는다.
- 초기 priority는 base period가 짧을수록 높은 fixed priority를 갖는 RM 방식으로 정한다.
- Monitor와 QoS policy를 분리한다. `MonitorTask`는 window state만 만들고,
  `QoSControllerTask`가 다음 QoS action을 선택한다.
- 초기 controller는 board-local heuristic이고, 이후 같은 state/action contract를 통해
  PC RL controller로 교체한다.
- 초기 QoS는 model/resolution switching이 아니라 inference period만 변경한다.
- 초기 resource reference는 logical NPU utilization `U*=0.67`, DMR reference는
  `M*=0.05`로 시작하되 보드 실측 후 조정한다.

`U*=0.67`은 non-preemptive RM schedulability 보장값이 아니다. 낮은 priority inference가
NPU mutex를 보유하여 만드는 blocking이 있으므로 response-time analysis와 실측 DMR을
함께 사용해야 한다.

## 2. Why This Design Was Selected

### 2.1 Rejected: one inference task plus synthetic CPU load

초기안은 하나의 `InferenceTask`와 CPU busy-loop `BackgroundTask`를 함께 실행하는
구조였다. 이 구조는 CPU interference를 만들기 쉽지만 STM32N6에서는 NPU가 CPU와
동시에 진행할 수 있어 논문의 single-resource task model과 직접 대응하기 어렵다.
NPU 실행 중 CPU를 polling하도록 강제해도 task가 선점된 동안 NPU가 계속 진행할 수
있으므로 CPU/NPU를 완전히 하나의 물리 자원으로 만들지는 못한다.

### 2.2 Rejected: custom central RM dispatcher

여러 inference request를 application queue에 넣고 직접 RM/EDF로 선택하는 구조는
가능하지만, 이 경우 FreeRTOS의 기본 task scheduler를 관찰하려는 프로젝트 목적보다
custom scheduler 구현이 중심이 된다.

### 2.3 Selected: periodic FreeRTOS tasks plus a shared NPU mutex

각 inference stream을 실제 FreeRTOS periodic task로 만들고 task priority와 mutex
경쟁을 FreeRTOS가 처리하게 한다. 이 구조에서는 다음 RTOS 현상을 직접 관찰할 수 있다.

- fixed-priority preemptive scheduling
- RM priority assignment
- `vTaskDelayUntil()` 기반 periodic release
- shared-resource blocking
- priority inversion과 mutex priority inheritance
- deadline miss와 response time
- runtime QoS period 변경

## 3. System Structure

```text
InferenceTask_A ─┐
InferenceTask_B ─┼── application NPU mutex ── Neural-ART runtime ── NPU
InferenceTask_C ─┘
       │
       │ completed task_run_record_t
       ▼
 MonitorTask ── qos_window_state_t ── QoSControllerTask
       │                                  │
       │ immutable telemetry snapshot     │ qos_action_t
       ▼                                  ▼
  LoggerTask ── UART ── PC           InferenceTasks
```

`MonitorTask`와 `QoSControllerTask`를 분리하는 이유는 관측과 정책을 분리하기
위해서다. 나중에 PC RL agent를 사용할 때도 InferenceTask와 MonitorTask는 유지하고
selector/transport 경계만 교체한다.

## 4. Task Contract

### 4.1 Initial task set

| Task | Release/period | Relative deadline | Relative priority | Responsibility |
|---|---|---|---|---|
| InferenceTask_A | base period `T_A`, QoS-scaled | current period | highest inference priority | periodic inference stream A |
| InferenceTask_B | base period `T_B`, QoS-scaled | current period | middle inference priority | periodic inference stream B |
| InferenceTask_C | base period `T_C`, QoS-scaled | current period | lowest inference priority | periodic inference stream C |
| MonitorTask | one control window `W` | `W` | above inference tasks, short execution | aggregate window state only |
| QoSControllerTask | notification at window boundary | before next window | below Monitor, short execution | select and validate next QoS |
| LoggerTask | event-driven or 1000 ms | non-critical | low | UART telemetry only |

초기 stream 수는 3개다. `T_A < T_B < T_C`가 되도록 하고 FreeRTOS priority도 같은
순서로 고정한다. 정확한 base period는 warm inference service time `C`를 보드에서
측정한 후 목표 utilization에 맞춰 정한다. 문서 단계에서 임의의 latency를 가정해
period를 확정하지 않는다.

### 4.2 InferenceTask responsibility

각 task는 독립적인 periodic stream이며 다음 순서로 한 job을 실행한다.

```text
vTaskDelayUntil()로 다음 release 대기
  -> release timestamp 기록
  -> NPU mutex 요청
  -> mutex 획득 후 start timestamp 기록
  -> task 전용 input을 model input buffer에 binding/copy
  -> full inference 실행
  -> output을 task 전용 result storage에 copy
  -> end/completion timestamp 기록
  -> NPU mutex 반환
  -> execution/response/deadline 계산
  -> 완성된 record를 MonitorTask에 전달
```

공유 model instance, activation buffer, input/output binding은 NPU mutex 내부에서만
접근한다. task는 미완성 record를 다른 task에 노출하지 않는다.

### 4.3 MonitorTask responsibility

MonitorTask는 control window `W` 동안 완료된 job record를 집계한다.

- logical NPU busy time
- released/completed job count
- deadline miss count와 DMR
- stream별 job count와 DMR
- queue/mutex wait 및 response-time 통계
- 현재 QoS level과 period

MonitorTask는 QoS를 선택하거나 task period를 직접 변경하지 않는다. window가 끝나면
immutable `qos_window_state_t` snapshot을 만들어 QoSControllerTask와 LoggerTask에
전달한다.

### 4.4 QoSControllerTask responsibility

QoSControllerTask는 state를 받아 다음 window의 action을 만든다.

- state와 sequence/window 번호 검증
- overload/underload 판단
- hysteresis와 cooldown 적용
- 유효한 QoS 범위로 action 제한
- window 경계에서 InferenceTask에 새 period 전달
- 향후 PC action timeout 시 local fallback 제공

초기에는 board-local heuristic을 사용한다. PC RL 단계에서는 policy 선택만 PC로
이동하고 action validation/fallback은 보드에 남긴다.

### 4.5 LoggerTask responsibility

LoggerTask만 UART TX를 소유한다. metrics나 QoS state를 수정하지 않고 전달받은
snapshot을 CSV로 직렬화한다. UART 출력 때문에 inference task가 block되지 않도록
InferenceTask가 직접 logging하지 않는다.

## 5. FreeRTOS Scheduling and NPU Non-preemption

### 5.1 Fixed-priority RM mapping

FreeRTOS는 Ready 상태 task 중 가장 높은 priority task를 실행한다. inference priority는
base period에 따라 한 번 정한다.

```text
T_A < T_B < T_C
  -> priority(A) > priority(B) > priority(C)
```

초기 QoS는 모든 stream에 공통 scale을 적용하여 period 순서를 유지한다.

```text
High:   T_i = base_i * scale_high
Medium: T_i = base_i * scale_medium
Low:    T_i = base_i * scale_low
```

정확한 scale과 period는 보드 profiling 후 `U*=0.67` 근처가 되도록 결정한다. 향후
task별 QoS vector를 허용하면 period 순서가 교차할 수 있다. 그 단계에서는 window
경계에서 `vTaskPrioritySet()`으로 RM priority를 다시 매기거나, base-period fixed
priority라는 정책을 명시적으로 유지한다.

### 5.2 Full-inference application mutex

ST runtime의 내부 synchronization에만 의존하지 않고 application mutex를 full
inference 구간에 건다.

```c
xSemaphoreTake(npu_mutex, portMAX_DELAY);
ai_model_bind_input(...);
ai_model_run(...);
ai_model_copy_output(...);
xSemaphoreGive(npu_mutex);
```

interrupt나 scheduler를 끄는 critical section은 사용하지 않는다. mutex를 보유한
task가 CPU에서 선점될 수는 있지만 다른 inference task는 같은 NPU/model memory에
들어가지 못한다.

### 5.3 Blocking and priority inheritance example

```text
1. low-priority C가 NPU mutex를 획득하고 inference 실행
2. high-priority A가 release되어 C를 CPU에서 선점
3. A가 같은 mutex를 요청하지만 C가 보유 중이므로 Blocked
4. FreeRTOS mutex priority inheritance로 C priority가 임시 상승
5. C가 inference를 완료하고 mutex 반환
6. C priority 복귀, A가 mutex를 얻어 inference 실행
```

이 blocking은 non-preemptive NPU resource의 정상적인 특성이다. binary semaphore가
아니라 FreeRTOS mutex를 사용해야 priority inheritance를 사용할 수 있다.

### 5.4 NPU interrupt boundary

STM32N6 runtime은 NPU event/epoch completion interrupt를 지원하지만 임의의 epoch
중간에서 inference를 suspend/resume하는 일반적인 선점 모델은 사용하지 않는다.
초기 프로젝트에서는 runtime의 epoch-level parallel-network 기능을 끄고 application
mutex로 full inference를 직렬화한다. 이 선택은 activation buffer 공유와 timing 해석을
단순하게 한다.

## 6. Resource Model and Metrics

### 6.1 Logical NPU utilization

초기 controller의 utilization은 CPU utilization이 아니라 하나의 직렬 inference
resource가 window 안에서 점유된 비율이다.

```text
U_npu(t) = window 안의 NPU mutex 보유시간 합 / window duration
```

mutex 보유 구간이 겹치지 않으므로 합은 중복되지 않는다. 이 값에는 input binding,
runtime invocation, NPU completion wait, output copy 등 의도적으로 정의한 full service
구간이 포함된다. 정확한 명칭은 `npu_busy_ratio` 또는
`inference_resource_utilization`이며 `cpu_utilization`이라고 기록하지 않는다.

초기 reference:

```text
U* = 0.67
M* = 0.05
```

`U*=0.67`은 보수적인 bring-up reference다. 고전적 preemptive RM utilization bound를
non-preemptive NPU에 적용한 보장값이 아니다.

mutex 보유 구간이 control window 경계를 넘으면 완료된 job 전체 시간을 한 window에
넣지 않고 각 window와 겹치는 구간만 잘라서 합산해야 한다.

```text
busy interval: 0.95 s -> 1.05 s
window 0:       0.00 s -> 1.00 s  => 50 ms 귀속
window 1:       1.00 s -> 2.00 s  => 50 ms 귀속
```

### 6.2 Deadline-miss ratio

job의 response time은 release부터 full inference 완료까지다.

```text
response_time = completion_time - release_time
deadline_miss = response_time > relative_deadline
DMR(t) = missed jobs in window / judged jobs in window
```

relative deadline은 초기에는 current period와 같게 둔다. window 경계에 걸친 job의
집계 규칙은 구현 전에 하나로 고정해야 하며, 우선안은 job deadline이 속한 window에
miss 여부를 귀속하는 것이다.

### 6.3 Non-preemptive response-time analysis

utilization만으로 schedulability를 주장하지 않는다. task `i`는 자신보다 낮은 priority
job 하나에 의해 막힐 수 있다.

```text
B_i = max execution time among lower-priority inference tasks
```

보드에서 `C_i`를 얻은 뒤 non-preemptive fixed-priority response-time analysis와 실측
DMR을 함께 사용한다. 최종 acceptance condition은 각 task의 `R_i <= D_i`와 windowed
DMR reference 만족이다.

### 6.4 Reference thesis mapping

설계 참고 문서는 repository root의
`200000943048_20260826140819.pdf`, *Adaptive Real-Time Scheduling for Open Systems
via Reinforcement Learning*이다. 논문은 single-core EDF에서 control window마다 CPU
utilization `U(t)`, DMR `M(t)`, task별 QoS vector를 관찰하고 다음 window의 task별
period/QoS를 선택한다. overload에서는 QoS를 낮추고, 안전한 underload에서는 QoS를
높이며, 최종 구조는 RL policy와 utilization predictor/safety shield를 포함한다.

이 프로젝트는 첫 RTOS 구현에서 다음처럼 단순화/변형한다.

| Reference thesis | Initial STM32N657 design |
|---|---|
| single-core CPU resource | single logical NPU/inference resource |
| EDF | FreeRTOS fixed priority with RM assignment |
| preemptive periodic jobs | full-inference non-preemptive mutex section |
| task별 QoS vector | initial global QoS scale |
| CPU utilization | logical NPU mutex-busy ratio |
| RL + predictor + shield | board-local heuristic first |

유지하는 핵심 control loop는 `window state -> QoS action -> next window execution`과
utilization/DMR constraint다. 초기 heuristic이 검증된 후 task별 QoS와 PC RL selector를
추가한다.

## 7. QoS Control Contract

### 7.1 State

초기 state는 windowed metric과 현재 global QoS다.

```c
typedef struct
{
  uint32_t window_index;
  uint32_t window_duration_us;
  uint16_t npu_utilization_permille;
  uint16_t total_dmr_permille;
  uint16_t ready_or_waiting_jobs;
  qos_level_t current_qos;
} qos_window_state_t;
```

stream별 count/DMR과 latency 통계는 telemetry에 추가하지만 첫 heuristic의 필수 입력은
아니다. 임베디드 구현에서는 floating point 대신 permille 표현을 우선 검토한다.

### 7.2 Action

```c
typedef struct
{
  uint32_t source_window_index;
  qos_level_t next_qos;
} qos_action_t;
```

초기에는 global action 하나가 세 inference task의 period scale을 함께 변경한다. 이로써
RM priority 순서를 유지한다. 논문의 task별 QoS vector와 PC RL action branching은
후속 단계에서 확장한다.

### 7.3 Initial heuristic

논문 구조를 단순화한 첫 controller는 다음과 같다.

```text
if U_npu > U* or DMR > M*:
    QoS를 한 단계 낮춤

else if U_npu가 lower band보다 낮고 DMR <= M*:
    QoS를 한 단계 높임

else:
    현재 QoS 유지
```

lower band, 연속 window 수, hysteresis, cooldown은 host simulation 또는 보드 fixed-QoS
baseline을 얻은 후 확정한다. predictor, safety shield, adaptive window, DQN은 초기
heuristic 완료 전에는 구현하지 않는다.

## 8. Metrics Ownership

| Data | Single writer/owner | Readers | Transfer rule |
|---|---|---|---|
| current job record | owning InferenceTask | none while mutable | completion 후 값 복사 |
| NPU/model/activation buffer | current mutex holder | no concurrent reader | full inference mutex |
| per-window aggregate | MonitorTask | QoSController, Logger | immutable snapshot |
| current/next QoS action | QoSControllerTask | InferenceTasks, Logger | window-indexed command |
| task current period | owning InferenceTask | Monitor | action을 안전한 release 경계에서 적용 |
| UART TX buffer | LoggerTask | UART adapter | Logger only |

원칙은 하나의 mutable object에 writer를 하나만 두는 것이다. QoSControllerTask가 다른
task의 period 변수를 임의로 직접 수정하지 않고 command를 전달하며, InferenceTask가
정해진 경계에서 적용한다.

## 9. UART and Future PC RL Boundary

초기 UART telemetry 초안:

```csv
window_index,npu_util_permille,dmr_permille,qos_level,task_id,job_id,period_ms,execution_us,response_us,deadline_miss,mutex_wait_us
```

초기 board-local flow:

```text
Monitor state -> local heuristic -> validated action -> InferenceTasks
```

향후 PC RL flow:

```text
Monitor state -> UART TX -> PC RL agent
PC action     -> UART RX -> board action validator/fallback -> InferenceTasks
```

PC action에는 source window/sequence를 포함하여 stale action을 거부한다. 일정 시간 action이
오지 않으면 마지막 안전 action을 잠시 유지한 뒤 board-local heuristic 또는 Low QoS로
fallback한다.

## 10. Current Portable Implementation

구현 완료:

```text
firmware/System/system_metrics.c/.h
firmware/System/profiler.c/.h
tests/firmware/test_system_metrics.c
tests/firmware/test_profiler.c
```

- `system_metrics`: release/start/end, execution/response, deadline miss 계산
- `profiler`: injected cycle reader/context/CPU clock
- unsigned subtraction 기반 32-bit cycle wrap-around
- strict C11 host tests

현재 `task_run_record_t`의 background-related field는 이전 설계의 잔재다. 즉시 ABI를
변경하기보다 다음 metrics contract 작업에서 stream ID, mutex wait, window accounting을
포함하도록 정리한다.

## 11. Before-board and On-target Boundary

보드 도착 전 확정/구현:

- task, mutex, state/action, metrics ownership contract
- portable window aggregation과 heuristic controller
- host test
- AI runtime adapter interface
- UART schema

보드에서 확인 후 확정:

- warm inference service time `C_i`
- base periods와 QoS scale
- actual FreeRTOS priorities
- tick rate
- ST runtime sync/async configuration과 OSAL integration
- DWT adapter, UART handle, generated network symbols
- non-preemptive response-time analysis 입력값

CPU clock, peripheral handle, memory address, activation-buffer placement은 CubeMX/generated
runtime 확인 전까지 hardcode하지 않는다.

## 12. References

- `200000943048_20260826140819.pdf` — *Adaptive Real-Time Scheduling for Open Systems
  via Reinforcement Learning*
- [ST Neural-ART NPU concepts](https://stm32ai-cs.st.com/assets/embedded-docs/stneuralart_programming_model.html)
- [Embedded ST Neural-ART API and RTOS stack](https://stm32ai-cs.st.com/assets/embedded-docs/stneuralart_api_and_stack.html)
