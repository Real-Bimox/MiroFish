# backend/app/services/graphiti_memory_updater.py
"""
Real-time simulation activity writer for Graphiti.
Replaces zep_graph_memory_updater.py.

Key improvements over Zep version:
- Saga chains: simulation rounds are linked as ordered episode sequences
- Batch size increased from 5 to 25 to reduce LLM call overhead
- Meaningful episode names include round number and platform
- asyncio event loop bridge via run_async (no new loop per call)
"""

import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any

from graphiti_core.nodes import EpisodeType

from app.services.graphiti_client import get_graphiti, SOCIAL_SIMULATION_PROMPT
from app.utils.async_loop import run_async
from app.utils.logger import get_logger

logger = get_logger(__name__)

BATCH_SIZE = 25       # Activities per episode (up from 5 — fewer LLM calls)
SEND_INTERVAL = 5.0   # Seconds between flushes


class GraphitiMemoryUpdater:
    """
    Collects simulation agent activities and writes them to Graphiti
    in batches as episodes, linked by saga chains per simulation round.

    Saga chaining: each flush within a simulation round passes the same
    saga identifier (simulation_id) so Graphiti links episodes in order.
    saga_previous_episode_uuid threads the previous episode UUID into each
    subsequent write, enabling ordered traversal of activity history.
    """

    def __init__(self, group_id: str, simulation_id: str):
        self.group_id = group_id
        self.simulation_id = simulation_id
        self._queue: queue.Queue[dict] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(
            target=self._worker_loop,
            name=f"mem-updater-{simulation_id[:8]}",
            daemon=True,
        )
        self._current_round = 0
        # Tracks the last episode UUID written; used as saga_previous_episode_uuid
        # for chaining episodes within the same simulation saga.
        self._last_episode_uuid: str | None = None

    def start(self):
        self._worker.start()
        logger.info(f"GraphitiMemoryUpdater started for simulation={self.simulation_id}")

    def stop(self):
        self._stop_event.set()
        self._worker.join(timeout=30)
        logger.info(f"GraphitiMemoryUpdater stopped for simulation={self.simulation_id}")

    def add_activity(self, agent_name: str, platform: str, action: str, content: str, round_num: int):
        """Enqueue a single agent activity for batched writing."""
        self._queue.put({
            "agent":    agent_name,
            "platform": platform,
            "action":   action,
            "content":  content,
            "round":    round_num,
        })

    def _worker_loop(self):
        pending: list[dict] = []
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=SEND_INTERVAL)
                pending.append(item)
            except queue.Empty:
                pass

            if len(pending) >= BATCH_SIZE or (pending and self._stop_event.is_set()):
                self._flush(pending)
                pending = []

        # Drain remaining on shutdown
        while not self._queue.empty():
            try:
                pending.append(self._queue.get_nowait())
            except queue.Empty:
                break
        if pending:
            self._flush(pending)

    def _flush(self, activities: list[dict]):
        if not activities:
            return

        # Group by round for meaningful episode names
        by_round: dict[int, list[dict]] = {}
        for a in activities:
            by_round.setdefault(a["round"], []).append(a)

        for round_num, acts in sorted(by_round.items()):
            platforms = list({a["platform"] for a in acts})
            platform_str = "+".join(sorted(platforms))
            episode_name = (
                f"sim_{self.simulation_id[:8]}_round_{round_num:03d}_{platform_str}"
            )

            text_lines = []
            for a in acts:
                text_lines.append(
                    f"[Round {a['round']} | {a['platform']}] "
                    f"{a['agent']} {a['action']}: {a['content']}"
                )
            episode_body = "\n".join(text_lines)

            self._write_episode_with_retry(episode_name, episode_body, round_num, len(acts))

    def _write_episode_with_retry(
        self,
        episode_name: str,
        episode_body: str,
        round_num: int,
        activity_count: int,
    ):
        for attempt in range(3):
            try:
                graphiti = get_graphiti(self.group_id)

                kwargs: dict[str, Any] = {
                    "name": episode_name,
                    "episode_body": episode_body,
                    "source": EpisodeType.text,
                    "source_description": f"Simulation round {round_num} activity log",
                    "reference_time": datetime.now(timezone.utc),
                    "group_id": self.group_id,
                    "custom_extraction_instructions": SOCIAL_SIMULATION_PROMPT,
                    # saga links all episodes under this simulation's saga chain.
                    # add_episode signature: saga: str | SagaNode | None
                    "saga": self.simulation_id,
                }

                # Thread the previous episode UUID for ordered saga traversal
                if self._last_episode_uuid is not None:
                    kwargs["saga_previous_episode_uuid"] = self._last_episode_uuid

                result = run_async(graphiti.add_episode(**kwargs))

                # Store episode UUID for the next episode's saga_previous_episode_uuid
                try:
                    self._last_episode_uuid = result.episode.uuid
                except AttributeError:
                    logger.debug("Could not extract episode UUID from result for saga chaining")

                logger.debug(
                    f"Wrote episode {episode_name} ({activity_count} activities), "
                    f"saga={self.simulation_id[:8]}, "
                    f"prev_uuid={kwargs.get('saga_previous_episode_uuid', 'none')}"
                )
                break
            except Exception as exc:
                delay = 2 ** attempt
                logger.warning(
                    f"Episode write failed (attempt {attempt + 1}): {exc}. Retry in {delay}s"
                )
                time.sleep(delay)


class GraphitiMemoryManager:
    """Creates and tracks GraphitiMemoryUpdater instances per simulation."""

    _updaters: dict[str, "GraphitiMemoryUpdater"] = {}
    _lock = threading.Lock()

    @classmethod
    def create_updater(cls, group_id: str, simulation_id: str) -> "GraphitiMemoryUpdater":
        with cls._lock:
            if simulation_id in cls._updaters:
                return cls._updaters[simulation_id]
            updater = GraphitiMemoryUpdater(group_id, simulation_id)
            updater.start()
            cls._updaters[simulation_id] = updater
            return updater

    @classmethod
    def stop_updater(cls, simulation_id: str):
        with cls._lock:
            updater = cls._updaters.pop(simulation_id, None)
        if updater:
            updater.stop()
