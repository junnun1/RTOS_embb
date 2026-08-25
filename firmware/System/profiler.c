#include "profiler.h"

bool profiler_init(profiler_t *profiler,
                   profiler_cycle_reader_t read_cycle,
                   void *reader_context,
                   uint32_t cpu_clock_hz)
{
  if (profiler == 0)
    return false;

  if (read_cycle == 0)
    return false;

  if (cpu_clock_hz == 0U)
    return false;
  profiler->read_cycle = read_cycle;
  profiler->reader_context = reader_context;
  profiler->cpu_clock_hz = cpu_clock_hz;

  return true;
}

bool profiler_read_cycle(
    const profiler_t *profiler,
    uint32_t *cycle_out)
{
    if (profiler == 0)
  {
      return false;
  }

  if (cycle_out == 0)
  {
      return false;
  }

  if (profiler->read_cycle == 0)
  {
      return false;
  }
  *cycle_out =
    profiler->read_cycle(profiler->reader_context);
  return true;

}

uint32_t profiler_elapsed_cycles(
    uint32_t start_cycle,
    uint32_t end_cycle)
{
  return end_cycle -start_cycle;
}

uint32_t profiler_get_cpu_clock_hz(
    const profiler_t *profiler)
{
  if (profiler == 0)
  {
      return 0U;
  }

  return profiler->cpu_clock_hz;
}
