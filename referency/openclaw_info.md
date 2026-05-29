https://openclaw.ai/, https://docs.openclaw.ai/clawhub
https://docs.openclaw.ai/concepts/architecture, 

"OpenClaw

    Documentation Index

    Fetch the complete documentation index at: https://docs.openclaw.ai/llms.txt

    Use this file to discover all available pages before exploring further.

OpenClaw

    “EXFOLIATE! EXFOLIATE!” — A space lobster, probably 

Any OS gateway for AI agents across Discord, Google Chat, iMessage, Matrix, Microsoft Teams, Signal, Slack, Telegram, WhatsApp, Zalo, and more.
Send a message, get an agent response from your pocket. Run one Gateway across built-in channels, bundled channel plugins, WebChat, and mobile nodes.",
"Overview
Chat channels

    Documentation Index

    Fetch the complete documentation index at: https://docs.openclaw.ai/llms.txt

    Use this file to discover all available pages before exploring further.

OpenClaw can talk to you on any chat app you already use. Each channel connects via the Gateway. Text is supported everywhere; media and reactions vary by channel." ,"Fundamentals
Gateway architecture

    Documentation Index

    Fetch the complete documentation index at: https://docs.openclaw.ai/llms.txt

    Use this file to discover all available pages before exploring further.

​
Overview

    A single long-lived Gateway owns all messaging surfaces (WhatsApp via Baileys, Telegram via grammY, Slack, Discord, Signal, iMessage, WebChat).
    Control-plane clients (macOS app, CLI, web UI, automations) connect to the Gateway over WebSocket on the configured bind host (default 127.0.0.1:18789).
    Nodes (macOS/iOS/Android/headless) also connect over WebSocket, but declare role: node with explicit caps/commands.
    One Gateway per host; it is the only place that opens a WhatsApp session.
    The canvas host is served by the Gateway HTTP server under:
        /__openclaw__/canvas/ (agent-editable HTML/CSS/JS)
        /__openclaw__/a2ui/ (A2UI host) It uses the same port as the Gateway (default 18789).

​
Components and flows
​
Gateway (daemon)

    Maintains provider connections.
    Exposes a typed WS API (requests, responses, server-push events).
    Validates inbound frames against JSON Schema.
    Emits events like agent, chat, presence, health, heartbeat, cron.

​
Clients (mac app / CLI / web admin)

    One WS connection per client.
    Send requests (health, status, send, agent, system-presence).
    Subscribe to events (tick, agent, presence, shutdown).

​" and "Overview
Tools and plugins

    Documentation Index

    Fetch the complete documentation index at: https://docs.openclaw.ai/llms.txt

    Use this file to discover all available pages before exploring further.

Everything the agent does beyond generating text happens through tools. Tools are how the agent reads files, runs commands, browses the web, sends messages, and interacts with devices.
​
Tools, skills, and plugins
OpenClaw has three layers that work together:
1

Tools are what the agent calls
A tool is a typed function the agent can invoke (e.g. exec, browser, web_search, message). OpenClaw ships a set of built-in tools and plugins can register additional ones.The agent sees tools as structured function definitions sent to the model API.
2

Skills teach the agent when and how
A skill is a markdown file (SKILL.md) injected into the system prompt. Skills give the agent context, constraints, and step-by-step guidance for using tools effectively. Skills live in your workspace, in shared folders, or ship inside plugins.Skills reference | Creating skills
3

Plugins package everything together
A plugin is a package that can register any combination of capabilities: channels, model providers, tools, skills, speech, realtime transcription, realtime voice, media understanding, image generation, video generation, web fetch, web search, and more. Some plugins are core (shipped with OpenClaw), others are external (published on npm by the community).Install and configure plugins | Build your own
​
Built-in tools
These tools ship with OpenClaw and are available without installing any plugins:
Tool	What it does	Page
exec / process	Run shell commands, manage background processes	Exec, Exec Approvals
code_execution	Run sandboxed remote Python analysis	Code Execution
browser	Control a Chromium browser (navigate, click, screenshot)	Browser
web_search / x_search / web_fetch	Search the web, search X posts, fetch page content	Web, Web Fetch
read / write / edit	File I/O in the workspace	
apply_patch	Multi-hunk file patches	Apply Patch
message	Send messages across all channels	Agent Send
nodes	Discover and target paired devices	
cron / gateway	Manage scheduled jobs; inspect, patch, restart, or update the gateway	
image / image_generate	Analyze or generate images	Image Generation
music_generate	Generate music tracks	Music Generation
video_generate	Generate videos	Video Generation
tts	One-shot text-to-speech conversion	TTS
sessions_* / subagents / agents_list	Session management, status, and sub-agent orchestration	Sub-agents
session_status	Lightweight /status-style readback and session model override	Session Tools
For image work, use image for analysis and image_generate for generation or editing. If you target openai/*, google/*, fal/*, or another non-default image provider, configure that provider’s auth/API key first. For music work, use music_generate. If you target google/*, minimax/*, or another non-default music provider, configure that provider’s auth/API key first. For video work, use video_generate. If you target qwen/* or another non-default video provider, configure that provider’s auth/API key first. For workflow-driven audio generation, use music_generate when a plugin such as ComfyUI registers it. This is separate from tts, which is text-to-speech. session_status is the lightweight status/readback tool in the sessions group. It answers /status-style questions about the current session and can optionally set a per-session model override; model=default clears that override. Like /status, it can backfill sparse token/cache counters and the active runtime model label from the latest transcript usage entry. gateway is the owner-only runtime tool for gateway operations:

    config.schema.lookup for one path-scoped config subtree before edits
    config.get for the current config snapshot + hash
    config.patch for partial config updates with restart
    config.apply only for full-config replacement
    update.run for explicit self-update + restart

For partial changes, prefer config.schema.lookup then config.patch. Use config.apply only when you intentionally replace the entire config. For broader config docs, read Configuration and Configuration reference. The tool also refuses to change tools.exec.ask or tools.exec.security; legacy tools.bash.* aliases normalize to the same protected exec paths.
​
Plugin-provided tools
Plugins can register additional tools. Some examples:

    Canvas — experimental bundled plugin for node Canvas control and A2UI rendering
    Diffs — diff viewer and renderer
    LLM Task — JSON-only LLM step for structured output
    Lobster — typed workflow runtime with resumable approvals
    Music Generation — shared music_generate tool with workflow-backed providers
    OpenProse — markdown-first workflow orchestration
    Tokenjuice — compact noisy exec and bash tool results

Plugin tools are still authored with api.registerTool(...) and declared in the plugin manifest’s contracts.tools list. OpenClaw captures the validated tool descriptor during discovery and caches it by plugin source and contract, so later tool planning can skip plugin runtime loading. Tool execution still loads the owning plugin and calls the live registered implementation. Tool Search is the compact surface for large catalogs. Instead of putting every OpenClaw, MCP, or client tool schema into the prompt, OpenClaw can give the model an isolated Node runtime with openclaw.tools.search, openclaw.tools.describe, and openclaw.tools.call. Calls still flow back through the Gateway, so tool policy, approvals, hooks, and session logs remain authoritative."
and "Full command tree

openclaw [--dev] [--profile <name>] <command>
  crestodian
  setup
  onboard
  configure
  config
    get
    set
    unset
    file
    schema
    validate
  completion
  doctor
  dashboard
  backup
    create
    verify
  security
    audit
  secrets
    reload
    audit
    configure
    apply
  reset
  uninstall
  update
    wizard
    status
  channels
    list
    status
    capabilities
    resolve
    logs
    add
    remove
    login
    logout
  directory
    self
    peers list
    groups list|members
  skills
    search
    install
    update
    list
    info
    check
  plugins
    list
    inspect
    install
    uninstall
    update
    enable
    disable
    doctor
    marketplace list
  memory
    status
    index
    search
  path
    resolve
    find
    set
    validate
    emit
  commitments
    list
    dismiss
  wiki
    status
    doctor
    init
    ingest
    compile
    lint
    search
    get
    apply
    bridge import
    unsafe-local import
    obsidian status|search|open|command|daily
  message
    send
    broadcast
    poll
    react
    reactions
    read
    edit
    delete
    pin
    unpin
    pins
    permissions
    search
    thread create|list|reply
    emoji list|upload
    sticker send|upload
    role info|add|remove
    channel info|list
    member info
    voice status
    event list|create
    timeout
    kick
    ban
  agent
  agents
    list
    add
    delete
    bindings
    bind
    unbind
    set-identity
  acp
  mcp
    serve
    list
    show
    set
    unset
  status
  health
  sessions
    cleanup
  tasks
    list
    audit
    maintenance
    show
    notify
    cancel
    flow list|show|cancel
  gateway
    call
    usage-cost
    health
    status
    probe
    discover
    install
    uninstall
    start
    stop
    restart
    run
  daemon
    status
    install
    uninstall
    start
    stop
    restart
  logs
  system
    event
    heartbeat last|enable|disable
    presence
  models
    list
    status
    set
    set-image
    aliases list|add|remove
    fallbacks list|add|remove|clear
    image-fallbacks list|add|remove|clear
    scan
  infer (alias: capability)
    list
    inspect
    model run|list|inspect|providers|auth login|logout|status
    image generate|edit|describe|describe-many|providers
    audio transcribe|providers
    tts convert|voices|providers|status|enable|disable|set-provider
    video generate|describe|providers
    web search|fetch|providers
    embedding create|providers
    auth add|login|login-github-copilot|setup-token|paste-token
    auth order get|set|clear
  sandbox
    list
    recreate
    explain
  cron
    status
    list
    add
    edit
    rm
    enable
    disable
    runs
    run
  nodes
    status
    describe
    list
    pending
    approve
    reject
    rename
    invoke
    notify
    push
    canvas snapshot|present|hide|navigate|eval
    canvas a2ui push|reset
    camera list|snap|clip
    screen record
    location get
  devices
    list
    remove
    clear
    approve
    reject
    rotate
    revoke
  node
    run
    status
    install
    uninstall
    stop
    restart
  approvals
    get
    set
    allowlist add|remove
  exec-policy
    show
    preset
    set
  browser
    status
    start
    stop
    reset-profile
    tabs
    open
    focus
    close
    profiles
    create-profile
    delete-profile
    screenshot
    snapshot
    navigate
    resize
    click
    type
    press
    hover
    drag
    select
    upload
    fill
    dialog
    wait
    evaluate
    console
    pdf
  hooks
    list
    info
    check
    enable
    disable
    install
    update
  webhooks
    gmail setup|run
  proxy
    start
    run
    coverage
    sessions
    query
    blob
    purge
  pairing
    list
    approve
  qr
  clawbot
    qr
  docs
  dns
    setup
  tui
  chat (alias: tui --local)
  terminal (alias: tui --local)

Plugins can add additional top-level commands (for example openclaw voicecall).
​
Chat slash commands
Chat messages support /... commands. See slash commands. Highlights:

    /status — quick diagnostics.
    /trace — session-scoped plugin trace/debug lines.
    /config — persisted config changes.
    /debug — runtime-only config overrides (memory, not disk; requires commands.debug: true).

​
Usage tracking
openclaw status --usage and the Control UI surface provider usage/quota when OAuth/API credentials are available. Data comes directly from provider usage endpoints and is normalized to X% left. Providers with current usage windows: Anthropic, GitHub Copilot, Gemini CLI, OpenAI Codex, MiniMax, Xiaomi, and z.ai. See Usage tracking for details."