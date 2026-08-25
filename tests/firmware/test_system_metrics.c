
#include "system_metrics.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#define TEST_CPU_CLOCK_HZ 100000000U

static void test_normal_record(void)
{
  task_run_record_t record = {0};

  record.relative_deadline_ms = 33U;
  record.release_cycle = 1000U;
  record.start_cycle = 101000U;
  record.end_cycle = 1101000U;

  system_metrics_complete_record(
      &record,
      TEST_CPU_CLOCK_HZ);

  assert(record.execution_cycles == 1000000U);
  assert(record.response_cycles == 1100000U);
  assert(record.execution_time_us == 10000U);
  assert(record.response_time_us == 11000U);
  assert(record.deadline_miss == false);
}

static void test_deadline_miss(void)
{
  task_run_record_t record = {0};

  record.relative_deadline_ms = 33U;
  record.release_cycle = 1000U;
  record.end_cycle = 4001000U;

  system_metrics_complete_record(
      &record,
      TEST_CPU_CLOCK_HZ);

  assert(record.deadline_miss == true);
}
static void test_cycle_wraparound(void)
{
  task_run_record_t record = {0};


  record.start_cycle = UINT32_MAX - 49U;
  record.end_cycle = 50U;

  system_metrics_complete_record(
      &record,
      TEST_CPU_CLOCK_HZ);

  assert(record.execution_cycles == 100U);
  assert(record.execution_time_us == 1U);

}
static void test_zero_cpu_clock(void){

  assert(system_metrics_cycles_to_us(100U, 0U) == UINT32_MAX);
}

int main(void)
{
  test_normal_record();
  test_deadline_miss();
  test_cycle_wraparound();
  test_zero_cpu_clock();

  printf("All system_metrics tests passed.\n");
  return 0;
}
