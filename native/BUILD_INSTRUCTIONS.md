# Native C++ UIA Server Build Instructions (Visual Studio 2019)

This document provides step-by-step instructions for compiling the high-performance native C++ Windows UI Automation (UIA) server that bridges Jarvis with OS-level UI elements.

## Prerequisites

- **Operating System:** Windows 10 or Windows 11
- **IDE:** Visual Studio 2019 (Community, Professional, or Enterprise)
- **C++ Build Tools:**
  - MSVC v142 - VS 2019 C++ x64/x86 build tools (v14.29 or compatible)
  - Windows 10 SDK (10.0.19041.0 or higher)
- **Windows UI Automation Library:**
  - The C++ project integrates with standard `UIAutomationCore.dll` and supports **UIA Remote Operations**.

---

## Build Steps

1. **Open the Solution in Visual Studio 2019:**
   - Launch Visual Studio 2019.
   - Open the solution file located at:  
     `native/Microsoft-UI-UIAutomation/src/UIAutomation/UIAutomation.sln`

2. **Configure the Solution Platforms:**
   - Set the active build configuration to **Release**.
   - Set the active platform target to **x64** (UIA requires matching OS architecture; x64 is standard for 64-bit Windows systems).

3. **Verify Toolset Configuration:**
   - Right-click on the `UIAutomationServer` project in the Solution Explorer, select **Properties**.
   - Under **Configuration Properties > General**, verify:
     - **Platform Toolset:** `Visual Studio 2019 (v142)`
     - **Windows SDK Version:** `10.0.19041.0` (or similar installed SDK)

4. **Build the Solution:**
   - Go to the top menu and select **Build > Build Solution** (or press `Ctrl+Shift+B`).
   - The compiled executable will be generated at:  
     `native/Microsoft-UI-UIAutomation/src/UIAutomation/x64/Release/UIAutomationServer.exe`

---

## Registration and Integration

### On-Demand Registration (ODR)

The C++ server integrates with Windows ODR for service location:
- Run `odr.exe list` from a terminal to verify if the server executable registers correctly. => it on hold for now.
- The `uia_config.yaml` file is pre-configured to point to the output path above.

### Remote Operations & COM Fallback

- The server is optimized to use **UIA Remote Operations** (over Windows 11 / Windows 10 SDK) to minimize cross-process context switching overhead.
- If Remote Operations are unsupported on the host OS version, the server automatically switches to **Classic COM Fallback Mode**, ensuring 100% reliability across all supported Windows environments.
