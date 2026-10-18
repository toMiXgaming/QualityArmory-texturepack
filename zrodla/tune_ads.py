import sys, json, numpy as np
sys.path.insert(0,'.')
import gen
from render import *
from preview import load
W,H=480,270
def cover(m,q,left=True):
    cv=Canvas(W,H,bg=(0,0,0),ss=1)
    cv.z[:]=-1e9
    xf,pr=first_person(m['display'],W,H,left=left,charged=True)
    draw(cv,q,xf,pr,light_mc3d,near=0.05)
    mask=cv.z>-1e8
    if not mask.any(): return 0,0,0,0
    ys,xs=np.where(mask)
    return mask.mean(), (xs.max()-xs.min()+1)/W, (H-ys.min())/H, (ys.max()+1)/H
for n in ['ak47','m4a1s','remmington']:
    m,q=load(n,'qa'); print(n,'QA ads cov/width/topfrac', np.round(cover(m,q),3), 'hip', np.round(cover(m,q,False),3))
    m,q=load(n,'axon'); print(n,'AX ads', np.round(cover(m,q),3), 'hip', np.round(cover(m,q,False),3))

print('--- sweep')
disp=json.load(open('display_qa.json'))
for n in ['ak47','m4a1s','remmington']:
    g=gen.BUILDERS[n](); m,q=load(n,'axon')
    for ev in ([g.ads['cam'][1]] if n!='remmington' else [1.6,2.0,2.4]):
        for u in (40,44,48,52,56,60,66,72):
            g.ads=dict(g.ads, cam=(u, ev))
            try: d,_=gen.ads_display(g,disp[n])
            except AssertionError: continue
            m['display']=d
            c=cover(m,q)
            print(n,ev,u,np.round(c,3))
