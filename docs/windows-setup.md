# Windows Setup & Troubleshooting

This document captures Windows-specific issues that contributors may encounter
while setting up Bindu locally. It is based on real setup attempts and observed
errors during local development.

The goal of this document is to reduce confusion and panic when setup does not
work on the first attempt.

---

“If setup feels frustrating at first, that’s normal — Windows environments vary a lot, and the sections below reflect what has helped in practice.”

---

## Before you troubleshoot

If setup fails initially, pause before changing multiple things at once.
Most Windows-related issues are caused by Python version compatibility or
native dependency requirements rather than problems in Bindu itself.

Review the sections below before retrying installation.

---

## Environment context (example)

The following issues were encountered under these conditions:

- Operating System: Windows 11
- Python versions tried: 3.10, then 3.12+
- Shell: VS Code integrated terminal / PowerShell
- Environment manager: uv

Behavior may vary depending on system configuration.

---

## Common issues

### 1. Python version incompatibility

Observed behavior:

- Dependency installation fails
- `uv sync` does not complete successfully

Likely cause:
Some dependencies require Python 3.12 or newer. Older versions such as 3.10
may fail during dependency resolution or wheel installation.

What helped:

- Installing Python 3.12+
- Recreating the virtual environment using the newer Python version

---

### 2. Failed building wheel for native dependencies

Observed behavior:
Failed building wheel for `ed25519-blake2b`

Likely cause:
Certain cryptographic dependencies require native compilation on Windows.
Prebuilt wheels may not be available for all Python and platform combinations.

What helped:

- Using Python 3.12+
- Deleting and recreating the virtual environment
- Retrying dependency installation

On some systems, installing Microsoft C++ Build Tools may also help.

---

### 3. `uv sync` hanging or exiting without clear output

Observed behavior:

- `uv sync --dev` appears stuck
- Command exits with no useful error message

Possible causes:

- Network-related delays
- Dependency resolution conflicts
- Incompatible Python version

What helped:

- Verifying the active Python version
- Removing the existing `.venv` directory
- Recreating the environment and retrying the command

---

### 4. Virtual environment not being used correctly

Observed behavior:

- Imports fail despite successful installation
- Commands behave differently across terminals

Likely cause:
The virtual environment is not activated or multiple Python installations
exist on the system.

What helped:

- Activating the virtual environment explicitly:
  `.venv\Scripts\activate`
- Verifying the Python path:
  `where python`

---

## Notes

- These issues are environment-specific and not indicative of problems in
  Bindu’s core implementation.
- Windows setups can vary significantly across systems.
- Contributors may need to experiment slightly to find a compatible setup.
- If additional Windows-specific issues are encountered, consider documenting
  them to help future contributors.
