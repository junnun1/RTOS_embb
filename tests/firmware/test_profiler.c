#include "profiler.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#define TEST_CPU_CLOCK_HZ 100000000U

typedef struct
{
  uint32_t cycle;
} fake_cycle_source_t;

static uint32_t fake_read_cycle(void *context)
{
  fake_cycle_source_t *source = context;
  return source->cycle;
}

static void test_read_cycle_from_fake_reader(void)
{
  fake_cycle_source_t source = {100U};
  profiler_t profiler = {0};
  uint32_t actual_cycle = 0U;

  /* profiler_init()이 true인지 검증 */
  assert(profiler_init(&profiler, fake_read_cycle, &source, TEST_CPU_CLOCK_HZ) == true);

  /* profiler_read_cycle()이 true인지 검증 */
  assert(profiler_read_cycle(&profiler, &actual_cycle));

  /* actual_cycle이 source.cycle과 같은지 검증 */

  assert(actual_cycle == source.cycle);
}

static void test_init_rejects_invalid_arguments(void)
{
  fake_cycle_source_t source = {100U};
  profiler_t profiler = {0};

  /* profiler 포인터가 NULL이면 false */
  assert(profiler_init(NULL, fake_read_cycle, &source, TEST_CPU_CLOCK_HZ) == false);

  /* cycle reader가 NULL이면 false */
  assert(profiler_init(&profiler, NULL, &source, TEST_CPU_CLOCK_HZ) == false);

  /* CPU clock이 0이면 false */
  assert(profiler_init(&profiler, fake_read_cycle, &source, 0U) == false);
}

static void test_read_cycle_rejects_invalid_arguments(void)
{
  fake_cycle_source_t source = {100U};
  profiler_t profiler = {0};
  profiler_t uninitialized_profiler = {0};
  uint32_t actual_cycle = 0U;

  assert(profiler_init(
             &profiler,
             fake_read_cycle,
             &source,
             TEST_CPU_CLOCK_HZ) == true);

  /* NULL profiler */
  assert(profiler_read_cycle(NULL, &actual_cycle) == false);

  /* NULL 출력 포인터 */
  assert(profiler_read_cycle(&profiler, NULL) == false);

  /* read_cycle이 NULL인 미초기화 profiler */
  assert(profiler_read_cycle(&uninitialized_profiler, &actual_cycle) == false);
}

static void test_elapsed_cycles_handles_wraparound(void)
{
  uint32_t start_cycle = UINT32_MAX - 49U;
  uint32_t end_cycle = 50U;

  /* profiler_elapsed_cycles() 결과가 100U인지 검증 */
  assert(profiler_elapsed_cycles(start_cycle, end_cycle) == 100U);
}

static void test_elapsed_cycles_without_wraparound(void)
{
  uint32_t start_cycle = 100U;
  uint32_t end_cycle = 350U;

  assert(profiler_elapsed_cycles(start_cycle, end_cycle) == 250U);
}

static void test_get_cpu_clock_hz(void)
{
  fake_cycle_source_t source = {100U};
  profiler_t profiler = {0};

  assert(profiler_init(
             &profiler,
             fake_read_cycle,
             &source,
             TEST_CPU_CLOCK_HZ) == true);

  /* 정상 profiler에서는 설정한 clock 반환 */
  assert(profiler_get_cpu_clock_hz(&profiler) == TEST_CPU_CLOCK_HZ);

  /* NULL profiler에서는 0 반환 */
  assert(profiler_get_cpu_clock_hz(NULL) == 0U);
}

int main(void)
{
  test_read_cycle_from_fake_reader();

  test_init_rejects_invalid_arguments();
  test_read_cycle_rejects_invalid_arguments();
  test_elapsed_cycles_handles_wraparound();
  test_elapsed_cycles_without_wraparound();
  test_get_cpu_clock_hz();
  printf("All profiler tests passed.\n");
  return 0;
}
