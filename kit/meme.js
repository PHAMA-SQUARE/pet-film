// meme.js — 강아지·고양이 자기소개 밈의 자막 그림과 편지 엔딩 그림을 만든다.  사용: node meme.js jobs/<신청번호>
// 입력: jobs/<신청번호>/meme.json   출력: jobs/<신청번호>/M/*.png (720x1280, 투명 배경)
// 자막: 한국어 큰 줄 + 영어 작은 줄(이탤릭) — A·B안 음악·가사 인수인계(2026-11-23)
// 디자인: 파마스퀘어 브랜드(SUIT, 흰 글자 + 끝 어절 민트, 상단 민트 선, 오른쪽 위 PHAMA SQUARE 로고). 2026-11-23 개정.
// 기획안 v2 원본은 meme.v2doc.js 에 그대로 두었다.
//   cap_1..7.png      밈 자막 7장
//   l_bg.png          편지 엔딩 바탕(어두운 틸 막)   l_1..l_n.png 편지 줄   l_sign.png 서명   l_end.png 끝 표기
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const dir = path.resolve(process.argv[2] || '.');
const J = JSON.parse(fs.readFileSync(path.join(dir, 'meme.json'), 'utf8'));
const FONTS = path.resolve(process.env.FONTS || path.join(__dirname, 'fonts'));
const ASSETS = path.resolve(path.join(__dirname, 'assets'));
const F = 'file://' + FONTS + '/';
const LOGO = 'data:image/png;base64,' + fs.readFileSync(path.join(ASSETS, 'logo_white.png')).toString('base64');
const TOP = J.caption_top || 860;   // 자막 첫 줄 위치(위에서 px). 브랜드 기준(1920 화면 y1310)을 720x1280에 맞춘 값. 얼굴을 가리면 바꾼다

const MINT = '#7FE3D2', MINT2 = '#CDF3EA';
const CSS = `
@font-face{font-family:S;src:url(${F}SUIT-Bold.ttf);font-weight:700}
@font-face{font-family:S;src:url(${F}SUIT-ExtraBold.ttf);font-weight:800}
@font-face{font-family:S;src:url(${F}SUIT-Medium.ttf);font-weight:500}
*{margin:0;box-sizing:border-box}
body{width:720px;height:1280px;position:relative;overflow:hidden;word-break:keep-all;background:transparent;font-family:S}
.shadow{text-shadow:0 2px 12px rgba(0,0,0,.5),0 0 2px rgba(0,0,0,.35)}
.line{position:absolute;left:64px;right:64px;top:170px;height:4px;border-radius:4px;background:${MINT};box-shadow:0 1px 6px rgba(0,0,0,.25)}
.logo{position:absolute;right:64px;top:192px;height:11px;filter:drop-shadow(0 1px 4px rgba(0,0,0,.5))}
.mark{position:absolute;left:64px;top:186px;font-weight:700;font-size:16px;letter-spacing:.02em;color:rgba(255,255,255,.9)}
.cap{position:absolute;left:64px;right:64px;top:${TOP}px;color:#FFFFFF}
.en{font-weight:700;font-size:22px;line-height:1.3;color:${MINT2};margin-top:8px;letter-spacing:.01em;font-style:italic}
.ko{font-weight:800;font-size:40px;line-height:1.4;letter-spacing:-.02em}
.ko em{font-style:normal;color:${MINT}}
.letter{position:absolute;left:64px;right:64px;color:#FFFFFF;font-weight:700;font-size:34px;line-height:1.5;letter-spacing:-.02em}
.from{position:absolute;left:64px;top:330px;font-weight:800;font-size:18px;letter-spacing:.2em;color:${MINT}}
.sign{position:absolute;left:64px;right:64px;font-weight:800;font-size:28px;color:${MINT}}
.end{position:absolute;left:64px;right:64px;top:1040px;color:#FFFFFF}
.end b{display:block;font-weight:800;font-size:24px}
.end span{display:block;font-weight:500;font-size:16px;color:${MINT2};margin-top:8px}`;

// 마지막 어절만 민트로
const lastMint = t => {
  const parts = String(t).split('<br>');
  const last = parts.pop(); const i = last.lastIndexOf(' ');
  const tail = i < 0 ? `<em>${last}</em>` : `${last.slice(0, i)} <em>${last.slice(i + 1)}</em>`;
  return [...parts, tail].join('<br>');
};
const chrome = `<div class="line"></div><img class="logo" src="${LOGO}">${J.mark ? `<div class="mark shadow">${J.mark}</div>` : ''}`;
const P = {};
J.lines.forEach((l, i) => {
  P['cap_' + (i + 1)] = `${chrome}<div class="cap shadow"><div class="ko">${lastMint(l.ko)}</div>${l.en ? `<div class="en">${l.en}</div>` : ''}</div>`;
});
// 편지 엔딩 (meme.json에 letter가 있을 때만)
if (Array.isArray(J.letter) && J.letter.length) {
  P.l_bg = `<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,82,81,.55) 0%,rgba(0,40,40,.82) 45%,rgba(0,30,30,.9) 100%)"></div>${chrome}<div class="from">TO. ${J.to || 'MY FAMILY'}</div>`;
  J.letter.forEach((t, i) => { P['l_' + (i + 1)] = `<div class="letter" style="top:${390 + i * 128}px">${t}</div>`; });
  P.l_sign = `<div class="sign" style="top:${390 + J.letter.length * 128 + 20}px">${J.sign || ''}</div>`;
  P.l_end = `<div class="end"><b>${J.brand || ''}</b><span>${J.footer || '파마스퀘어가 선물하는 우리 아이 영상'}</span>${J.sample ? '<span style="margin-top:6px;color:rgba(255,255,255,.6)">샘플 영상 · 이름과 이야기는 예시예요</span>' : ''}</div>`;
}

(async () => {
  const out = path.join(dir, 'M'); fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
  for (const [k, body] of Object.entries(P)) {
    const pg = await b.newPage({ viewport: { width: 720, height: 1280 } });
    await pg.goto(F);
    await pg.setContent(`<html><head><style>${CSS}</style></head><body>${body}</body></html>`);
    await pg.evaluate('document.fonts.ready'); await pg.waitForTimeout(300);
    await pg.screenshot({ path: path.join(out, k + '.png'), omitBackground: true });
    await pg.close();
  }
  await b.close(); console.log('그림 ' + Object.keys(P).length + '장 완료 → ' + out);
})();
