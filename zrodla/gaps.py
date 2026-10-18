import os, sys; sys.path.insert(0,'.')
from render import *
from preview import load
from PIL import Image
n=sys.argv[1]; m,q=load(n,'axon')
tiles=[]
os.makedirs('out', exist_ok=True)
for yaw,pitch in [(0,0),(180,0),(0,60),(0,-60),(40,25),(140,25),(220,-25),(320,-25),(90,0)]:
    R=ortho_view(yaw,pitch); cv=Canvas(600,300,bg=(255,0,255)); cv.col[:]=(255,0,255)
    xf,pr,_=fit_ortho(q,R,600,300); draw(cv,q,xf,pr,light_preview); tiles.append(cv.image())
o=Image.new('RGB',(1800,900))
for i,t in enumerate(tiles): o.paste(t,((i%3)*600,(i//3)*300))
o.save(os.path.join('out', 'gaps_'+n+'.png'))
