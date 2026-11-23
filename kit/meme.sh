#!/bin/bash
# meme.sh — A·B안 자기소개 밈 영상(약 20초)을 합친다.  사용: bash meme.sh jobs/<신청번호>
# 입력: jobs/<신청번호>/meme.json, 장면 영상 6개(meme.json의 clips), M/cap_1..6.png (meme.js가 만든 것)
# 구성: 컷 n = 영상 n + 자막 n. 컷 길이는 clips[n].dur(초) — 곡의 가사 n번째 줄이 시작해서 다음 줄이 시작할 때까지.
# 배경음악: BGM=<파일> BGM_SS=<첫 가사가 나오는 초> bash meme.sh ...  (지정하지 않으면 무음)
set -e
D="${1:?jobs/<신청번호> 폴더를 지정하세요}"
mapfile -t CL < <(python3 -c "
import json;j=json.load(open('$D/meme.json'))
for c in j['clips']: print(c['file'], c.get('ss',0), c['dur'])")
N=${#CL[@]}
NC=$(ls "$D"/M/cap_*.png | wc -l)
[ "$N" -eq "$NC" ] || { echo "clips($N)와 자막 그림($NC) 수가 다릅니다. meme.js를 다시 돌리세요"; exit 1; }
TOT=$(python3 -c "import json;print(round(sum(c['dur'] for c in json.load(open('$D/meme.json'))['clips']),2))")
IN=""; for c in "${CL[@]}"; do set -- $c; IN="$IN -ss $2 -i $D/$1"; done
for n in $(seq 1 $N); do IN="$IN -framerate 30 -loop 1 -t 10 -i $D/M/cap_$n.png"; done
if [ -n "$BGM" ]; then AUD="-ss ${BGM_SS:-0} -t $TOT -i $BGM"; else AUD="-f lavfi -t $TOT -i anullsrc=r=44100:cl=stereo"; fi
V="scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=30,format=yuv420p"
FC=""; CAT=""
for i in $(seq 0 $((N-1))); do
  set -- ${CL[$i]}; DUR=$3
  FC="$FC[$i:v]$V,tpad=stop_mode=clone:stop_duration=$DUR,trim=0:$DUR,setpts=PTS-STARTPTS[v$i];[$((i+N)):v]format=rgba,trim=0:$DUR,setpts=PTS-STARTPTS[c$i];[v$i][c$i]overlay,format=yuv420p[k$i];"
  CAT="$CAT[k$i]"
done
FC="$FC${CAT}concat=n=$N:v=1:a=0,fade=t=out:st=$(python3 -c "print(round($TOT-0.5,2))"):d=0.5[v];"
FC="$FC[$((2*N)):a]afade=t=in:d=0.05,afade=t=out:st=$(python3 -c "print(round($TOT-0.8,2))"):d=0.8[a]"
ffmpeg -v error -y $IN $AUD -filter_complex "$FC" -map "[v]" -map "[a]" -t $TOT \
  -c:v libx264 -preset veryfast -crf 21 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart "$D/out.mp4"
# 검수용 모음(컷마다 가운데 한 장)과 표지
python3 - "$D" <<'E'
import json,subprocess,sys
d=sys.argv[1]; t=0; outs=[]
for i,c in enumerate(json.load(open(d+'/meme.json'))['clips']):
    m=t+c['dur']/2; t+=c['dur']; o=f"{d}/q_{i}.jpg"; outs.append(o)
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(m),'-i',d+'/out.mp4','-frames:v','1','-vf','scale=180:-1',o],check=True)
subprocess.run(['montage',*outs,'-tile',f'{len(outs)}x1','-geometry','+2+2',d+'/strip.jpg'],check=True)
for o in outs: subprocess.run(['rm','-f',o])
E
ffmpeg -v error -y -ss 1 -i "$D/out.mp4" -frames:v 1 -q:v 3 "$D/cover.jpg"
echo "완료 → $D/out.mp4 (${TOT}초), 검수 $D/strip.jpg, 표지 $D/cover.jpg"
