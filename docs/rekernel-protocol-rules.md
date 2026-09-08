# Re:Kernel protocol definition (v1)

This is the kernel-side wire definition established by T13. It describes the
interface expected from a future NoActive-compatible userspace; no such
userspace is present in the Ace6 workspace.

## Transport

The kernel creates one raw netlink socket in `init_net`, selecting the first
available protocol unit in the inclusive/exclusive range `22..25`. The chosen
unit is exposed as the decimal filename `/proc/rekernel/<unit>`. A userspace
receiver must bind an `AF_NETLINK` socket for that unit to port ID `100`.
Events are kernel-to-userspace unicast messages; the kernel does not consume a
response protocol.

The source identity is `ace6-rekernel-kv/v1`, represented by
`REKERNEL_PROTOCOL_VERSION 1`. The payload is not NUL-terminated and is at
most 127 bytes. It is comma-separated `key=value` text terminated by `;`.
Formatting that would require 128 bytes or more is rejected/dropped rather
than silently truncated.

## Event schemas

Binder events use:

```text
type=Binder,bindertype=<reply|transaction|free_buffer_full>,oneway=<0|1>,from_pid=<pid>,from=<uid>,target_pid=<pid>,target=<uid>;
```

Signal events use:

```text
type=Signal,signal=<number>,killer_pid=<pid>,killer=<uid>,dst_pid=<pid>,dst=<uid>;
```

`killer_*` always describe `current`, and `dst_*` describe the signal target
`p`. Binder `from_*` describes the sending Binder process and `target_*` the
target process. The exact field names and event names are part of v1.

## Compatibility boundary

No NoActive implementation, receiver, or pinned userspace commit matching this
definition was found in the workspace during T13. The kernel-side definition
is recorded and statically checked. Userspace compatibility, receiver startup,
event handling and recovery remain unverified. T26 must use a named
NoActive/userspace version and capture both receiver and kernel logs before the
profile can be considered for any non-experimental status.
