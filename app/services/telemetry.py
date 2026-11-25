from dataclasses import asdict, dataclass


@dataclass
class AgentTelemetry:
    chat_requests: int = 0
    guardrail_blocks: int = 0
    llm_calls: int = 0
    llm_fallbacks: int = 0
    llm_errors: int = 0
    total_chat_latency_ms: float = 0.0

    def record_chat(self, latency_ms: float) -> None:
        self.chat_requests += 1
        self.total_chat_latency_ms += latency_ms

    def record_guardrail_block(self) -> None:
        self.guardrail_blocks += 1

    def record_llm_call(self) -> None:
        self.llm_calls += 1

    def record_llm_fallback(self) -> None:
        self.llm_fallbacks += 1

    def record_llm_error(self) -> None:
        self.llm_errors += 1

    def snapshot(self) -> dict:
        data = asdict(self)
        avg = self.total_chat_latency_ms / self.chat_requests if self.chat_requests else 0.0
        data["avg_chat_latency_ms"] = round(avg, 2)
        return data


telemetry = AgentTelemetry()
