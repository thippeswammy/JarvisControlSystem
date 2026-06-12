The diagnostic results significantly narrow down the root cause of the native C++ startup failure.
`
### Diagnostic Findings

A dedicated utility (`scratch/diagnose_winrt.py`) was created and executed to validate the WinRT activation chain independently from `UIAutomationServer.exe`.

Output:

```text
[*] Loading DLL via ctypes...
[+] DLL loaded successfully!

[*] Locating DllGetActivationFactory export...
[+] Found DllGetActivationFactory export!

[*] Setting up WinRT HSTRING helper APIs...
[+] RoInitialize returned HRESULT: 0x00000000

[*] Creating WinRT HSTRING for class:
    'Microsoft.UI.UIAutomation.AutomationRemoteOperation'...
[+] HSTRING created successfully!

[*] Invoking DllGetActivationFactory...
[+] DllGetActivationFactory returned HRESULT: 0x00000000

[+] SUCCESS! Class factory resolved successfully.
    Registration-Free WinRT activation is functioning correctly.
```

### What This Confirms

The test successfully validates several critical assumptions:

#### 1. The Registration-Free WinRT Manifest Works

The side-by-side (SxS) manifest configuration is being loaded correctly by Windows. Namespace declarations, activation metadata, and factory mappings are all resolving as expected.

#### 2. The DLL Itself Is Healthy

`Microsoft.UI.UIAutomation.dll` loads correctly and exposes a functioning `DllGetActivationFactory` export.

#### 3. WinRT Activation Is Functional

After calling `RoInitialize`, the runtime successfully creates an activation factory for:

```cpp
Microsoft.UI.UIAutomation.AutomationRemoteOperation
```

This proves the underlying WinRT component can be activated successfully outside of the crashing executable.

### Implication

The failure is no longer likely to be:

* Manifest configuration
* Missing WinRT registration
* Missing DLL dependencies
* Broken UI Automation WinRT component
* OS-level activation restrictions

Those paths have effectively been ruled out.

### Why Does `UIAutomationServer.exe` Still Crash?

The remaining evidence points toward an early initialization failure occurring inside the executable itself.

The observed crash:

```text
Exit Code: 3221226505
0xC0000409 (STATUS_STACK_BUFFER_OVERRUN)
```

combined with the crash offset indicates that execution likely fails before the application's main entry point begins normal operation.

A common cause in C++/WinRT applications is premature use of WinRT projections during static initialization.

For example:

```cpp
static SomeWinRTObject g_object;
```

or

```cpp
static auto factory =
    winrt::get_activation_factory<...>();
```

These constructs execute before `main()` runs.

If any WinRT projection code executes before apartment initialization via:

```cpp
winrt::init_apartment();
```

or

```cpp
RoInitialize();
```

the runtime may trigger a fail-fast termination rather than returning a recoverable error.

### Current Working Hypothesis

The evidence strongly suggests that `UIAutomationServer.exe` contains one or more:

* Global objects
* Static class instances
* Namespace-scope variables
* Static initialization blocks

that indirectly touch WinRT APIs before apartment initialization has occurred.

The activation infrastructure itself appears healthy; the crash is most likely occurring during executable startup rather than during WinRT component activation.

### Research Directions

To isolate the issue, focus investigation on:

1. Global/static variables in `UIAutomationServer.exe`
2. Constructors executed before `main()`
3. Calls to:

   * `winrt::get_activation_factory`
   * `winrt::make`
   * `AutomationRemoteOperation`
   * Any WinRT projected type
4. CRT startup sequence (`mainCRTStartup`)
5. Static initialization order issues across translation units

### Recommended Next Step

Attach a native debugger and break on first-chance exceptions before process termination:

```bat
windbg UIAutomationServer.exe
```

Then enable:

```text
sxe av
sxe eh
sxe ibp
```

and run:

```text
g
```

Capturing the first faulting stack trace should reveal the exact constructor or startup routine triggering the fail-fast before the application reaches its normal initialization path.
