def log_polar(point):
    #point=[x,y]
    if  (point[0]==0 and point[1]==0):
        return ([0,0])
    else:
        u=np.sqrt(point[0]**2+point[1]**2)
        if point[1]>=0:
            v=np.arccos(point[0]/(np.sqrt(point[0]**2+point[1]**2)))
        else:
            v=-np.arccos(point[0]/(np.sqrt(point[0]**2+point[1]**2)))+2*np.pi
            
        return ([u,v])

def LP_trans(points_array):
    """
    pointsは画像全体の特徴点(二次元)のnparray
    返り値はshape_contextの行列と描画用の点列
    """
    points=[]
    for j in points_array:
        #特徴点のみサンプリング
        #k=BINSEP(j)[:,0:2]
        #points=points+k.astype(np.int64).tolist()
        points=points+j
    points=np.array(points)    
    for i in range(len(points)):
        vectors=np.delete(points,i,0)-points[i]
        redge=np.linspace(-32,32,65)
        aedge=np.linspace(-32,32,65)
        h,redge,aedge=(np.histogram2d(vectors[:,0],vectors[:,1],bins=(redge,aedge)))
        h=np.reshape(h,(1,64**2))[0]#/np.sum(h)
        if i==0:
            H=h
        else:
            H=np.vstack((H,h))
    return H

sp1=LP_trans(key1_points_array).astype(np.float32)
sp1=sp1.reshape(sp1.shape[0],1,64,64)
sp2=LP_trans(key2_points_array).astype(np.float32)
sp2=sp2.reshape(sp2.shape[0],1,64,64)
np.save("sp1.npy",sp1)
np.save("sp2.npy",sp2)