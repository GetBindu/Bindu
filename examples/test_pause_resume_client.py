"""Client script for testing pause/resume operations with the test agent.

Usage:
    1. Start the agent: python examples/pause_resume_test_agent.py
    2. Run this client: python examples/test_pause_resume_client.py
"""

import asyncio
import uuid
import aiohttp
import time


class PauseResumeTestClient:
    """JSON-RPC client for testing pause/resume operations."""
    
    def __init__(self, base_url: str = "http://localhost:3776"):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
    
    async def _send_jsonrpc_request(self, method: str, params: dict) -> dict:
        """Send a JSON-RPC 2.0 request to the agent."""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(uuid.uuid4())
        }
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(self.base_url, json=request) as response:
                return await response.json()
    
    async def send_message(self, content: str, context_id: str = None) -> dict:
        """Send a message to start a task."""
        # Generate UUIDs for message components
        message_id = str(uuid.uuid4())
        if not context_id:
            context_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        
        # Build A2A protocol compliant message
        params = {
            "configuration": {
                "acceptedOutputModes": ["text"]
            },
            "message": {
                "messageId": message_id,
                "contextId": context_id,
                "taskId": task_id,
                "kind": "message",
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": content
                    }
                ]
            }
        }
        
        print(f"Sending message: '{content}'")
        response = await self._send_jsonrpc_request("message/send", params)
        
        if "result" in response:
            task = response["result"]
            
            # Handle both snake_case and camelCase responses
            task_id = task.get("id") or task.get("taskId")
            ctx_id = task.get("context_id") or task.get("contextId")
            
            if not task_id or not ctx_id:
                print(f"Error: Could not extract task/context IDs from response")
                return None
            
            print(f"Task started: {task_id}")
            return {
                "taskId": task_id,
                "contextId": ctx_id,
                "task": task
            }
        else:
            error = response.get("error", {})
            print(f"Error: {error.get('message', 'Unknown error')}")
            return None
    
    async def pause_task(self, task_id: str) -> dict:
        """Pause a running task."""
        print(f"Pausing task: {task_id}")
        response = await self._send_jsonrpc_request("tasks/pause", {"taskId": task_id})
        
        if "result" in response:
            result = response["result"]
            state = result.get("status", {}).get("state", "unknown")
            print(f"Task paused successfully (state: {state})")
            return result
        else:
            error_msg = response.get('error', {}).get('message', 'Unknown error')
            print(f"Pause failed: {error_msg}")
            return None
    
    async def resume_task(self, task_id: str) -> dict:
        """Resume a paused task."""
        print(f"Resuming task: {task_id}")
        response = await self._send_jsonrpc_request("tasks/resume", {"taskId": task_id})
        
        if "result" in response:
            result = response["result"]
            state = result.get("status", {}).get("state", "unknown")
            print(f"Task resumed successfully (state: {state})")
            return result
        else:
            error_msg = response.get('error', {}).get('message', 'Unknown error')
            print(f"Resume failed: {error_msg}")
            return None
    
    async def get_task(self, task_id: str) -> dict:
        """Get task status and history."""
        response = await self._send_jsonrpc_request("tasks/get", {"taskId": task_id})
        
        if "result" in response:
            return response["result"]
        else:
            return None


async def test_pause_resume_workflow():
    """Test the complete pause/resume workflow."""
    client = PauseResumeTestClient()
    
    print("=" * 70)
    print("PAUSE/RESUME TEST - Automated Workflow")
    print("=" * 70)
    
    # Step 1: Start a long task
    print("\nStep 1: Starting 20-step async task")
    result = await client.send_message("20")
    
    if not result:
        print("Failed to start task")
        return
    
    task_id = result["taskId"]
    
    # Step 2: Wait a bit, then pause
    print("\nStep 2: Waiting 5 seconds, then pausing...")
    await asyncio.sleep(5)
    
    pause_result = await client.pause_task(task_id)
    
    if not pause_result:
        print("Task may have already completed")
        return
    
    # Step 3: Check task while paused
    print("\nStep 3: Checking task status while paused...")
    paused_task = await client.get_task(task_id)
    if paused_task:
        state = paused_task.get("status", {}).get("state", "unknown")
        print(f"State: {state}")
        print(f"Messages: {len(paused_task.get('history', []))}")
        
        if state == "failed":
            print("Task failed instead of pausing - check agent logs")
            return
    
    # Step 4: Wait, then resume
    print("\nStep 4: Waiting 5 seconds before resuming...")
    await asyncio.sleep(5)
    
    resume_result = await client.resume_task(task_id)
    
    if not resume_result:
        print("Failed to resume task")
        return
    
    # Step 5: Wait for completion
    print("\nStep 5: Waiting for task to complete...")
    await asyncio.sleep(45)
    
    # Step 6: Check final result
    print("\nStep 6: Checking final task status...")
    final_task = await client.get_task(task_id)
    if final_task:
        state = final_task.get("status", {}).get("state", "unknown")
        print(f"\nFinal state: {state}")
        print(f"Total messages: {len(final_task.get('history', []))}")
    
    print("\n" + "=" * 70)
    print("Test completed successfully")
    print("=" * 70)


async def interactive_test():
    """Interactive test allowing manual control."""
    client = PauseResumeTestClient()
    
    print("=" * 70)
    print(" INTERACTIVE PAUSE/RESUME TEST")
    print("=" * 70)
    print("\nCommands:")
    print("  start <steps>  - Start a new task with N steps (default: 10)")
    print("  pause <taskId> - Pause a running task")
    print("  resume <taskId> - Resume a paused task")
    print("  status <taskId> - Check task status")
    print("  quit - Exit")
    print("=" * 70)
    
    while True:
        command = input("\n> ").strip().lower()
        
        if command == "quit":
            break
        
        parts = command.split()
        if not parts:
            continue
        
        try:
            if parts[0] == "start":
                steps = parts[1] if len(parts) > 1 else "10"
                result = await client.send_message(steps)
                if result:
                    print(f"\n  Save this task ID: {result['taskId']}")
            
            elif parts[0] == "pause" and len(parts) > 1:
                await client.pause_task(parts[1])
            
            elif parts[0] == "resume" and len(parts) > 1:
                await client.resume_task(parts[1])
            
            elif parts[0] == "status" and len(parts) > 1:
                task = await client.get_task(parts[1])
                if task:
                    print(f"\n  Task Status:")
                    print(f"   ID: {task['id']}")
                    print(f"   State: {task['state']}")
                    print(f"   Messages: {len(task.get('history', []))}")
                    if task.get('metadata', {}).get('paused_at'):
                        print(f"   Paused at: {task['metadata']['paused_at']}")
            
            else:
                print("Unknown command. Use: start, pause, resume, status, or quit")
        
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    print("\nSelect test mode:")
    print("1. Automated workflow test (recommended)")
    print("2. Interactive mode (manual control)")
    
    try:
        choice = input("\nChoice (1 or 2): ").strip()
        
        if choice == "1":
            asyncio.run(test_pause_resume_workflow())
        elif choice == "2":
            asyncio.run(interactive_test())
        else:
            print("Invalid choice. Running automated test...")
            asyncio.run(test_pause_resume_workflow())
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
