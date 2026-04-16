#!/usr/bin/env python3
"""Test script for pause/resume functionality."""

import time
import uuid
import requests

BASE_URL = "http://localhost:3773"


def make_request(method: str, params: dict) -> dict:
    """Make an A2A request."""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params,
    }
    response = requests.post(
        BASE_URL, json=payload, headers={"Content-Type": "application/json"}
    )
    return response.json()


def send_message(text: str, blocking: bool = True) -> str:
    """Send a message and return task_id."""
    task_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    context_id = str(uuid.uuid4())

    params = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "messageId": message_id,
            "contextId": context_id,
            "taskId": task_id,
            "kind": "message",
        },
        "configuration": {
            "acceptedOutputModes": ["text/plain"],
            "blocking": blocking,
        },
    }

    result = make_request("message/send", params)

    if "error" in result:
        print(f"❌ Error sending message: {result['error']}")
        return None

    return result["result"]["id"]


def get_task(task_id: str) -> dict:
    """Get task status."""
    result = make_request("tasks/get", {"taskId": task_id})

    if "error" in result:
        print(f"❌ Error getting task: {result['error']}")
        return None

    return result["result"]


def pause_task(task_id: str) -> dict:
    """Pause a task."""
    result = make_request("tasks/pause", {"taskId": task_id})

    if "error" in result:
        print(f"❌ Error pausing task: {result['error']}")
        return None

    return result["result"]


def resume_task(task_id: str) -> dict:
    """Resume a task."""
    result = make_request("tasks/resume", {"taskId": task_id})

    if "error" in result:
        print(f"❌ Error resuming task: {result['error']}")
        return None

    return result["result"]


def test_pause_working_task():
    """Test pausing a task in working state - with polling."""
    print("\n" + "=" * 50)
    print("TEST: Pause task in 'working' state (with polling)")
    print("=" * 50)

    # Send message
    print("\n1. Sending message...")
    task_id = send_message("test", blocking=False)

    if not task_id:
        return False

    print(f"   Task ID: {task_id}")

    # Poll for "working" state
    print("\n2. Polling for 'working' state...")
    for i in range(10):  # Try 10 times
        time.sleep(0.3)  # Wait 300ms between checks
        task = get_task(task_id)
        if task:
            state = task["status"]["state"]
            print(f"   Attempt {i + 1}: state = {state}")
            if state == "working":
                # Found it! Now try to pause
                print("\n3. Found 'working' state! Attempting to pause...")
                result = pause_task(task_id)
                if result:
                    # Now wait for state to actually change to suspended
                    print("   Waiting for state to change to 'suspended'...")
                    for j in range(10):
                        time.sleep(0.2)
                        task = get_task(task_id)
                        if task:
                            new_state = task["status"]["state"]
                            if new_state == "suspended":
                                print(f"   ✅ Pause successful! State: {new_state}")
                                return True
                            elif new_state == "completed":
                                print("   Task completed before pause took effect")
                                return False
                    print(
                        f"   ⚠️  Pause returned but state is: {task['status']['state']}"
                    )
                    return False
                else:
                    print("   ❌ Pause failed")
                    return False
            elif state == "completed":
                print("   Task already completed, too late!")
                break

    print("   ❌ Could not catch task in 'working' state")
    return False


def test_pause_completed_task():
    """Test pausing a task in completed state - should fail."""
    print("\n" + "=" * 50)
    print("TEST: Pause task in 'completed' state (should fail)")
    print("=" * 50)

    # Send message - it will complete on its own
    print("\n1. Sending message...")
    task_id = send_message("hello", blocking=False)

    if not task_id:
        return False

    print(f"   Task ID: {task_id}")

    # Wait for completion (the async sleep is only 2 seconds)
    print("   Waiting for task to complete...")
    for i in range(10):
        time.sleep(0.5)
        task = get_task(task_id)
        if task:
            state = task["status"]["state"]
            if state == "completed":
                print(f"   Task completed! State: {state}")
                break
            print(f"   Waiting... state = {state}")

    # Check task status
    task = get_task(task_id)
    if not task:
        return False

    state = task["status"]["state"]
    print(f"   Current state: {state}")

    # Try to pause - should fail (task is completed)
    print("\n2. Attempting to pause (should fail)...")
    result = pause_task(task_id)

    if result is None:
        print("   ✅ Correctly rejected! TaskNotPausableError")
        return True
    else:
        print(f"   ❌ Should have failed but got: {result}")
        return False


def test_resume_suspended_task():
    """Test resuming a task in suspended state - with polling."""
    print("\n" + "=" * 50)
    print("TEST: Resume task in 'suspended' state (with polling)")
    print("=" * 50)

    # Send message
    print("\n1. Sending message...")
    task_id = send_message("test", blocking=False)

    if not task_id:
        return False

    print(f"   Task ID: {task_id}")

    # Poll for "working" state, then pause
    print("\n2. Polling for 'working' state to pause...")
    paused = False
    for i in range(10):
        time.sleep(0.3)
        task = get_task(task_id)
        if task:
            state = task["status"]["state"]
            print(f"   Attempt {i + 1}: state = {state}")
            if state == "working":
                # Try to pause
                pause_result = pause_task(task_id)
                # Wait for state to actually become suspended
                for j in range(10):
                    time.sleep(0.2)
                    task = get_task(task_id)
                    if task and task["status"]["state"] == "suspended":
                        print(f"   ✅ Paused! State: {task['status']['state']}")
                        paused = True
                        break
                if paused:
                    break
                print(f"   Pause result: {pause_result}")
            elif state == "completed":
                print("   Task completed before we could pause")
                break

    if not paused:
        print("   ❌ Could not pause task")
        return False

    # Now resume
    print("\n3. Resuming task...")
    resume_result = resume_task(task_id)

    if resume_result:
        print(f"   ✅ Resume successful! State: {resume_result['status']['state']}")
        return True
    else:
        print("   ❌ Resume failed")
        return False


def test_resume_working_task():
    """Test resuming a task in working state - should fail."""
    print("\n" + "=" * 50)
    print("TEST: Resume task in 'working' state (should fail)")
    print("=" * 50)

    # Send non-blocking message
    print("\n1. Sending message (non-blocking)...")
    task_id = send_message("sleep 3", blocking=False)

    if not task_id:
        return False

    print(f"   Task ID: {task_id}")

    # Give it time to start
    time.sleep(0.5)

    # Check state
    task = get_task(task_id)
    state = task["status"]["state"]
    print(f"   Current state: {state}")

    # Try to resume - should fail (not suspended)
    print("\n2. Attempting to resume (should fail)...")
    result = resume_task(task_id)

    if result is None:
        print("   ✅ Correctly rejected! TaskNotResumableError")
        return True
    else:
        print(f"   ❌ Should have failed but got: {result}")
        return False


def main():
    print("🧪 Testing Pause/Resume Functionality")
    print("=" * 50)
    print(f"Server: {BASE_URL}")
    print("Make sure the agent is running first!")
    print("=" * 50)

    results = []

    # Run tests with delays to let worker finish previous tasks
    results.append(("Pause working task", test_pause_working_task()))
    time.sleep(3)  # Wait for task to complete
    results.append(("Pause completed task (should fail)", test_pause_completed_task()))
    time.sleep(3)  # Wait for task to complete
    results.append(("Resume suspended task", test_resume_suspended_task()))
    time.sleep(3)  # Wait for task to complete
    results.append(("Resume working task (should fail)", test_resume_working_task()))

    # Summary
    print("\n" + "=" * 50)
    print("📊 RESULTS")
    print("=" * 50)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")


if __name__ == "__main__":
    main()
