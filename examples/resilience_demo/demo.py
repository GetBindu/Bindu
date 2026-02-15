"""Demo: Production-Ready Agent with Circuit Breaker and Rate Limiting

This demo shows how to use circuit breakers and rate limiters to build
resilient, production-grade AI agents with Bindu.

Features demonstrated:
1. Circuit breaker for agent-to-agent communication
2. Rate limiting for request throttling
3. Monitoring and metrics collection
4. Auto-recovery from failures
"""

import asyncio
import random
from bindu.utils.circuit_breaker import CircuitBreaker, CircuitBreakerRegistry
from bindu.utils.rate_limiter import (
    TokenBucketRateLimiter,
    SlidingWindowRateLimiter,
    AdaptiveRateLimiter,
    RateLimiterRegistry,
    RateLimitExceeded,
)


# ============================================================================
# Demo 1: Basic Circuit Breaker Usage
# ============================================================================


async def unreliable_agent_call(fail_rate: float = 0.3):
    """Simulates calling an unreliable agent."""
    await asyncio.sleep(0.1)  # Simulate network delay
    if random.random() < fail_rate:
        raise Exception("Agent communication failed")
    return {"status": "success", "data": "Agent response"}


async def demo_basic_circuit_breaker():
    """Demo: Protect agent calls with circuit breaker."""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Circuit Breaker Protection")
    print("=" * 70)

    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=5.0,
        name="agent_communication",
    )

    # Make some calls
    for i in range(10):
        try:
            async with breaker:
                result = await unreliable_agent_call(fail_rate=0.6)
                print(f"✅ Call {i+1}: Success - {result['status']}")
        except Exception as e:
            print(f"❌ Call {i+1}: Failed - {type(e).__name__}: {e}")

        # Show circuit state
        status = breaker.get_status()
        print(f"   Circuit: {status['state'].upper()}, "
              f"Failures: {status['failure_count']}/{breaker.failure_threshold}")

        await asyncio.sleep(0.5)

    # Show final metrics
    print("\n📊 Final Metrics:")
    metrics = breaker.metrics.to_dict()
    print(f"   Total Requests: {metrics['total_requests']}")
    print(f"   Successful: {metrics['successful_requests']}")
    print(f"   Failed: {metrics['failed_requests']}")
    print(f"   Rejected: {metrics['rejected_requests']}")
    print(f"   Success Rate: {metrics['success_rate']}%")


# ============================================================================
# Demo 2: Rate Limiting for Agent Requests
# ============================================================================


async def demo_rate_limiting():
    """Demo: Rate limit agent requests."""
    print("\n" + "=" * 70)
    print("DEMO 2: Rate Limiting Agent Requests")
    print("=" * 70)

    limiter = TokenBucketRateLimiter(
        rate=10,  # 10 requests per second
        per_seconds=1.0,
        burst_size=5,  # Allow burst of 5
        name="agent_requests",
    )

    print(f"Rate: {limiter.rate} req/s, Burst: {limiter.burst_size}")
    print("\nMaking 20 rapid requests...\n")

    for i in range(20):
        try:
            async with limiter:
                print(f"✅ Request {i+1}: Allowed")
                await asyncio.sleep(0.05)  # Simulate work
        except RateLimitExceeded as e:
            print(f"⏱️  Request {i+1}: Rate limited - {e}")

    # Show status
    print("\n📊 Rate Limiter Status:")
    status = limiter.get_status()
    print(f"   Accepted: {status['accepted_requests']}")
    print(f"   Rejected: {status['rejected_requests']}")
    print(f"   Acceptance Rate: {status['acceptance_rate']}%")


# ============================================================================
# Demo 3: Adaptive Rate Limiting
# ============================================================================


async def demo_adaptive_rate_limiting():
    """Demo: Adaptive rate limiter adjusts to system load."""
    print("\n" + "=" * 70)
    print("DEMO 3: Adaptive Rate Limiting")
    print("=" * 70)

    limiter = AdaptiveRateLimiter(
        base_rate=10,
        min_rate=3,
        max_rate=20,
        window_seconds=2.0,
        error_threshold=0.3,  # 30% errors trigger reduction
        name="adaptive_agent",
    )

    print(f"Base: {limiter.base_rate} req/s, Range: [{limiter.min_rate}, {limiter.max_rate}]")
    print("\nPhase 1: High error rate (should reduce limit)...")

    # High error rate phase
    for i in range(15):
        try:
            async with limiter:
                if random.random() < 0.5:  # 50% error rate
                    raise Exception("High load error")
                await asyncio.sleep(0.05)
        except (RateLimitExceeded, Exception) as e:
            pass

    await asyncio.sleep(2.5)  # Wait for adjustment

    status = limiter.get_status()
    print(f"   Current rate after high errors: {status['current_rate']} req/s")

    print("\nPhase 2: Low error rate (should increase limit)...")

    # Low error rate phase
    for i in range(15):
        try:
            async with limiter:
                if random.random() < 0.05:  # 5% error rate
                    raise Exception("Rare error")
                await asyncio.sleep(0.05)
        except (RateLimitExceeded, Exception):
            pass

    await asyncio.sleep(2.5)

    status = limiter.get_status()
    print(f"   Current rate after low errors: {status['current_rate']} req/s")


# ============================================================================
# Demo 4: Multi-Agent System with Registry
# ============================================================================


async def demo_multi_agent_registry():
    """Demo: Managing multiple agents with registries."""
    print("\n" + "=" * 70)
    print("DEMO 4: Multi-Agent System with Registries")
    print("=" * 70)

    # Create registries
    breaker_registry = CircuitBreakerRegistry()
    limiter_registry = RateLimiterRegistry()

    # Setup for 3 different agents
    agents = ["research_agent", "data_agent", "summarizer_agent"]

    for agent in agents:
        breaker_registry.get_or_create(agent, failure_threshold=3)
        limiter_registry.create_token_bucket(
            agent, rate=20, per_seconds=1.0, burst_size=10
        )

    print(f"Registered {len(agents)} agents\n")

    # Simulate traffic to different agents
    for _ in range(10):
        agent = random.choice(agents)
        breaker = breaker_registry.get(agent)
        limiter = limiter_registry.get(agent)

        try:
            async with limiter:
                async with breaker:
                    await unreliable_agent_call(fail_rate=0.2)
                    print(f"✅ {agent}: Request successful")
        except Exception as e:
            print(f"❌ {agent}: {type(e).__name__}")

        await asyncio.sleep(0.1)

    # Show all statuses
    print("\n📊 Circuit Breaker Status:")
    for name, status in breaker_registry.get_all_statuses().items():
        print(f"   {name}: {status['state'].upper()}, "
              f"Success rate: {status['metrics']['success_rate']}%")

    print("\n📊 Rate Limiter Status:")
    for name, status in limiter_registry.get_all_statuses().items():
        print(f"   {name}: {status['accepted_requests']} accepted, "
              f"{status['rejected_requests']} rejected")


# ============================================================================
# Demo 5: Real-World Integration Example
# ============================================================================


class ResilientAgent:
    """Example agent with built-in resilience."""

    def __init__(self, name: str):
        self.name = name
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            name=f"{name}_circuit",
        )
        self.rate_limiter = TokenBucketRateLimiter(
            rate=100,
            per_seconds=60,
            burst_size=20,
            name=f"{name}_rate",
        )

    async def send_message(self, message: str):
        """Send message with circuit breaker and rate limiting."""
        try:
            async with self.rate_limiter:
                async with self.circuit_breaker:
                    # Simulate agent communication
                    return await unreliable_agent_call(fail_rate=0.1)
        except RateLimitExceeded as e:
            return {"error": "rate_limited", "retry_after": e.retry_after}
        except Exception as e:
            return {"error": "circuit_breaker", "message": str(e)}

    def get_health(self):
        """Get agent health metrics."""
        breaker_status = self.circuit_breaker.get_status()
        limiter_status = self.rate_limiter.get_status()

        return {
            "name": self.name,
            "circuit_breaker": {
                "state": breaker_status["state"],
                "success_rate": breaker_status["metrics"]["success_rate"],
            },
            "rate_limiter": {
                "acceptance_rate": limiter_status["acceptance_rate"],
                "available_tokens": limiter_status["available_tokens"],
            },
        }


async def demo_resilient_agent():
    """Demo: Production-ready agent with all features."""
    print("\n" + "=" * 70)
    print("DEMO 5: Production-Ready Resilient Agent")
    print("=" * 70)

    agent = ResilientAgent("production_agent")

    print("Simulating production workload...\n")

    success_count = 0
    failure_count = 0

    # Simulate production traffic
    for i in range(30):
        result = await agent.send_message(f"Request {i+1}")

        if "error" in result:
            failure_count += 1
            print(f"❌ Request {i+1}: {result['error']}")
        else:
            success_count += 1
            print(f"✅ Request {i+1}: Success")

        # Show health every 10 requests
        if (i + 1) % 10 == 0:
            health = agent.get_health()
            print(f"\n💊 Health Check:")
            print(f"   Circuit: {health['circuit_breaker']['state'].upper()}")
            print(
                f"   Success Rate: {health['circuit_breaker']['success_rate']:.1f}%"
            )
            print(
                f"   Rate Limit: {health['rate_limiter']['acceptance_rate']:.1f}% acceptance"
            )
            print()

        await asyncio.sleep(0.1)

    print(f"\n📊 Final Results:")
    print(f"   Total Requests: {success_count + failure_count}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {failure_count}")


# ============================================================================
# Main Demo Runner
# ============================================================================


async def run_all_demos():
    """Run all demos."""
    print("\n")
    print("🌟" * 35)
    print("  BINDU: Production-Grade Agent Resilience Demo")
    print("🌟" * 35)

    await demo_basic_circuit_breaker()
    await demo_rate_limiting()
    await demo_adaptive_rate_limiting()
    await demo_multi_agent_registry()
    await demo_resilient_agent()

    print("\n" + "=" * 70)
    print("✅ All demos completed!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Integrate circuit breakers into your Bindu agents")
    print("2. Configure rate limits based on your needs")
    print("3. Monitor metrics in production")
    print("4. Adjust thresholds based on observed behavior")
    print()


if __name__ == "__main__":
    asyncio.run(run_all_demos())
