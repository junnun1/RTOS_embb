#ifndef PROFILER_H
#define PROFILER_H

#include <stdbool.h>
#include <stdint.h>

typedef uint32_t (*profiler_cycle_reader_t)(void *context);

typedef struct
{
  profiler_cycle_reader_t read_cycle;
  void *reader_context;
  uint32_t cpu_clock_hz;
} profiler_t;

bool profiler_init(
    profiler_t *profiler,
    profiler_cycle_reader_t read_cycle,
    void *reader_context,
    uint32_t cpu_clock_hz);

bool profiler_read_cycle(
    const profiler_t *profiler,
    uint32_t *cycle_out);

uint32_t profiler_elapsed_cycles(
    uint32_t start_cycle,
    uint32_t end_cycle);

uint32_t profiler_get_cpu_clock_hz(
    const profiler_t *profiler);

#endif