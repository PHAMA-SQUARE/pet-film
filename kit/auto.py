#!/usr/bin/env python3
# auto.py — 신청 1건을 릴스로 만든다 (힉스필드 샌드박스 ~/kit 에서).
# 사용: python3 auto.py <신청id> <A|B> <아이이름> [ss1,ss2,...,ss6]
#   1) petfilm-sign 함수로 1시간짜리 링크를 받아 slot-1..6.mp4 를 jobs/<id>/ 에 내려받는다 (토큰은 환경변수 PETFILM_TOKEN)
#   2) 빠진 칸은 다른 영상의 뒷부분으로 채우고, 장면 길이보다 짧은 영상은 반복해 늘린다
#   3) templates/<A|B>.json 으로 meme.json 을 쓰고 meme.js → meme.sh 로 out.mp4, strip.jpg 를 만든다
import json, os, subprocess, sys, urllib.request
KIT = os.path.dirname(os.path.abspath(__file__))
aid, kind, pet = sys.argv[1], sys.argv[2], sys.argv[3]
ssin = [float(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else None
D = os.path.join(KIT, 'jobs', aid); os.makedirs(D, exist_ok=True)
req = urllib.request.Request('https://ypeqsbmuuedzdzxkuuoj.supabase.co/functions/v1/petfilm-sign', data=json.dumps({'id': aid}).encode(),
      headers={'x-petfilm-token': os.environ['PETFILM_TOKEN'], 'Content-Type': 'application/json'})
for u in json.load(urllib.request.urlopen(req))['urls']:
    fn = os.path.join(D, os.path.basename(u['path']))
    if not os.path.exists(fn): urllib.request.urlretrieve(u['url'], fn)
def dur(f): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]).decode().strip() or 0)
T = json.load(open(os.path.join(KIT, 'templates', kind + '.json'), encoding='utf-8'))
have = [i for i in range(1, 7) if os.path.exists(os.path.join(D, f'slot-{i}.mp4'))]
if 6 not in have: sys.exit('6번(보호자와 함께) 영상이 없어요')
clips = []
for n in range(1, 7):
    need = T['dur'][n-1]
    src = n if n in have else max(have, key=lambda i: dur(os.path.join(D, f'slot-{i}.mp4')))
    f = f'slot-{src}.mp4'; L = dur(os.path.join(D, f))
    if src != n: ss = max(0.0, L - need - 0.3)          # 빠진 칸: 가장 긴 영상의 뒷부분
    elif ssin: ss = ssin[n-1]
    else: ss = max(0.0, min(1.0, L - need - 0.1))          # 기본: 1초 지점(손떨림 건너뛰기)
    if L - ss < need + 0.05:                                 # 짧으면 반복해서 늘린 사본
        g = f'slot-{n}-loop.mp4'
        subprocess.run(['ffmpeg','-v','error','-y','-stream_loop','3','-i',os.path.join(D,f),'-t',str(need+1),'-an','-c:v','libx264','-crf','18',os.path.join(D,g)], check=True)
        f, ss = g, 0
    clips.append({'file': f, 'ss': round(ss, 2), 'dur': need, 'from_slot': src})
J = {k: T[k] for k in ('type','caption_top','lines','mark','bgm_ss')}; J.update(pet=pet, clips=clips)
json.dump(J, open(os.path.join(D, 'meme.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
env = dict(os.environ, NODE_PATH=subprocess.check_output(['npm','root','-g']).decode().strip(), BGM=T['bgm'], BGM_SS=str(T['bgm_ss']))
subprocess.run(['node','meme.js','jobs/'+aid], cwd=KIT, env=env, check=True)
subprocess.run(['bash','meme.sh','jobs/'+aid], cwd=KIT, env=env, check=True)
print('missing slots:', [i for i in range(1,7) if i not in have])
print('done', os.path.join(D,'out.mp4'), os.path.join(D,'strip.jpg'))
