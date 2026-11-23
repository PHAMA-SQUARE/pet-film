#!/bin/bash
# meme.sh — A·B안 자기소개 밈 영상(약 17초)을 합친다.  사용: bash meme.sh jobs/<신청번호>
# 입력: jobs/<신청번호>/meme.json, 보호자 영상 5개(meme.json의 clips), M/cap_1..7.png (meme.js가 만든 것)
# 구성: 컷1~5 = 영상1~5에 자막1~5 (각 CUT초) / 컷6 = 영상(last_clip)에 자막6("그런데…") 1.4초 뒤 자막7(반전)로 바뀜
# 배경음악: BGM=<파일> [BGM_SS=<시작 초>] bash meme.sh ...  (지정하지 않으면 무음)
# 2026-11-23 개정: M/l_bg.png(편지 엔딩)가 있으면 반전 컷 뒤에 7.5초 편지 엔딩을 붙인다(약 24.7초). 원본은 meme.v2doc.sh
set -e
D="${1:?jobs/<신청번호> 폴더를 지정하세요}"
CUT=$(python3 -c "import json;print(json.load(open('$D/meme.json')).get('cut',2.6))")
LAST=$(python3 -c "import json;print(json.load(open('$D/meme.json')).get('last_clip',2))")
END=4.2
mapfile -t CL < <(python3 -c "
import json;j=json.load(open('$D/meme.json'))
for c in j['clips']: print(c['file'], c.get('ss',0))")
[ ${#CL[@]} -eq 5 ] || { echo "clips는 5개여야 합니다"; exit 1; }
LF=$(echo ${CL[$((LAST-1))]} | cut -d' ' -f1); LS=$(echo ${CL[$((LAST-1))]} | cut -d' ' -f2)
# 영상 입력 5개 + 마지막 컷용 1개. 짧은 영상은 마지막 프레임을 늘려 채운다
IN=""; for c in "${CL[@]}"; do f=$(echo $c | cut -d' ' -f1); s=$(echo $c | cut -d' ' -f2); IN="$IN -ss $s -i $D/$f"; done
IN="$IN -ss $LS -i $D/$LF"
for n in 1 2 3 4 5 6 7; do IN="$IN -framerate 30 -loop 1 -t 5 -i $D/M/cap_$n.png"; done
NL=$(ls "$D"/M/l_[0-9]*.png 2>/dev/null | wc -l); LET=0; [ -f "$D/M/l_bg.png" ] && LET=7.5
TOT=$(python3 -c "print(round($CUT*5+$END+$LET,2))"); SEG=$(python3 -c "print(round($END+$LET,2))")
if [ -n "$BGM" ]; then AUD="-ss ${BGM_SS:-0} -t $TOT -i $BGM"; else AUD="-f lavfi -t $TOT -i anullsrc=r=44100:cl=stereo"; fi
V="scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=30,format=yuv420p"
FC=""
for i in 0 1 2 3 4; do
  FC="$FC[$i:v]$V,tpad=stop_mode=clone:stop_duration=$CUT,trim=0:$CUT,setpts=PTS-STARTPTS[v$i];[$((i+6)):v]format=rgba,trim=0:$CUT,setpts=PTS-STARTPTS[c$i];[v$i][c$i]overlay,format=yuv420p[k$i];"
done
FC="$FC[5:v]$V,tpad=stop_mode=clone:stop_duration=$SEG,trim=0:$SEG,setpts=PTS-STARTPTS[v5];"
FC="$FC[11:v]format=rgba,trim=0:1.4,setpts=PTS-STARTPTS[c5];[12:v]format=rgba,trim=0:$END,fade=in:st=1.4:d=0.15:alpha=1,setpts=PTS-STARTPTS[c6];"
FC="$FC[v5][c5]overlay=enable='lt(t,1.4)'[w5];[w5][c6]overlay=eof_action=pass,format=yuv420p[k5];"
if [ "$LET" != "0" ]; then
  # 편지 엔딩: 화면이 멈춘 채 어두워지고(0.8초), 편지 줄이 1.2초 간격으로, 이어 서명과 끝 표기가 떠오른다
  LIN="-framerate 30 -loop 1 -t $SEG -i $D/M/l_bg.png"; k=14; L="[k5]"; n=0
  FC="$FC[$k:v]format=rgba,fade=in:st=$END:d=0.8:alpha=1[lb];$L[lb]overlay=eof_action=pass[m$n];"; L="[m$n]"
  for f in $(ls "$D"/M/l_[0-9]*.png | sort -V) "$D/M/l_sign.png" "$D/M/l_end.png"; do
    k=$((k+1)); n=$((n+1)); LIN="$LIN -framerate 30 -loop 1 -t $SEG -i $f"
    # 편지 줄: 0.9초부터 1.1초 간격 / 서명: 마지막 줄 1.3초 뒤 / 끝 표기: 서명 1초 뒤
    st=$(python3 -c "n=$n;N=$NL;print(round($END+0.9+1.1*min(n-1,N)+(0.2 if n>N else 0)+(1.0 if n==N+2 else 0),2))")
    FC="$FC[$k:v]format=rgba,fade=in:st=$st:d=0.7:alpha=1[o$n];$L[o$n]overlay=eof_action=pass[m$n];"; L="[m$n]"
  done
  FC="${FC}${L}format=yuv420p[k5x];"
fi
K5="[k5]"; FO=0.5; [ "$LET" != "0" ] && K5="[k5x]" && FO=0.8
FC="$FC[k0][k1][k2][k3][k4]${K5}concat=n=6:v=1:a=0,fade=t=out:st=$(python3 -c "print(round($TOT-$FO,2))"):d=$FO[v];"
FC="$FC[13:a]afade=t=in:d=0.3,afade=t=out:st=$(python3 -c "print(round($TOT-1,2))"):d=1[a]"
ffmpeg -v error -y $IN $AUD $LIN -filter_complex "$FC" -map "[v]" -map "[a]" -t $TOT \
  -c:v libx264 -preset veryfast -crf 21 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart "$D/out.mp4"
# 검수용 모음과 표지
i=0; for t in $(python3 -c "c=$CUT;L=$LET;print(' '.join(str(round(c*k+c/2,2)) for k in range(5))+' '+str(round(c*5+0.7,2))+' '+str(round(c*5+3,2))+((' '+str(round(c*5+$END+5,2))+' '+str(round($TOT-1.2,2))) if L else ''))"); do
  ffmpeg -v error -y -ss $t -i "$D/out.mp4" -frames:v 1 -vf scale=180:-1 "$D/q_$i.jpg"; i=$((i+1)); done
montage $(ls "$D"/q_*.jpg | sort -V) -tile ${i}x1 -geometry +2+2 "$D/strip.jpg" && rm -f "$D"/q_*.jpg
ffmpeg -v error -y -ss $(python3 -c "print($CUT/2)") -i "$D/out.mp4" -frames:v 1 -q:v 3 "$D/cover.jpg"
echo "완료 → $D/out.mp4 (${TOT}초), 검수 $D/strip.jpg, 표지 $D/cover.jpg"
