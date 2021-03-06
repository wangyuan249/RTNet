from RFTNet import *
from RFlearn import *
from DataLoader import *
from Utils import *
import scipy.io
import numpy as np
from tensorflow.contrib import slim
os.environ['CUDA_VISIBLE_DEVICES']=''



class Train():
    def __init__(self,class_num,batch_size,iters,learning_rate,keep_prob,param):
        self.ClassNum=class_num

        self.BatchSize=batch_size
        self.Iters=iters
        self.LearningRate=learning_rate
        self.KeepProb=keep_prob
        self.target_loss_param=param[0]
        self.domain_loss_param=param[1]
        self.adver_loss_param=param[2]

        self.SourceData,self.SourceLabel=load_svhn('svhn')
        # filter_label_index=np.where(self.SourceLabel<5)
        # self.SourceData=self.SourceData[filter_label_index]
        # self.SourceLabel=self.SourceLabel[filter_label_index]
        # self.SourceData2,self.SourceLabel2=load_fakemnist('s_train')
        # self.SourceData=np.concatenate((self.SourceData1,self.SourceData2),axis=0)
        # self.SourceLabel=np.concatenate((self.SourceLabel1,self.SourceLabel2),axis=0)
        # self.SourceData2,self.SourceLabel2=load_s('s')
        # self.SourceData=np.vstack((self.SourceData1,self.SourceData2))
        # self.SourceLabel=np.hstack((self.SourceLabel1,self.SourceLabel2))
        # self.SourceData,self.SourceLabel=init_shuffle(self.SourceData,self.SourceLabel)

        # self.TargetData, self.TargetLabel=load_fakemnistm('mm')
        # self.TestData, self.TestLabel = load_fakemnistm('mm')
        self.TargetData, self.TargetLabel=load_mnist('mnist')
        filter_label_index=np.where(self.TargetLabel<5)
        self.TargetData=self.TargetData[filter_label_index]
        self.TargetLabel=self.TargetLabel[filter_label_index]

        self.TestData, self.TestLabel = load_mnist('mnist',split='test')
        filter_label_index=np.where(self.TestLabel<5)
        self.TestData=self.TestData[filter_label_index]
        self.TestLabel=self.TestLabel[filter_label_index]

        #######################################################################################

        # self.SourceData,self.SourceLabel=load_fakemnist('s_train')
        # # self.SourceData2,self.SourceLabel2=load_fakemnist('s_train')
        #
        # self.TargetData, self.TargetLabel=load_mnist('mnist')
        # self.TestData, self.TestLabel = load_mnist('mnist',split="test")
        #########################################################################################
        self.source_image = tf.placeholder(tf.float32, shape=[self.BatchSize, 32,32,3],name="source_image")
        self.source_label = tf.placeholder(tf.float32, shape=[self.BatchSize, self.ClassNum],name="source_label")

        # self.mid_image = tf.placeholder(tf.float32, shape=[self.BatchSize, 32,32,3],name="source_image")
        # self.mid_label = tf.placeholder(tf.float32, shape=[self.BatchSize, self.ClassNum],name="source_label")

        self.target_image = tf.placeholder(tf.float32, shape=[self.BatchSize, 32, 32,1],name="target_image")
        self.Training_flag = tf.placeholder(tf.bool, shape=None,name="Training_flag")

        self.action=tf.placeholder(tf.float32,shape=[self.BatchSize,],name="Choose_Sample")



    def TrainNet(self):
        self.source_model=Lenet(inputs=self.source_image,name="source",training_flag=self.Training_flag, reuse=False)
        self.target_model=Lenet(inputs=self.target_image,name="target",training_flag=self.Training_flag,reuse=True)



        # self.mid_model=Lenet(inputs=self.mid_image, training_flag=self.Training_flag,reuse=True)

        varall=tf.trainable_variables()
        self.CalLoss()
        self.solver = tf.train.AdamOptimizer(learning_rate=self.LearningRate).minimize(self.loss)
        self.source_prediction = tf.argmax(self.source_model.softmax_output, 1)
        self.target_prediction = tf.argmax(self.target_model.softmax_output, 1)

        with tf.Session(config=tf.ConfigProto(gpu_options=tf.GPUOptions(allow_growth=True))) as sess:
            actor = Actor(sess, n_features=64, n_actions=2, lr=0.001)
            critic = Critic(sess, n_features=64, lr=0.01)

            # self.solver = tf.train.AdamOptimizer(learning_rate=self.LearningRate).minimize(self.loss)
            init = tf.global_variables_initializer()
            sess.run(init)
            self.SourceLabel=sess.run(tf.one_hot(self.SourceLabel,10))
            self.TestLabel=sess.run(tf.one_hot(self.TestLabel,10))

            # self.SourceLabel2 = sess.run(tf.one_hot(self.SourceLabel2, 10))
            # self.source_model.weights_initial(sess)
            # self.target_model.weights_initial(sess)
            true_num = 0.0
            for step in range(self.Iters):
                # self.SourceData,self.SourceLabel=shuffle(self.SourceData,self.SourceLabel)
                i= step % int(self.SourceData.shape[0]/self.BatchSize)
                j= step % int(self.TargetData.shape[0]/self.BatchSize)
                source_batch_x = self.SourceData[i * self.BatchSize: (i + 1) * self.BatchSize]
                source_batch_y = self.SourceLabel[i * self.BatchSize: (i + 1) * self.BatchSize]

                # mid_batch_x = self.SourceData2[i * self.BatchSize: (i + 1) * self.BatchSize]
                # mid_batch_y = self.SourceLabel2[i * self.BatchSize: (i + 1) * self.BatchSize]

                target_batch_x = self.TargetData[j * self.BatchSize: (j + 1) * self.BatchSize]
                state=sess.run(
                    fetches=self.source_model.fc4,
                    feed_dict={self.source_image: source_batch_x, self.source_label: source_batch_y,self.target_image: target_batch_x, self.Training_flag: False})
                a = actor.choose_action(state)
                total_loss, source_loss,domain_loss,source_prediction,_= sess.run(
                    fetches=[self.loss, self.source_loss, self.domain_loss,self.source_prediction, self.solver],
                    feed_dict={self.source_image: source_batch_x, self.source_label: source_batch_y,self.target_image: target_batch_x, self.Training_flag: True,self.action:a})
                self.re_loss = tf.reduce_mean(tf.reduce_sum(tf.square(self.target_model.inputs - self.target_model.re), axis=[1, 2, 3]))
                re_loss=sess.run(fetches=self.re_loss,feed_dict={self.target_image: target_batch_x, self.Training_flag: False})
                reward=np.exp(-re_loss)
                state_next=sess.run(
                    fetches=self.source_model.fc4,
                    feed_dict={self.source_image: source_batch_x, self.source_label: source_batch_y,self.target_image: target_batch_x, self.Training_flag: False})
                td_error = critic.learn(state,reward,state_next)
                exp_v=actor.learn(state, a, td_error)
                # print("======================")
                # print(td_error)
                true_label = argmax(source_batch_y, 1)
                true_num = true_num + sum(true_label == source_prediction)

                # if step % 100==0:
                #     self.SourceData, self.SourceLabel = shuffle(self.SourceData, self.SourceLabel)
                if step % 200 ==0:
                    print ("Iters-{} ### TotalLoss={} ### SourceLoss={} ###DomainLoss={} ###ReLoss={}".format(step, total_loss, source_loss,domain_loss,re_loss))
                    train_accuracy = true_num / (200*self.BatchSize)
                    true_num = 0.0
                    print (" ########## train_accuracy={} ###########".format(train_accuracy))
                    self.Test(sess)






    def CalLoss(self):
        self.source_cross_entropy = tf.nn.softmax_cross_entropy_with_logits(labels=self.source_label, logits=self.source_model.fc5)
        self.re_loss= tf.reduce_mean(tf.reduce_sum(tf.square(self.source_model.inputs - self.source_model.re), axis=[1, 2, 3]))
        self.re_loss_source= tf.reduce_mean(tf.reduce_sum(tf.square(self.source_model.inputs - self.source_model.re), axis=[1, 2, 3]))
        self.re_loss_target= tf.reduce_mean(tf.reduce_sum(tf.square(self.target_model.inputs - self.target_model.re), axis=[1, 2, 3]))

        # self.mid_cross_entropy = tf.nn.softmax_cross_entropy_with_logits(labels=self.mid_label, logits=self.mid_model.fc5)
        # self.mid_loss = tf.reduce_mean(self.mid_cross_entropy)
        filter_loss=tf.where(tf.equal(self.action,1))
        filter_loss = filter_loss[:, 0:1]
        self.source_cross_entropy=tf.squeeze(tf.gather(self.source_cross_entropy,filter_loss))
        # self.source_loss = tf.reduce_mean(self.source_cross_entropy*self.action)
        self.source_loss = tf.reduce_mean(self.source_cross_entropy)


        # self.CalTargetLoss(method="Entropy")
        self.CalDomainLoss(method="CORAL")
        # self.CalAdver()
        # self.L2Loss()
        self.loss=self.source_loss+self.domain_loss_param*self.domain_loss
        # self.loss=self.source_loss+self.domain_loss_param*self.domain_loss+self.re_loss_source+self.re_loss_target

    def L2Loss(self):
        all_variables = tf.trainable_variables()
        self.l2 = 1e-5 * tf.add_n([tf.nn.l2_loss(v) for v in all_variables if 'bias' not in v.name])

    def CalDomainLoss(self,method):
        if method=="MMD":
            Xs=self.source_model.fc4
            Xt=self.target_model.fc4
            diff=tf.reduce_mean(Xs, 0, keep_dims=False) - tf.reduce_mean(Xt, 0, keep_dims=False)
            self.domain_loss=tf.reduce_sum(tf.multiply(diff,diff))


        elif method=="KMMD":
            Xs=self.source_model.fc4
            Xt=self.target_model.fc4
            self.domain_loss=tf.maximum(0.0001,KMMD(Xs,Xt))



        elif method=="CORAL":
            Xs = self.source_model.fc4
            Xt = self.target_model.fc4
            filter_loss = tf.where(tf.equal(self.action, 1))
            filter_loss = filter_loss[:, 0:1]
            Xs = tf.squeeze(tf.gather(Xs, filter_loss))
            Xt = tf.squeeze(tf.gather(Xt, filter_loss))
            # d=int(Xs.shape[1])
            # Xms = Xs - tf.reduce_mean(Xs, 0, keep_dims=True)
            # Xcs = tf.matmul(tf.transpose(Xms), Xms) / self.BatchSize
            # Xmt = Xt - tf.reduce_mean(Xt, 0, keep_dims=True)
            # Xct = tf.matmul(tf.transpose(Xmt), Xmt) / self.BatchSize
            # self.domain_loss = tf.reduce_sum(tf.multiply((Xcs - Xct), (Xcs - Xct)))
            # self.domain_loss=self.domain_loss / (4.0*d*d)
            self.domain_loss=self.coral_loss(Xs,Xt)


        elif method =='LCORAL':
            Xs = self.source_model.fc4
            Xt = self.target_model.fc4
            self.domain_loss=self.log_coral_loss(Xs,Xt)


    def CalTargetLoss(self,method):
        if method=="Entropy":
            trg_softmax=self.target_model.softmax_output
            self.target_loss=-tf.reduce_mean(tf.reduce_sum(trg_softmax * tf.log(trg_softmax), axis=1))


        elif method=="Manifold":
            pass




    def coral_loss(self, h_src, h_trg, gamma=1e-3):

        # regularized covariances (D-Coral is not regularized actually..)
        # First: subtract the mean from the data matrix
        batch_size = self.BatchSize
        h_src = h_src - tf.reduce_mean(h_src, axis=0)
        h_trg = h_trg - tf.reduce_mean(h_trg, axis=0)
        cov_source = (1. / (batch_size - 1)) * tf.matmul(h_src, h_src,
                                                         transpose_a=True)  # + gamma * tf.eye(self.hidden_repr_size)
        cov_target = (1. / (batch_size - 1)) * tf.matmul(h_trg, h_trg,
                                                         transpose_a=True)  # + gamma * tf.eye(self.hidden_repr_size)
        # Returns the Frobenius norm (there is an extra 1/4 in D-Coral actually)
        # The reduce_mean account for the factor 1/d^2
        return tf.reduce_mean(tf.square(tf.subtract(cov_source, cov_target)))

    def log_coral_loss(self, h_src, h_trg, gamma=1e-3):
        # regularized covariances result in inf or nan
        # First: subtract the mean from the data matrix
        batch_size = float(self.BatchSize)
        h_src = h_src - tf.reduce_mean(h_src, axis=0)
        h_trg = h_trg - tf.reduce_mean(h_trg, axis=0)
        cov_source = (1. / (batch_size - 1)) * tf.matmul(h_src, h_src,
                                                         transpose_a=True)  # + gamma * tf.eye(self.hidden_repr_size)
        cov_target = (1. / (batch_size - 1)) * tf.matmul(h_trg, h_trg,
                                                         transpose_a=True)  # + gamma * tf.eye(self.hidden_repr_size)
        # eigen decomposition
        eig_source = tf.self_adjoint_eig(cov_source)
        eig_target = tf.self_adjoint_eig(cov_target)
        log_cov_source = tf.matmul(eig_source[1],
                                   tf.matmul(tf.diag(tf.log(eig_source[0])), eig_source[1], transpose_b=True))
        log_cov_target = tf.matmul(eig_target[1],
                                   tf.matmul(tf.diag(tf.log(eig_target[0])), eig_target[1], transpose_b=True))

        # Returns the Frobenius norm
        return tf.reduce_mean(tf.square(tf.subtract(log_cov_source, log_cov_target)))



    # ~ return tf.reduce_mean(tf.reduce_max(eig_target[0]))
    # ~ return tf.to_float(tf.equal(tf.count_nonzero(h_src), tf.count_nonzero(h_src)))


    def Test(self,sess):
        true_num=0.0
        # num=int(self.TargetData.shape[0]/self.BatchSize)
        num = int(self.TestData.shape[0] / self.BatchSize)
        total_num=num*self.BatchSize
        for i in range (num):
            # self.TestData, self.TestLabel = shuffle(self.TestData, self.TestLabel)
            k = i % int(self.TestData.shape[0] / self.BatchSize)
            target_batch_x = self.TestData[k * self.BatchSize: (k + 1) * self.BatchSize]
            target_batch_y= self.TestLabel[k * self.BatchSize: (k + 1) * self.BatchSize]
            prediction=sess.run(fetches=self.target_prediction, feed_dict={self.target_image:target_batch_x, self.Training_flag: False})
            true_label = argmax(target_batch_y, 1)

            true_num+=sum(true_label==prediction)
        accuracy=true_num / total_num
        print ("###########  Test Accuracy={} ##########".format(accuracy))

def main():
    target_loss_param =0
    domain_loss_param =8 #best 6
    adver_loss_param=0
    param=[target_loss_param, domain_loss_param,adver_loss_param]
    Runer=Train(class_num=10,batch_size=128,iters=100000,learning_rate=0.0001,keep_prob=1,param=param)
    Runer.TrainNet()

def load_mnist(image_dir, split='train'):
    print ('Loading MNIST dataset.')

    image_file = 'train.pkl' if split == 'train' else 'test.pkl'
    image_dir = os.path.join(image_dir, image_file)
    with open(image_dir, 'rb') as f:
        mnist = pickle.load(f)
    images = mnist['X'] / 127.5 - 1
    labels = mnist['y']
    labels=np.squeeze(labels).astype(int)

    return images,labels
def load_svhn(image_dir, split='train'):
    print ('Loading SVHN dataset.')

    image_file = 'train_32x32.mat' if split == 'train' else 'test_32x32.mat'

    image_dir = os.path.join(image_dir, image_file)
    svhn = scipy.io.loadmat(image_dir)
    images = np.transpose(svhn['X'], [3, 0, 1, 2]) / 127.5 - 1
    # ~ images= resize_images(images)
    labels = svhn['y'].reshape(-1)
    labels[np.where(labels == 10)] = 0
    return images, labels

def load_USPS(image_dir,split='train'):
    print('Loading USPS dataset.')
    image_file='USPS_train.pkl' if split=='train' else 'USPS_test.pkl'
    image_dir=os.path.join(image_dir,image_file)
    with open(image_dir, 'rb') as f:
        usps = pickle.load(f)
    images = usps['data']
    images=np.reshape(images,[-1,32,32,1])
    labels = usps['label']
    labels=np.squeeze(labels).astype(int)
    return images,labels

def load_syn(image_dir,split='train'):
    print('load syn dataset')
    image_file='synth_train_32x32.mat' if split=='train' else 'synth_test_32x32.mat'
    image_dir=os.path.join(image_dir,image_file)
    syn = scipy.io.loadmat(image_dir)
    images = np.transpose(syn['X'], [3, 0, 1, 2]) / 127.5 - 1
    labels = syn['y'].reshape(-1)
    return images,labels


def load_mnistm(image_dir,split='train'):
    print('Loading mnistm dataset.')
    image_file='mnistm_train.pkl' if split=='train' else 'mnistm_test.pkl'
    image_dir=os.path.join(image_dir,image_file)
    with open(image_dir, 'rb') as f:
        mnistm = pickle.load(f)
    images = mnistm['data']

    labels = mnistm['label']
    labels=np.squeeze(labels).astype(int)
    return images,labels

def load_s(image_dir):
    print('load syn dataset')
    image_file = 's_train.mat'
    image_dir = os.path.join(image_dir, image_file)
    s = scipy.io.loadmat(image_dir)

    images = s['x'] / 127.5 - 1
    labels = s['y'].reshape(-1)
    return images,labels
    print("success")

def load_fakemnist(image_dir):
    print('load syn dataset')
    image_file = 's_trainFakemnist.mat'
    image_dir = os.path.join(image_dir, image_file)
    s = scipy.io.loadmat(image_dir)

    images = s['x'] / 127.5 - 1
    labels = s['y'].reshape(-1)
    return images,labels
    print("success")

def load_realsvhn(image_dir):
    print('load syn dataset')
    image_file = 's_trainRealSVHN.mat'
    image_dir = os.path.join(image_dir, image_file)
    s = scipy.io.loadmat(image_dir)

    images = s['x'] / 127.5 - 1
    labels = s['y'].reshape(-1)
    return images,labels
    print("success")

def load_realmnist(image_dir):
    print('load syn dataset')
    image_file = 's_Realmnist.mat'
    image_dir = os.path.join(image_dir, image_file)
    s = scipy.io.loadmat(image_dir)

    images = s['x'] / 127.5 - 1
    labels = s['y'].reshape(-1)
    return images,labels
    print("success")

def load_testrealmnist(image_dir):
    print('load syn dataset')
    image_file = 's_testRealmnist.mat'
    image_dir = os.path.join(image_dir, image_file)
    s = scipy.io.loadmat(image_dir)

    images = s['x'] / 127.5 - 1
    labels = s['y'].reshape(-1)
    return images,labels
    print("success")

def load_fakemnistm(image_dir):
    print('load syn dataset')
    image_file = 's_train.mat'
    image_dir = os.path.join(image_dir, image_file)
    s = scipy.io.loadmat(image_dir)

    images = s['x'] / 127.5 - 1
    labels = s['y'].reshape(-1)
    return images,labels
    print("success")

if __name__=="__main__":
    main()
