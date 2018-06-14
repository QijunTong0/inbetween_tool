"""
#対応グループの決定
#flowDict_f
mathcはキーフレーム1からキーフレーム2へのマッピング
"""
import copy
def mapping(flowDict):
    if rev:#m1<m2のとき
        """
        転置が起きたなら
        """
        match=np.zeros((m2,m1))
        for i in range(m2):
            for j in range(m2,m1+m2):
                if flowDict[i][j]==1:
                    match[i,j-m2]=1
        #key1からのマッピングに直す
        match=match.T
    else:
        match=np.zeros((m1,m2))
        for i in range(m1):
            for j in range(m1,m1+m2):
                if flowDict[i][j]==1:
                    match[i,j-m1]=1
    return match
def coratio(st1,st2,match):
    """
    与えられた対応の元でst1とst21の類似度を計算する
    st1とst2はインデックス,list or bool
    """
    W=match[st1].T[st2].T
    if np.sum(W)>0:
        r1=np.sum(np.apply_along_axis(np.sum,1,W)>0)
        r2=np.sum(np.apply_along_axis(np.sum,0,W)>0)
        return((r1/len(st1)+r2/len(st2))*0.5)
    else:
        return(0)
def covest(st1,st2,match):
    """
    与えられた対応の元でst1とst21の類似度を計算する
    st1とst2はインデックス,list or bool
    """
    W=match[st1].T[st2].T
    if np.sum(W)>1:
        vect=np.array(np.where(W==1))
        cov=np.cov(vect[0],vect[1])
        return(cov[0,1]/np.sqrt(cov[0,0]*cov[1,1]))
    else:
        return(0)
def stroke_match(stroke_matrix,seq_matrix):#一対一の場合
    stmat=copy.deepcopy(stroke_matrix)
    revmat=copy.deepcopy(seq_matrix)
    st_ind=[]
    rev_ind=[]
    while (len(st_ind)!=len(key1_points_array)):
        max_ind=np.unravel_index(stmat.argmax(), stmat.shape)
        st_ind.append(max_ind)
        stmat[max_ind[0]]=-1
        stmat[:,max_ind[1]]=-1
        rev_ind.append(np.sign(revmat[max_ind]))
    st_ind=np.array(st_ind)
    rev_ind=np.array(rev_ind).reshape((len(rev_ind),1))
    temp=np.hstack((st_ind,rev_ind))
    return(temp[np.argsort(temp[:,0])])
    
def fix_array(key2_points_array,stmatch):
    temp=[]
    for i in range(len(stmatch)):
        if stmatch[i,2]==1:
            temp.append([key2_points_array[i]])
        else:
            temp.append([key2_points_array[i].reverse()])
        return(temp)
match=mapping(flowDict)
plt.imshow(match)
key1_ind=[]
for i,j in enumerate(key1_points_array):
    key1_ind+=[i]*len(j)
key1_ind=np.array(key1_ind)
key2_ind=[]
for i,j in enumerate(key2_points_array):
    key2_ind+=[i]*len(j)
key2_ind=np.array(key2_ind)
"""
for i,j in zip(ma,key2_points_array):
    key2_ind+=[i]*len(j)  
key2_ind=np.array(key2_ind)
"""
"""ストローク再構成
stroke_matrix:ストロークの類似度行列
seq_matrix:順番の推定行列
"""
stroke_matrix=np.zeros((len(key1_points_array),len(key2_points_array)))
seq_matrix=np.zeros((len(key1_points_array),len(key2_points_array)))
for i in range(len(key1_points_array)):
    for j in range(len(key2_points_array)):
        stroke_matrix[i][j]=coratio(np.where(key1_ind==i)[0],np.where(key2_ind==j)[0],match)
        seq_matrix[i,j]=covest(np.where(key1_ind==i)[0],np.where(key2_ind==j)[0],match)
#print(stroke_matrix)
#print(seq_matrix)
#matchst=stroke_match(stroke_matrix,seq_matrix)        
#fixed_key2=fix_array(key2.points_array,matchst)
