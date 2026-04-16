from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Callable, Coroutine


@dataclass(frozen=True)
class ParallelAgentSpec:
    agent_name: str
    run: Callable[[], Coroutine[Any, Any, object]]
    timeout_ms: int


@dataclass(frozen=True)
class ParallelAgentFailure:
    agent_name: str
    code: str
    message: str


@dataclass(frozen=True)
class ParallelExecutionResult:
    successes: dict[str, object]
    failures: list[ParallelAgentFailure]
    failed_agents: list[str]
    minimum_successes_required: int
    minimum_successes_met: bool


@dataclass(frozen=True)
class _AgentOutcome:
    agent_name: str
    value: object | None = None
    failure: ParallelAgentFailure | None = None


async def run_bounded_parallel(
    specs: list[ParallelAgentSpec],
    concurrency_limit: int,
    minimum_successes_required: int,
) -> ParallelExecutionResult:
    if concurrency_limit < 1:
        raise ValueError("concurrency_limit must be at least 1")

    if minimum_successes_required < 0:
        raise ValueError("minimum_successes_required must be at least 0")

    semaphore = asyncio.Semaphore(concurrency_limit)
    outcomes = await asyncio.gather(
        *[_run_single_spec(spec=spec, semaphore=semaphore) for spec in specs],
    )

    successes: dict[str, object] = {}
    failures: list[ParallelAgentFailure] = []
    failed_agents: list[str] = []

    for outcome in outcomes:
        if outcome.failure is None:
            successes[outcome.agent_name] = outcome.value
            continue

        failures.append(outcome.failure)
        failed_agents.append(outcome.agent_name)

    return ParallelExecutionResult(
        successes=successes,
        failures=failures,
        failed_agents=failed_agents,
        minimum_successes_required=minimum_successes_required,
        minimum_successes_met=len(successes) >= minimum_successes_required,
    )


async def _run_single_spec(
    spec: ParallelAgentSpec,
    semaphore: asyncio.Semaphore,
) -> _AgentOutcome:
    runner_task: asyncio.Task[object] | None = None
    loop = asyncio.get_running_loop()
    deadline = loop.time() + (spec.timeout_ms / 1000)

    try:
        async with asyncio.timeout_at(deadline):
            async with semaphore:
                runner_task = asyncio.create_task(spec.run())
                try:
                    value = await asyncio.shield(runner_task)
                except asyncio.CancelledError:
                    current_task = asyncio.current_task()
                    if current_task is not None and current_task.cancelling():
                        raise

                    if runner_task.done() and runner_task.cancelled():
                        return _AgentOutcome(
                            agent_name=spec.agent_name,
                            failure=ParallelAgentFailure(
                                agent_name=spec.agent_name,
                                code="cancelled",
                                message="agent execution was cancelled",
                            ),
                        )
                    raise
    except TimeoutError:
        if runner_task is not None:
            runner_task.cancel()
            with suppress(asyncio.CancelledError):
                await runner_task

        return _AgentOutcome(
            agent_name=spec.agent_name,
            failure=ParallelAgentFailure(
                agent_name=spec.agent_name,
                code="timeout",
                message=f"agent timed out after {spec.timeout_ms}ms",
            ),
        )
    except asyncio.CancelledError:
        if runner_task is not None:
            runner_task.cancel()
            with suppress(asyncio.CancelledError):
                await runner_task
        raise
    except Exception as exc:
        return _AgentOutcome(
            agent_name=spec.agent_name,
            failure=ParallelAgentFailure(
                agent_name=spec.agent_name,
                code="execution_failed",
                message=f"agent execution failed: {exc}",
            ),
        )

    return _AgentOutcome(agent_name=spec.agent_name, value=value)
