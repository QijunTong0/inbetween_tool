# -*- coding: utf-8 -*-
#コスト行列,パラメータ
#cost=distance.cdist(vec[0:m1],vec[m1:m1+m2])
cost=1-stroke_matrix
#cost=10000*cost
cost=cost.astype(np.int64)
cost=cost-np.min(cost)
row,col=np.shape(cost) 
#常に行の方を多くする
rev=False
if row<col:
    cost=cost.T
    row,col=np.shape(cost) 
    rev=True
source_capacity=1000
sink_capacity=1000
Demand=row
#グラフ作成

lower=[-1]*row+[1]*col
G = nx.DiGraph()
G.add_node('s', demand = -Demand+row)
for i in range(row+col):
    G.add_node(i,demand=lower[i])
G.add_node('t', demand = Demand-col)

# ノード間をエッジでつなぐ
for i in range(row):
    for j in range(col):
        G.add_edge(i, j+row, weight = cost[i][j], capacity = 1)
for k in range(row):
    G.add_edge('s',k,weight=0,capacity=source_capacity)
for k in range(col):
    G.add_edge(k+row,'t',weight=0,capacity=sink_capacity)
#network_simplex(G, demand='demand', capacity='capacity', weight='weight')
#Find a minimum cost flow satisfying all demands in digraph G.
flowCost, flowDict = nx.network_simplex(G)
"""
plt.scatter(allpoints1[:,0],allpoints1[:,1],s=2,color="red")
plt.scatter(allpoints2[:,0],allpoints2[:,1],s=2,color="blue")
if m1>m2:
    for i in range(row):
        for j in range(col):
            if flowDict[i][j+row]==1:
                plt.plot([allpoints1[i,0],allpoints2[j,0]],[allpoints1[i,1],allpoints2[j,1]],color="black",alpha=0.15)
else:
    for i in range(row):
        for j in range(col):
            if flowDict[i][j+row]==1:
                plt.plot([allpoints2[i,0],allpoints1[j,0]],[allpoints2[i,1],allpoints1[j,1]],color="black",alpha=0.15)
"""





