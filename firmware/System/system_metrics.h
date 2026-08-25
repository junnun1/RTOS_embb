#ifndef SYSTEM_METRICS_H
#define SYSTEM_METRICS_H

#include <stdbool.h>
#include <stdint.h>

typedef enum
{
  TASK_ID_INFERENCE = 0,
  TASK_ID_BACKGROUND,
  TASK_ID_MONITOR,
  TASK_ID_LOGGER,
  TASK_ID_COUNT
} task_id_t;

typedef enum
{
  QOS_LEVEL_LOW = 0,
  QOS_LEVEL_MEDIUM,
  QOS_LEVEL_HIGH
} qos_level_t;

typedef struct
{
  task_id_t task_id;

  uint32_t iteration;
  uint32_t period_ms;
  uint32_t relative_deadline_ms;

  uint32_t release_cycle;
  uint32_t start_cycle;
  uint32_t end_cycle;

  uint32_t execution_cycles;
  uint32_t response_cycles;

  uint32_t execution_time_us;
  uint32_t response_time_us;

  bool deadline_miss;

  uint8_t background_load_percent;
  uint16_t queue_backlog;
  qos_level_t qos_level;

} task_run_record_t;

uint32_t system_metrics_cycles_to_us(
    uint32_t cycles,
    uint32_t cpu_clock_hz);

void system_metrics_complete_record(
    task_run_record_t *record,
    uint32_t cpu_clock_hz);

#endif