// tcp-config WebUI logic.
// KernelSU WebUI is the only control channel: kernelsu.exec() runs apply.sh /
// status commands with the trusted local privilege boundary. There is no
// browser/TCP fallback because a socket cannot authenticate the Android caller.
// Built with esbuild; the output goes to webroot/index.js.
import { exec } from 'kernelsu';

const MODROOT = '/data/adb/modules/tcp-config';
const ALGORITHMS = new Set(['cubic', 'bbr', 'kerneldflt']);
const QDISCS = new Set(['fq', 'fq_codel', 'pfifo_fast']);

function requireKsuBridge() {
  if (typeof ksu === 'undefined') {
    throw new Error('KernelSU WebUI bridge is unavailable');
  }
}

export async function getStatus() {
  requireKsuBridge();
  const { stdout } = await exec(
    'sysctl -n net.ipv4.tcp_congestion_control; sysctl -n net.core.default_qdisc; ' +
    'zcat /proc/config.gz 2>/dev/null | grep -oE \'^CONFIG_DEFAULT_TCP_CONG="[^"]*"\' | cut -d\'"\' -f2; ' +
    'sed -n "s/^ALGO=//p; s/^QDISC=//p" /data/adb/tcpcfg.state 2>/dev/null'
  );
  const lines = stdout.trim().split('\n');
  return { algo: lines[0] || '', qdisc: lines[1] || '', dflt: lines[2] || 'unknown', state_algo: lines[3] || '', state_qdisc: lines[4] || '' };
}

export async function apply(algo, qdisc) {
  requireKsuBridge();
  if (!ALGORITHMS.has(algo)) return { ok: false, error: 'invalid algorithm' };
  if (!QDISCS.has(qdisc)) return { ok: false, error: 'invalid qdisc' };
  const { errno, stdout, stderr } = await exec(`sh ${MODROOT}/webroot/apply.sh '${algo}' '${qdisc}'`);
  if (errno !== 0) return { ok: false, error: stderr || ('exec failed: ' + errno) };
  try { return JSON.parse(stdout); } catch { return { ok: false, error: stdout }; }
}
