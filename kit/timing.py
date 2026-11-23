# timing.py — 곡에서 가사 줄마다 시작 시간을 찾아 meme.json의 dur 값과 BGM_SS를 알려 준다.
# 사용: python3 timing.py <곡.mp3> dog|cat
# 필요: pip install faster-whisper (힉스필드 샌드박스에는 이미 있음)
# 원리: 음성 인식으로 단어별 시간을 얻고, 각 줄의 첫 단어(아래 KEYS)가 처음 나오는 시간을 줄 시작으로 본다.
import sys, re
from faster_whisper import WhisperModel

KEYS = {
    "dog": ["cool", "sleep", "dinner", "grooming", "walks", "human"],
    "cat": ["chic", "sleep", "dinner", "self", "spot", "human"],
}
# 2026-11-23 실측 보정: 인식기가 chic을 cheek으로 듣는다. 그리고 각 줄의 첫 단어("I'm", "This", "But")가
# 키워드보다 먼저 나오므로, 키워드를 찾은 뒤 같은 줄의 앞 단어(최대 2단어, 0.8초 이내)로 시작을 당긴다.
ALIAS = {"chic": ("chic", "cheek", "sheik"), "cool": ("cool",), "human": ("human",)}
LEAD = {"cool": ("im", "a"), "chic": ("im", "a"), "spot": ("this",), "human": ("but", "my")}
song, kind = sys.argv[1], sys.argv[2]
keys = KEYS[kind]
m = WhisperModel("small", compute_type="int8")
segs, _ = m.transcribe(song, language="en", word_timestamps=True, vad_filter=False)
words = [(re.sub(r"[^a-z]", "", w.word.lower()), round(w.start, 2)) for s in segs for w in s.words]
print("인식된 단어:", " ".join(f"{w}@{t}" for w, t in words))

starts, k, last = [], 0, -1.0
for i, (w, t) in enumerate(words):
    if k < len(keys) and any(w.startswith(a) for a in ALIAS.get(keys[k], (keys[k],))) and t > last:
        st = t
        for j in range(i - 1, max(-1, i - 3), -1):  # 같은 줄 앞 단어로 당기기
            pw, pt = words[j]
            if pw in LEAD.get(keys[k], ()) and t - pt <= 0.8 and pt > last: st = pt
            else: break
        starts.append(st); last = t; k += 1
if len(starts) < len(keys):
    print(f"\n줄 시작을 {len(starts)}/{len(keys)}개만 찾았습니다. 위 단어 목록을 보고 직접 정하세요.")
    sys.exit(1)

# 줄 시작보다 0.15초 앞에서 컷을 바꾼다(가사보다 화면이 살짝 먼저 바뀌어야 자연스럽다)
cuts = [max(0, round(t - 0.15, 2)) for t in starts]
ss = cuts[0]
import subprocess
total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", song],
                             capture_output=True, text=True).stdout)
ends = cuts[1:] + [min(total, cuts[-1] + 4.0)]     # 마지막 장면은 최대 4초
durs = [round(e - c, 2) for c, e in zip(cuts, ends)]
print("\nBGM_SS =", ss)
print("dur =", durs, " (합계", round(sum(durs), 2), "초)")
for i, d in enumerate(durs, 1):
    flag = "" if 2.0 <= d <= 4.5 else "  ← 2~4초 범위 밖, 귀로 확인 필요"
    print(f"  장면 {i}: {d}초{flag}")
