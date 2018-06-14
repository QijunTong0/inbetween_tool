# -*- coding: utf-8 -*-
#データの復元

def length(points):
    leng=0
    for i in range(1,len(points)):
        leng += np.linalg.norm(np.array(points[i])-np.array(points[i-1]))
    return(leng)
def sampling(lines,rate=2):
    new=[]
    for line in lines:
        sample=[]
        x=np.array(line)[:,0]
        y=np.array(line)[:,1]
        ts=np.linspace(0,1,len(line))
        in1 = interpolate.PchipInterpolator(ts, x)
        in2 = interpolate.PchipInterpolator(ts, y)
        for i in range(1,len(ts)):
            Leng=np.sqrt((x[i]-x[i-1])**2+(y[i]-y[i-1])**2)
            t=np.linspace(ts[i-1],ts[i],int(Leng/rate+1))
            for j in t:
                sample.append([int(in1(j)),int(in2(j))])
        new.append(sample)
    return(new)
def plot_line():
    cmap=plt.get_cmap("jet")
    temp=0
    for i in key_points_array:
        j=np.array(i)
        plt.plot(j[:,0],-j[:,1],color=cmap(temp/len(key_points_array)))
        temp+=1
    plt.xticks([])
    plt.yticks([])
with open('key1_2.p', 'rb') as f:
    key1_points_array = pickle.load(f)
with open('key2_2.p', 'rb') as f:
    key2_points_array = pickle.load(f)
    
del key1_points_array[-1]
del key2_points_array[-1]
key1_points_array=sampling(key1_points_array,rate=2)
key2_points_array=sampling(key2_points_array,rate=2)
allpoints1=[]
allpoints2=[]
for i in (key1_points_array):
    allpoints1=allpoints1+i
for i in (key2_points_array):
    allpoints2=allpoints2+i

allpoints1=np.array(allpoints1)
allpoints2=np.array(allpoints2)
m1=len(allpoints1)
m2=len(allpoints2)
#plot_line()
plt.scatter(allpoints1[:,0],-allpoints1[:,1],s=2)
plt.show()
plt.scatter(allpoints2[:,0],-allpoints2[:,1],s=2)
plt.show()
#データの保存
#np.savetxt('kpca.csv', Cpca_prod, delimiter=',')
#pickle.dump(key1.points_array,open("key1.p","wb"))
#pickle.dump(key2.points_array,open("key2.p","wb"))