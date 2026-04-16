from __future__ import annotations

import asyncio
from time import perf_counter

from app.runtime.parallel import ParallelAgentSpec, run_bounded_parallel


async def test_run_bounded_parallel_limits_concurrency_and_runs_in_parallel() -> None:
    active_agents = 0
    max_active_agents = 0
    lock = asyncio.Lock()

    async def run_agent(agent_name: str) -> str:
        nonlocal active_agents, max_active_agents

        async with lock:
            active_agents += 1
            max_active_agents = max(max_active_agents, active_agents)

        try:
            await asyncio.sleep(0.1)
            return f"{agent_name}_ok"
        finally:
            async with lock:
                active_agents -= 1

    specs = [
        ParallelAgentSpec(
            agent_name=f"agent_{index}",
            run=lambda agent_name=f"agent_{index}": run_agent(agent_name),
            timeout_ms=500,
        )
        for index in range(4)
    ]

    started_at = perf_counter()
    result = await run_bounded_parallel(
        specs,
        concurrency_limit=2,
        minimum_successes_required=4,
    )
    elapsed_seconds = perf_counter() - started_at

    assert max_active_agents == 2
    assert elapsed_seconds < 0.32
    assert set(result.successes) == {"agent_0", "agent_1", "agent_2", "agent_3"}
    assert result.failures == []
    assert result.minimum_successes_required == 4
    assert result.minimum_successes_met is True


async def test_run_bounded_parallel_counts_queue_wait_against_timeout() -> None:
    queued_agent_started = asyncio.Event()

    async def slow_agent() -> str:
        await asyncio.sleep(0.2)
        return "chart_ok"

    async def queued_agent() -> str:
        queued_agent_started.set()
        return "risk_ok"

    result = await run_bounded_parallel(
        [
            ParallelAgentSpec(
                agent_name="chart",
                run=slow_agent,
                timeout_ms=500,
            ),
            ParallelAgentSpec(
                agent_name="risk",
                run=queued_agent,
                timeout_ms=50,
            ),
        ],
        concurrency_limit=1,
        minimum_successes_required=2,
    )

    assert result.successes == {"chart": "chart_ok"}
    assert result.failed_agents == ["risk"]
    assert result.failures[0].code == "timeout"
    assert queued_agent_started.is_set() is False
    assert result.minimum_successes_met is False


async def test_run_bounded_parallel_surfaces_timeout_and_cancellation() -> None:
    cancellation_observed = asyncio.Event()

    async def slow_agent() -> str:
        try:
            await asyncio.sleep(1.0)
            return "slow_ok"
        except asyncio.CancelledError:
            cancellation_observed.set()
            raise

    result = await run_bounded_parallel(
        [
            ParallelAgentSpec(
                agent_name="slow",
                run=slow_agent,
                timeout_ms=50,
            ),
        ],
        concurrency_limit=1,
        minimum_successes_required=1,
    )

    assert result.successes == {}
    assert result.failed_agents == ["slow"]
    assert result.failures[0].code == "timeout"
    assert "50ms" in result.failures[0].message
    assert result.minimum_successes_met is False
    assert cancellation_observed.is_set()


async def test_run_bounded_parallel_surfaces_failures_and_tracks_coverage() -> None:
    async def successful_agent() -> str:
        return "news_ok"

    async def failing_agent() -> str:
        raise RuntimeError("fixture boom")

    result = await run_bounded_parallel(
        [
            ParallelAgentSpec(
                agent_name="news",
                run=successful_agent,
                timeout_ms=100,
            ),
            ParallelAgentSpec(
                agent_name="risk",
                run=failing_agent,
                timeout_ms=100,
            ),
        ],
        concurrency_limit=2,
        minimum_successes_required=2,
    )

    assert result.successes == {"news": "news_ok"}
    assert result.failed_agents == ["risk"]
    assert result.failures[0].code == "execution_failed"
    assert "fixture boom" in result.failures[0].message
    assert result.minimum_successes_required == 2
    assert result.minimum_successes_met is False


async def test_run_bounded_parallel_surfaces_agent_cancellation_as_failure() -> None:
    async def cancelled_agent() -> str:
        raise asyncio.CancelledError

    result = await run_bounded_parallel(
        [
            ParallelAgentSpec(
                agent_name="flow",
                run=cancelled_agent,
                timeout_ms=100,
            ),
        ],
        concurrency_limit=1,
        minimum_successes_required=1,
    )

    assert result.successes == {}
    assert result.failed_agents == ["flow"]
    assert result.failures[0].code == "cancelled"
    assert result.minimum_successes_met is False


async def test_run_bounded_parallel_surfaces_self_cancellation_as_failure() -> None:
    async def self_cancelled_agent() -> str:
        task = asyncio.current_task()
        assert task is not None
        task.cancel()
        await asyncio.sleep(0)
        return "never"

    result = await run_bounded_parallel(
        [
            ParallelAgentSpec(
                agent_name="flow",
                run=self_cancelled_agent,
                timeout_ms=100,
            ),
        ],
        concurrency_limit=1,
        minimum_successes_required=1,
    )

    assert result.successes == {}
    assert result.failed_agents == ["flow"]
    assert result.failures[0].code == "cancelled"
    assert result.minimum_successes_met is False


async def test_run_bounded_parallel_preserves_distinct_success_outputs() -> None:
    async def news_agent() -> dict[str, str]:
        return {"stance": "positive", "summary": "news sees upside"}

    async def risk_agent() -> dict[str, str]:
        return {"stance": "cautious", "summary": "risk sees volatility"}

    result = await run_bounded_parallel(
        [
            ParallelAgentSpec(
                agent_name="news",
                run=news_agent,
                timeout_ms=100,
            ),
            ParallelAgentSpec(
                agent_name="risk",
                run=risk_agent,
                timeout_ms=100,
            ),
        ],
        concurrency_limit=2,
        minimum_successes_required=2,
    )

    assert result.successes == {
        "news": {"stance": "positive", "summary": "news sees upside"},
        "risk": {"stance": "cautious", "summary": "risk sees volatility"},
    }
    assert result.failed_agents == []
    assert result.minimum_successes_met is True


async def test_run_bounded_parallel_propagates_caller_cancellation() -> None:
    async def slow_agent() -> str:
        await asyncio.sleep(1.0)
        return "slow_ok"

    parallel_task = asyncio.create_task(
        run_bounded_parallel(
            [
                ParallelAgentSpec(
                    agent_name="chart",
                    run=slow_agent,
                    timeout_ms=1000,
                ),
            ],
            concurrency_limit=1,
            minimum_successes_required=1,
        ),
    )

    await asyncio.sleep(0.05)
    parallel_task.cancel()

    try:
        await parallel_task
    except asyncio.CancelledError:
        return

    raise AssertionError("caller cancellation should propagate")
