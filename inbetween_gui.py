# -*- coding: utf-8 -*-
import tkinter
import numpy as np
import time 
from scipy import interpolate
import networkx as nx
import matplotlib.pyplot as plt
from scipy.spatial import distance
from sklearn.decomposition import KernelPCA
#前準備
"""
グローバル変数定義
"""
titer=np.linspace(0,1,30)
mode=0#1が点を打つ、0が線を引く
temp_x=0
temp_y=0
Domip=[]
c_size=256
"""
定義終わり
"""
root = tkinter.Tk()
key1 = tkinter.Canvas(root, width = c_size, height = c_size)
key1.points_array=[]#点列の格納リスト
key1.pack(side="left")
key1.create_rectangle(0, 0, c_size, c_size,fill="#ffffff")
INBET = tkinter.Canvas(root, width = c_size, height = c_size)
INBET.pack(side="left")
INBET.create_rectangle(0, 0, c_size, c_size,fill="#ffffff")
key2 = tkinter.Canvas(root, width = c_size, height = c_size)
key2.points_array=[]
key2.pack(side="left")
key2.create_rectangle(0, 0, c_size, c_size,fill="#ffffff")
"""
座標軸を入れたい場合
for i in range(0,10):
    c.create_line(0,45*i,800,45*i,fill = '#87cefa')
    c.create_line(80*i,0,80*i,450,fill='#87cefa')
    c.create_line(400,450,400,0,fill='#4169e1',arrow=tkinter.LAST,width=2)
    c.create_line(0,225,800,225,fill='#4169e1',arrow=tkinter.LAST,width=2)
"""
#関数定義
def getp(event):
    global temp_x,temp_y
    temp_x=event.x
    temp_y=event.y
def create_point(event,c):
        x=event.x
        y=event.y
        id=c.create_oval(x-3,y-3,x+3,y+3,fill = '#fa3253',tags='draw')
        """
        #idに識別用のメンバを追加すれば点列の編集も可能
        """
        #c.create_text(x-10, y-10, text = 'P%d'%len(c.points_array[-1]),tags='draw')
        c.points_array[-1].append([x,y])
def write(event,c):
    
    if mode==1:
        
        if len(c.points_array)==0:
            c.points_array.append([])
        create_point(event,c)
    elif mode==0:
        getp(event)
        c.points_array.append([])
def Draw_line(event,c):
    if mode==0:
        global temp_x,temp_y
        x=event.x
        y=event.y
        c.create_line(temp_x,temp_y,x,y,tags='draw',fill = '#000000')
        getp(event)
        c.points_array[-1].append([x,y]) 
def interpolation():
    for p1 in key1.points_array:
        sp1=[]
        if mode==0:
            BINP1=BINSEP(p1)
            for p in BINP1:
                key1.create_oval(p[0]-3,p[1]-3,p[0]+3,p[1]+3,fill = '#6ef442',tags='draw')
            f1=lambda t:INTER(t,BINP1)
        else:
            f1=lambda t:INTER(t,p1)
        for i in titer:
            sp1.append(f1(i))
        key1.create_line(sp1, smooth = 0,tags='draw',fill = '#5998ff')   
        
    for p2 in key2.points_array:
        sp2=[]
        if mode==0:
            BINP2=BINSEP(p2)
            for p in BINP2:
                key2.create_oval(p[0]-3,p[1]-3,p[0]+3,p[1]+3,fill = '#6ef442',tags='draw')
            f2=lambda t:INTER(t,BINP2)
        else:
            f2=lambda t:INTER(t,p2)
        for i in titer:
            sp2.append(f2(i))
        key2.create_line(sp2, smooth = 0,tags='draw',fill = '#5998ff')
        
def delete():
    key1.delete('draw')
    key2.delete('draw')
    key1.points_array=[]
    key2.points_array=[]
    INBET.delete("inbetween")
    
def INTER(t,point):
        #pointは[x,y]のリスト
    x=np.array(point)[:,0]
    y=np.array(point)[:,1]
    if len(x)>2:
        ts=np.linspace(0,1,len(x))
        in1 = interpolate.PchipInterpolator(ts, x)
        in2 = interpolate.PchipInterpolator(ts, y)
        return([in1(t),in2(t)])
    else:#制御点が二つだけの時の例外処理
        return([x[0]+t*(x[1]-x[0]),y[0]+t*(y[1]-y[0])])
def inbetween():
    if len(key1.points_array)!=len(key2.points_array):
        INBET.create_text(80, 10, text = u'エラー:線の本数が一致しません',tags='draw')
    else:  
        k1p=[]
        k2p=[]
        for p1,p2 in zip(key1.points_array,key2.points_array):
            k1p.append([])
            k2p.append([])
            if mode==0:
                BINP1=BINSEP(p1)
                BINP2=BINSEP(p2)
                f1=lambda t:INTER(t,BINP1)
                f2=lambda t:INTER(t,BINP2)
            else:
                f1=lambda t:INTER(t,p1)
                f2=lambda t:INTER(t,p2)
            for i in titer:
                k1p[-1].append(f1(i))
                k2p[-1].append(f2(i))
            k1p[-1]=np.array(k1p[-1])
            k2p[-1]=np.array(k2p[-1])
        
        for i in range(100):
            time.sleep(1/60)
            INBET.delete("inbetween")
            for BeP1,BeP2 in zip(k1p,k2p):
                inbet=BeP1+(i/99)*(BeP2-BeP1)
                inbet=inbet.astype(np.int64).tolist()
                INBET.create_line(inbet,smooth=1,tags='inbetween',fill = '#000000')
            INBET.update()
    

def seprate(line):#二分割法によるドミナントポイント検出
    #インデックス+xy座標
    

    if len(line)<=1:
        pass
    else:
        a=line[:,1][-1]-line[:,1][0]
        b=line[:,0][0]-line[:,0][-1]
        c=line[:,0][-1]*line[:,1][0]-line[:,0][0]*line[:,1][-1]
        d=np.sqrt(a*a+b*b)
        dist=np.abs(a*line[:,0]+b*line[:,1]+c)/d
        if max(dist)>d/50:
            Domip.append(line[np.argmax(dist)])
            seprate(line[0:np.argmax(dist)])
            seprate(line[np.argmax(dist):-1])
            
        else:
            pass
        
def BINSEP(line):
    global Domip
    Domip=[]    
    a=np.array(line)
    Lines=np.concatenate((a,np.arange(len(a)).reshape(len(a),1)),axis=1)  
    """
    点列の順序を追加、列が増えていることに注意
    """    
    seprate(Lines)
    domi=np.array(Domip)
    if len(Domip)!=0:
        temp=domi[:,-1]
        temp=temp.argsort()
        domi = domi[temp]
        domi=np.vstack((Lines[0],domi,Lines[-1]))
    else:
        domi=np.vstack((Lines[0],Lines[-1]))
    return domi
    
def mode_change(n):
    global mode
    mode=scale1.get()    
    
def Additer1(event,c):
    if mode==1:
        x=c.points_array[-1][0][0]
        y=c.points_array[-1][0][1]
        c.create_text(x-10, y-10, text = 'L%d'%len(c.points_array),tags='draw')
        c.points_array.append([])
def Additer0(event,c):
    if mode==0:
        x=c.points_array[-1][0][0]
        y=c.points_array[-1][0][1]
        c.create_text(x-10, y-10, text = 'L%d'%len(c.points_array),tags='draw')
       
def fix():
    exec(open("./recovery.py").read())
    exec(open("./conbshapecontex.py").read())
    exec(open("./matchingnetwork.py").read())
    exec(open("./stroke_correspond.py").read())
    global key2
    key2.points_array=fixed_key2
    inbetween()
#終わり

key1.bind( '<Button-1>', lambda x : write(x,key1)) #move_ovalの引数は自動的に決まる 多くの引数を渡したいときはλ関数で与える
key1.bind( '<Button1-Motion>', lambda x :Draw_line(x,key1))
key1.bind('<ButtonRelease-1>',lambda x: Additer0(x,key1))
key1.bind('<Button-3>',lambda x: Additer1(x,key1))

key2.bind( '<Button-1>', lambda x : write(x,key2))
key2.bind( '<Button1-Motion>', lambda x :Draw_line(x,key2))
key2.bind('<ButtonRelease-1>',lambda x: Additer0(x,key2))
key2.bind('<Button-3>',lambda x: Additer1(x,key2))

button1 = tkinter.Button(root, text=u'補間', command=interpolation,bg='#5998ff')
button1.pack(side=tkinter.RIGHT)
button_inbetween=tkinter.Button(root, text=u'中割り', command=inbetween,bg='#f78e80')
button_inbetween.pack(side=tkinter.RIGHT)
button_del=tkinter.Button(root, text=u'消去', command=delete)
button_fix=tkinter.Button(root, text=u'自動中割り', command=fix)
button_del.pack(side=tkinter.RIGHT)
button_fix.pack(side=tkinter.RIGHT)
scale1 = tkinter.Scale(root, label='Mode', orient='h', from_=0, to=1, command=mode_change)
scale1.pack()

root.mainloop()


