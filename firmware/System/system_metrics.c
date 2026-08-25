#include "system_metrics.h"

void system_metrics_complete_record(task_run_record_t *record, uint32_t cpu_clock_hz)
{

  if (record == 0)
  {
    return;
  }

  record->execution_cycles =
      record->end_cycle - record->start_cycle;

  record->response_cycles =
      record->end_cycle - record->release_cycle;

  record->execution_time_us =
      system_metrics_cycles_to_us(
          record->execution_cycles,
          cpu_clock_hz);

  record->response_time_us =
      system_metrics_cycles_to_us(
          record->response_cycles,
          cpu_clock_hz);

  uint64_t deadline_us =
      (uint64_t)record->relative_deadline_ms * 1000ULL;

  record->deadline_miss =
      (uint64_t)record->response_time_us > deadline_us;
}

uint32_t system_metrics_cycles_to_us(uint32_t cycles, uint32_t cpu_clock_hz)
{
  if (cpu_clock_hz == 0U)
  {
    return UINT32_MAX;
  }

  uint64_t microseconds =
      ((uint64_t)cycles * 1000000ULL) / cpu_clock_hz;

  if (microseconds > UINT32_MAX)
  {
    return UINT32_MAX;
  }

  return (uint32_t)microseconds;
}