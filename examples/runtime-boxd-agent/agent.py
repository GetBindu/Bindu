"""Bindu agent that runs as a real microservice in a boxd microVM.

The script's body is a vanilla bindu echo agent — what makes it a
"runtime-boxd" example is the ``runtime={"provider": "boxd"}`` block
in ``bindufy()``. That tells bindu: don't run me locally, ship my
source to a fresh boxd VM, install bindu + my deps inside it, and
start the agent there. After deploy, the host process supervises
(streams VM logs to stdout, handles Ctrl-C); A2A clients talk
directly to the public URL printed at startup.

Usage:
    pip install bindu boxd                  # boxd: not on PyPI yet
    pip install -e ~/boxd/sdk/python        # for now, install editable
    export BOXD_TOKEN=$(boxd login --json | jq -r .token)
    python agent.py

After ``✓ runtime-boxd-example serving at https://...``, hit it::

    curl https://runtime-boxd-example.boxd.sh/health
    curl https://runtime-boxd-example.boxd.sh/.well-known/agent.json

Ctrl-C detaches; the VM auto-suspends after 60s of inactivity. Re-run
this script to resume in ~1s.

See ``docs/runtime/`` for the full runtime-provider documentation.
"""

from bindu.penguin.bindufy import bindufy


def handler(messages: list[dict[str, str]]):
    """Echo the latest user message back."""
    if not messages:
        return "send a message"
    return [
        {
            "role": "assistant",
            "content": messages[-1].get("content", ""),
        }
    ]


config = {
    "author": "you@example.com",
    "name": "runtime-boxd-example",
    "description": "Echo agent running inside a boxd microVM.",
    "deployment": {
        # The agent inside the VM binds 0.0.0.0:3773 so the boxd proxy can
        # reach it. The host injects BINDU_PUBLIC_URL automatically.
        "url": "http://0.0.0.0:3773",
        "expose": True,
    },
}


if __name__ == "__main__":
    bindufy(
        config,
        handler,
        runtime={
            "provider": "boxd",
            "auto_suspend": 60,  # seconds idle before VM auto-suspends
            "on_exit": "suspend",  # Ctrl-C detaches; re-run resumes
        },
    )
