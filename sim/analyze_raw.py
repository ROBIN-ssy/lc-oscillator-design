import struct, sys

path = sys.argv[1]
target = sys.argv[2] if len(sys.argv) > 2 else None

data = open(path, 'rb').read()
marker = 'Binary:\n'.encode('utf-16-le')
idx = data.find(marker)
header = data[:idx].decode('utf-16-le', 'replace')
body = data[idx + len(marker):]

nvars = npoints = None
invars = False
varnames = []
for ln in header.split('\n'):
    s = ln.strip()
    if s.startswith('No. Variables:'):
        nvars = int(s.split(':')[1])
    elif s.startswith('No. Points:'):
        npoints = int(s.split(':')[1].strip())
    elif s.startswith('Variables:'):
        invars = True
    elif invars and s:
        p = [x for x in s.split('\t') if x.strip()]
        if len(p) >= 2:
            varnames.append(p[1].strip())

per = len(body) / npoints / nvars
all_double = per >= 7.5

times = []
cols = {n: [] for n in varnames}
pos = 0
for _ in range(npoints):
    times.append(struct.unpack_from('<d', body, pos)[0]); pos += 8
    for j in range(1, nvars):
        if all_double:
            v = struct.unpack_from('<d', body, pos)[0]; pos += 8
        else:
            v = struct.unpack_from('<f', body, pos)[0]; pos += 4
        cols[varnames[j]].append(v)

tn = times[-1]
start = tn * 0.8
tail = [(i, t) for i, t in enumerate(times) if t >= start]

print(f'终点 {tn*1e3:.3f} ms, 变量 {nvars} 个\n')

def amp_and_freq(name):
    ys = [cols[name][i] for i, _ in tail]
    ts = [t for _, t in tail]
    amp = (max(ys) - min(ys)) / 2
    mean = sum(ys) / len(ys)
    cr = []
    for k in range(1, len(ys)):
        a, b = ys[k-1] - mean, ys[k] - mean
        if a < 0 <= b:
            t0, v0 = ts[k-1], ys[k-1]
            t1, v1 = ts[k], ys[k]
            if v1 != v0:
                cr.append(t0 + (t1 - t0) * (0 - v0) / (v1 - v0))
    f = None
    if len(cr) >= 3:
        period = (cr[-1] - cr[0]) / (len(cr) - 1)
        if period > 0:
            f = 1 / period
    return amp, mean, f, len(cr)

if target:
    amp, mean, f, n = amp_and_freq(target)
    print(f'{target}: 幅度 {amp*1000:.2f} mV, 均值 {mean:.3f} V', end='')
    print(f', 频率 {f/1e6:.4f} MHz' if f else ', 无明显周期')
else:
    rows = []
    for n in varnames[1:]:
        amp, mean, f, nc = amp_and_freq(n)
        rows.append((amp, n, mean, f))
    rows.sort(reverse=True)
    print('按末尾 20% 段的交流幅度排序（前 12 个）:')
    print(f'{"变量":<14}{"幅度(mV)":>12}{"直流(V)":>10}{"频率":>14}')
    for amp, n, mean, f in rows[:12]:
        fs = f'{f/1e6:.4f} MHz' if f else '—'
        print(f'{n:<14}{amp*1000:12.2f}{mean:10.3f}{fs:>14}')
