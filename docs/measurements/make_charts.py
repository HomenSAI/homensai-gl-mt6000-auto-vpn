"""Static SVG charts for docs/measurements (GitHub renders them as images). Data = router/measurements_help.inc.js."""
import sys
from pathlib import Path
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True)
AUTO_STAGES=[('Сбой ещё не замечен / not yet noticed','#9aa3ad'),('Подтверждение сбоя / confirming','#e0b100'),('Само переключение / switch itself','#e07800')]
MANUAL_STAGES=[('Запрос кнопки / button request','#7c3aed'),('Ожидание Auto / waiting for Auto','#9aa3ad'),('Проверки до / checks before','#e0b100'),
               ('Смена маршрута / route change','#2f9e57'),('Проверки после / checks after','#e07800'),('Запись и отображение / saving','#2563eb')]
AUTO=[('alpha82 · rtp2',[29.5,63.3,60.5]),('beta5 · fast',[28,57,44]),('beta7 · fast',[28.3,68.3,39.3])]
MANUAL=[('beta7',[4.6,2.8,12.1,5.5,15.7,1.5]),('beta8',[3.5,1.7,5.3,0.3,3.7,2.1]),('beta9',[3.3,1.4,2.3,1.2,0.7,1.0])]
def chart(name,title,rows,stages,unit_max):
    left,width,row,top=150,800,40,60
    h=top+len(rows)*row+40+len(stages)*22
    scale=width/unit_max
    out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 %d" font-family="Segoe UI,Arial,sans-serif">'%h,
         '<rect width="1000" height="%d" fill="#ffffff"/>'%h,
         '<text x="20" y="30" font-size="18" font-weight="700" fill="#14212e">%s</text>'%title]
    step=10 if unit_max<=60 else 20
    for t in range(0,int(unit_max)+1,step):
        x=left+t*scale
        out.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="#d8d9d8"/>'%(x,x,top-8,top+len(rows)*row))
        out.append('<text x="%.1f" y="%d" font-size="12" text-anchor="middle" fill="#4b5563">%d с</text>'%(x,top+len(rows)*row+16,t))
    for i,(label,values) in enumerate(rows):
        y=top+i*row;at=0
        out.append('<text x="%d" y="%d" font-size="14" text-anchor="end" fill="#14212e">%s</text>'%(left-10,y+22,label))
        for k,v in enumerate(values):
            x=left+at*scale;w=v*scale
            out.append('<rect x="%.1f" y="%d" width="%.1f" height="28" fill="%s"><title>%s: %.1f с</title></rect>'%(x,y+4,max(w,1),stages[k][1],stages[k][0],v))
            if w>=34:out.append('<text x="%.1f" y="%d" font-size="12" text-anchor="middle" fill="#ffffff">%.1f</text>'%(x+w/2,y+23,v))
            at+=v
        out.append('<text x="%.1f" y="%d" font-size="13" font-weight="700" fill="#14212e">%.1f с</text>'%(left+at*scale+6,y+23,at))
    ly=top+len(rows)*row+36
    for k,(label,color) in enumerate(stages):
        out.append('<rect x="%d" y="%d" width="14" height="14" fill="%s"/><text x="%d" y="%d" font-size="13" fill="#14212e">%s</text>'%(left,ly+k*22-11,color,left+22,ly+k*22,label))
    out.append('</svg>')
    (OUT/name).write_text('\n'.join(out)+'\n',encoding='utf-8',newline='\n')
chart('auto-by-version.svg','Auto: от сбоя до трафика на резерве (уровень 3) / fault to traffic on reserve',AUTO,AUTO_STAGES,160)
chart('manual-by-version.svg','Ручная кнопка при включённом Auto: от нажатия до готово / click to done',MANUAL,MANUAL_STAGES,45)
print('ok')
