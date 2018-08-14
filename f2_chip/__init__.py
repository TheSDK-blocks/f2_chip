#from joblib import Parallel, delayed
import numpy as np
from thesdk import *
import multiprocessing
from functools import reduce
from f2_signal_gen import *
from f2_chip.system_definitions_mixin import system_definitions_mixin
from f2_util_classes import *

class f2_chip(thesdk,system_definitions_mixin):
    def __init__(self,*arg):
        self.proplist=[ 'rxmodels', 'Txantennas', 'Txpower', 'Rxantennas', 'Users', 'Disableuser', 'Nbits', 'Txbits', 'Channeldir', 'CPUFBMODE', 'DSPmode', 'dsp_decimator_model', 'dsp_decimator_scales', 'noisetemp', 'Rs', 'Rs_dsp', 'Hstf', 'ofdmdict' ]; 
        self.rxmodels=[]
        #Signals should be in form s(user,time,Txantenna)
        self.Txantennas=1                       #All the antennas process the same data
        self.Txpower=30                         #Output power per antenna in dBm
        self.Rxantennas=4
        self.Users=2
        self.Disableuser=[]
        self.Nbits=10  #ADC bits
        self.Txbits=9  #DAC bits
        self.Channeldir='Uplink'
        self.CPUBFmode = 'ZF';                  #['BF' | 'ZF'] Default to beam forming 
        self.DSPmode = 'cpu';                   #['cpu' | 'local'] bamforming can be local 
        self.dsp_decimator_model='py'
        self.dsp_decimator_scales=[1,1,1,1]
        self.noisetemp=290
        self.Rs=160e6
        self.Rs_dsp=20e6
        self.Hstf=1                             #Synchronization filter
        self.signal_gen=[]
        self.channel=[]
        self.rx=[]
        self.adc=[]
        self.dsp=[]
        self.tx=[]
        self.serdes=[]
        self.DEBUG= False
        if len(arg)>=1:
            parent=arg[0]
            self.copy_propval(parent,self.proplist)
            self.parent =parent;
        self.init()

    def init(self):
        #this sets the dependent variables
        [ self.rxmodels.append('py') for i in range(self.Rxantennas) ];
        [ self.Disableuser.append(False) for i in range(self.Users) ]              #Disable data transmission for cerrtain users
        self.Rxantennalocations=np.arange(self.Rxantennas)*0.3
    
    def run(self):
        self.channel.run()

        # Parallel processing: When you call obj.method in a child process, the child process is getting its
        #own separate copy of each instance variable in obj. So, the changes you make to
        #them in the child will not be reflected in the parent. You'll need to
        #explicitly pass the changed values back to the parent via a
        #multiprocessing.Queue in order to make the changes take effect the parent:
        k=0
        que1=[]
        proc1=[]
        out=[]
        for i in self.rx: 
            i.init()
            que1.append(multiprocessing.Queue())
            proc1.append(multiprocessing.Process(target=self.rx[k].run, args=(que1[k],)))
            proc1[k].start()
            k += 1 

        for i in range(self.Rxantennas):
            self.rx[i]._Z.Value=que1[i].get()
            proc1[i].join()

        for i in self.adc: 
            i.init()
            i.run()

        #Run dsp in parallel
        #Split in two phases: First, get the channel estimates
        l=0
        que2=[]
        proc2=[]
        for i in range(self.Rxantennas):
            self.dsp[i].init()
            que2.append(multiprocessing.Queue())
            proc2.append(multiprocessing.Process(target=self.dsp[i].get_channel_estimate, args=(que2[l],)))
            proc2[l].start()
            l += 1 

        #Collect results for dsps
        l=0
        for i in range(self.Rxantennas):
            self.dsp[i]._decimated.Value=que2[l].get()
            self.dsp[i]._delayed.Value=que2[l].get()
            self.dsp[i]._sync_index.Value=que2[l].get()
            self.dsp[i]._Frame_sync_short.Value=que2[l].get()
            self.dsp[i]._Frame_sync_long.Value=que2[l].get()
            for k in range(self.Users):
                self.dsp[i]._channel_est.Value[k].Value=que2[l].get()
                self.dsp[i]._channel_corr.Value[k].Value=que2[l].get()
            proc2[l].join()
            l+=1
                
        #This is the CPU for zero-forcing       
        self.cpu.run() 
        # 
        ##Then, receive the data
        l=0
        que3=[]
        proc3=[]
        for i in range(self.Rxantennas):
            que3.append(multiprocessing.Queue())
            proc3.append(multiprocessing.Process(target=self.dsp[i].receive_data, args=(que3[l],)))
            proc3[l].start()
            l += 1 

        #Collect results for dsps
        l=0
        for i in range(self.Rxantennas):
            for k in range(self.Users):
                self.dsp[i]._symbols.Value[k].Value=que3[l].get()
            for k in range(self.Users):
                self.dsp[i]._wordstream.Value[k].Value=que3[l].get()
                self.dsp[i]._bitstream.Value[k].Value=que3[l].get()
            proc3[l].join()
            l+=1


        self.postproc.init()
        self.postproc.run()

        self.serdes.init()
        self.serdes.run()
    
    def run_tx_dsp(self):  

        self.tx_dsp.init()
        self.tx_dsp.run()

        #Set the parallel processing
        for i in self.tx_dacs:
            i.par='True'
        l=0
        que=[]
        proc=[]
        for i in range(self.Txantennas):
            que.append(multiprocessing.Queue())
            proc.append(multiprocessing.Process(target=self.tx_dacs[i].run, args=(que[l],)))
            proc[l].start()
            l += 1 

        #Collect results for dsps
        l=0
        for i in range(self.Txantennas):
            self.tx_dacs[i]._Z.Value=que[l].get()
            proc[l].join()
            l+=1

        print(self.tx_dacs[0]._Z.Value)


    def run_rx_dsp(self):  
        # Parallel processing: When you call obj.method in a child process, the child process is getting its
        #own separate copy of each instance variable in obj. So, the changes you make to
        #them in the child will not be reflected in the parent. You'll need to
        #explicitly pass the changed values back to the parent via a
        #multiprocessing.Queue in order to make the changes take effect the parent:
        k=0
        que1=[]
        proc1=[]
        out=[]
        for i in self.rx: 
            i.init()
            que1.append(multiprocessing.Queue())
            proc1.append(multiprocessing.Process(target=self.rx[k].run, args=(que1[k],)))
            proc1[k].start()
            k += 1 

        for i in range(self.Rxantennas):
            self.rx[i]._Z.Value=que1[i].get()
            proc1[i].join()

        for i in self.adc: 
            i.init()
            i.run()

        self.rx_dsp.init()
        self.rx_dsp.run()

        self.serdes.init()
        self.serdes.run()

