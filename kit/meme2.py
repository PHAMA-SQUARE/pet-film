#!/usr/bin/env python3
# meme2.py — 노래 가사에 맞춘 자기소개 밈 릴스를 합친다.  사용: python3 meme2.py jobs/<신청번호>
# 먼저 node meme.js jobs/<신청번호> 로 자막 그림(M/cap_1..N.png)을 만든다.
# meme.json:
#   "clips":    [{"file":"1.mp4","ss":0}, ... 5개]      보호자 영상 (칸 순서)
#   "bgm":      "bgm/cat_chic.mp3"                       키트 폴더 기준 음원
#   "total":    22.8                                     영상 전체 길이(= 음원 길이)
#   "timeline": [{"t":0,"clip":1,"cap":1}, {"t":2.16,"clip":2,"cap":2}, ...]
#       t    이 장면이 시작하는 초(가사 시작에 맞춘다). 다음 장면의 t까지 이어진다
#       clip 쓸 영상 번호(1~5). 같은 영상을 이어서 쓰면 앞에서 쓴 만큼 뒤부터 이어 붙는다
#       cap  띄울 자막 번호(lines의 순서, 1부터). 0이면 자막 없음
#       ss   (선택) 이 장면에서 영상을 시작할 초. 넣으면 이어 붙이지 않고 여기서 시작
# 결과: out.mp4(720x1280, 30fps), strip.jpg(장면별 검수), cover.jpg
import json, os, subprocess, sys

D = sys.argv[1]
KIT = os.path.dirname(os.path.abspath(__file__))
J = json.load(open(os.path.join(D, 'meme.json'), encoding='utf-8'))
TL = J['timeline']; TOT = float(J['total'])
clips = J['clips']
V = "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=30,format=yuv420p"

used = {}  # 영상별로 이미 쓴 초
args, fc, segs = [], [], []
for i, s in enumerate(TL):
    t0 = float(s['t']); t1 = float(TL[i + 1]['t']) if i + 1 < len(TL) else TOT
    dur = round(t1 - t0, 3); c = int(s['clip'])
    base = float(clips[c - 1].get('ss', 0))
    ss = float(s['ss']) if 'ss' in s else base + used.get(c, 0.0)
    used[c] = (ss - base) + dur
    segs.append((t0, dur))
    args += ['-ss', str(ss), '-t', str(dur + 0.5), '-i', os.path.join(D, clips[c - 1]['file'])]
cap_in = {}
for i, s in enumerate(TL):
    k = int(s.get('cap', 0))
    if k and k not in cap_in:
        cap_in[k] = len(args) // 2  # 입력 번호는 아래에서 다시 센다
n_vid = len(TL)
cap_idx = {}
for k in sorted(cap_in):
    cap_idx[k] = n_vid + len(cap_idx)
    args += ['-framerate', '30', '-loop', '1', '-t', str(TOT), '-i', os.path.join(D, 'M', f'cap_{k}.png')]
a_idx = n_vid + len(cap_idx)
args += ['-t', str(TOT), '-i', os.path.join(KIT, J['bgm'])] if J.get('bgm') else ['-f', 'lavfi', '-t', str(TOT), '-i', 'anullsrc=r=44100:cl=stereo']

# 같은 자막 그림을 여러 장면에 쓰면 split
uses = {}
for s in TL:
    k = int(s.get('cap', 0))
    if k: uses[k] = uses.get(k, 0) + 1
lab = {}
for k, n in uses.items():
    if n == 1: lab[k] = [f'[{cap_idx[k]}:v]']
    else:
        outs = ''.join(f'[cs{k}_{j}]' for j in range(n))
        fc.append(f'[{cap_idx[k]}:v]split={n}{outs}')
        lab[k] = [f'[cs{k}_{j}]' for j in range(n)]
for i, s in enumerate(TL):
    dur = segs[i][1]
    fc.append(f'[{i}:v]{V},tpad=stop_mode=clone:stop_duration={dur},trim=0:{dur},setpts=PTS-STARTPTS[v{i}]')
    k = int(s.get('cap', 0))
    if k:
        src = lab[k].pop(0)
        fc.append(f'{src}format=rgba,trim=0:{dur},setpts=PTS-STARTPTS,fade=in:st=0:d=0.12:alpha=1[c{i}]')
        fc.append(f'[v{i}][c{i}]overlay=eof_action=pass,format=yuv420p[k{i}]')
    else:
        fc.append(f'[v{i}]null[k{i}]')
fo = 0.6
fc.append(''.join(f'[k{i}]' for i in range(n_vid)) + f'concat=n={n_vid}:v=1:a=0,fade=t=out:st={round(TOT-fo,2)}:d={fo}[v]')
fc.append(f'[{a_idx}:a]afade=t=out:st={round(TOT-0.8,2)}:d=0.8[a]')
out = os.path.join(D, 'out.mp4')
cmd = ['ffmpeg', '-v', 'error', '-y', *args, '-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]', '-t', str(TOT),
       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', out]
subprocess.run(cmd, check=True)

# 검수용 모음과 표지
qs = []
for i, (t0, dur) in enumerate(segs):
    q = os.path.join(D, f'q_{i:02d}.jpg'); qs.append(q)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(round(t0 + min(dur / 2, dur - 0.1), 2)), '-i', out, '-frames:v', '1', '-vf', 'scale=180:-1', q], check=True)
subprocess.run(['montage', *qs, '-tile', f'{len(qs)}x1', '-geometry', '+2+2', os.path.join(D, 'strip.jpg')], check=True)
for q in qs: os.remove(q)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(round(segs[0][1] / 2, 2)), '-i', out, '-frames:v', '1', '-q:v', '3', os.path.join(D, 'cover.jpg')], check=True)
print(f'완료 → {out} ({TOT}초, 장면 {n_vid}개), 검수 {D}/strip.jpg')
