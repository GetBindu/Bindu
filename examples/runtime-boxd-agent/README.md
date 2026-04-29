# runtime-boxd-agent

A bindu agent that runs as a real microservice inside a [boxd](https://boxd.sh)
microVM — own machine, own IP, own HTTPS domain, own DID. The script body is
a vanilla echo agent; the magic is the `runtime={"provider": "boxd"}` block.

```python
bindufy(
    config,
    handler,
    runtime={
        "provider": "boxd",
        "auto_suspend": 60,
        "on_exit": "suspend",
    },
)
```

## Run

```bash
# 1. Install bindu and the boxd SDK
pip install bindu

# Until the boxd Python SDK is on PyPI, install editably from a local checkout:
pip install -e ~/boxd/sdk/python

# 2. Authenticate
boxd login           # browser flow; or set BOXD_TOKEN directly
export BOXD_TOKEN=$(jq -r .token ~/.config/boxd/credentials.json)

# 3. Deploy
python agent.py
```

You should see:

```
✓ runtime-boxd-example serving at https://runtime-boxd-example.boxd.sh

[runtime-boxd-example] INFO: Started server process [...]
[runtime-boxd-example] INFO: Application startup complete.
```

In another terminal:

```bash
curl https://runtime-boxd-example.boxd.sh/health
curl https://runtime-boxd-example.boxd.sh/.well-known/agent.json
```

Ctrl-C the deploy terminal — boxd auto-suspends the VM after 60s of inactivity.
Re-run `python agent.py` to resume (~1 second warm).

## What just happened

1. The host bindu (your laptop / dev VM) packaged this directory into a tarball.
2. It created a boxd VM named `runtime-boxd-example` (or reused an existing one
   with that name).
3. It uploaded the tarball, ran `pip install bindu` + `pip install -e .` inside
   the VM.
4. It exec'd `python3 agent.py` inside the VM, where `bindufy()` sees no
   `runtime=` (because that's a host-side param) and runs the standard
   in-process server on port 3773.
5. Boxd's proxy routes public HTTPS traffic to the agent's port.
6. The host streams VM logs to your terminal until you Ctrl-C.

## See also

- `docs/runtime/README.md` — overview of the runtime-provider abstraction.
- `docs/runtime/boxd.md` — full config reference (vcpu, memory, on_exit modes,
  etc.).
- `docs/runtime/custom-image.md` — A1 mode (deploy from a pre-built Docker image
  instead of shipping source).
