"""Echo agent fixture for the boxd_e2e test.

Runs *inside* the boxd VM during e2e. Not invoked by the host directly.
"""
from bindu.penguin.bindufy import bindufy


def handler(messages):
    if not messages:
        return "no message"
    return [
        {
            "role": "assistant",
            "content": messages[-1].get("content", ""),
        }
    ]


config = {
    "author": "e2e@azin.run",
    "name": "boxd-e2e-echo",
    "description": "echo agent for e2e",
    "deployment": {"url": "http://localhost:3773"},
}

if __name__ == "__main__":
    bindufy(config, handler)
