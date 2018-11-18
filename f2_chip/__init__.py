#from joblib import Parallel, delayed
import numpy as np
from thesdk import *
import multiprocessing
from functools import reduce
from f2_signal_gen import *
from f2_dsp import *
from f2_signal_gen import *
from f2_channel import *
from f2_rx import *
from f2_adc import *
from f2_dac import *
from f2_dsp import *
from f2_util_classes import *

class f2_chip(thesdk):
    def __init__(self,*arg):
        self.proplist=[ 'rxmodels', 
                        'Txantennas', 
                        'Txpower', 
                        'Rxantennas', 
                        'Users', 
                        'Rxgain',
                        'Rx_NF_dB'
                        'Disableuser', 
                        'Nbits', 
                        'Txbits', 
                        'Channeldir', 
                        'CPUFBMODE', 
                        'DSPmode', 
                        'dsp_decimator_scales', 
                        'dsp_decimator_cic3shift',
                        'rx_output_mode',
                        'noisetemp', 
                        'Rs', 
                        'Rs_dsp', 
                        'Hstf', 
                        'ofdmdict' 
                        'nserdes' ]; 
        self.rxmodels=[]
        #Signals should be in form s(user,time,Txantenna)
        self.txrxmode='tx'
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
        self.dsp_decimator_cic3shift=4
        self.rx_output_mode=1
        self.noisetemp=290
        self.Rs=160e6
        self.Rs_dsp=20e6
        self.Hstf=1                             #Synchronization filter
        self.rx=[]
        self.adc=[]
        self.dsp=[]
        self.tx=[]
        self.nserdes=2
        self.serdes=[]
        self.DEBUG=False
        self.iptr_A=refptr()
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
        self.iptr_A.Value=[refptr() for _ in range(self.Rxantennas)]

        self._Z_real_t=[ refptr() for _ in range(self.Txantennas) ]
        self._Z_real_b=[ refptr() for _ in range(self.Txantennas) ]
        self._Z_imag_t=[ refptr() for _ in range(self.Txantennas) ]
        self._Z_imag_b=[ refptr() for _ in range(self.Txantennas) ]

        #Rx and tx refer to serdes lane tx is the transmitter input of the serdes
        self._io_lanes_tx=[ iofifosigs(**{'users':self.Users}) for _ in range(self.nserdes)] #this is an output
        self._io_lanes_rx=[ iofifosigs(**{'users':self.Users}) for _ in range(self.nserdes)] #this is an input
    
        #This is the definition for the Transceiver system
        # Aim is to make it resemple the actual circuit as closely as possible

        # One RX_path takes in multiple users and either
        # Sums the user signals or just transmits one of them
        self.dsp=f2_dsp(self)

        self.tx_dacs=[ f2_dac(self) for i in range(self.Txantennas) ]
        for i in range(self.Txantennas):
            self.tx_dacs[i].iptr_real_t=self.dsp._Z_real_t[i]
            self.tx_dacs[i].iptr_real_b=self.dsp._Z_real_b[i]
            self.tx_dacs[i].iptr_imag_t=self.dsp._Z_imag_t[i]
            self.tx_dacs[i].iptr_imag_b=self.dsp._Z_imag_b[i]
        #Not connected anywhere, just check if you can run the sim


        #Rx_block
        self.rx= [f2_rx(self) for i in range(self.Rxantennas)]
        #Set the Rx models
        for i in range(self.Rxantennas):
            self.rx[i].model=self.rxmodels[i]
            # Io defined by load 
            # Always define upper level by the lower level.
            self.iptr_A.Value[i]=self.rx[i].iptr_A

        self.adc=[f2_adc(self) for i in range(self.Rxantennas)]
        for i in range(self.Rxantennas):
            #connect adc rx 
            self.adc[i].iptr_A=self.rx[i]._Z
            self.dsp.iptr_A.Value[i]=self.adc[i]._Z

        #self.serdes=f2_serdes(self)
        #self.serdes.Users=1 #We use only 1 user coming out of the dsp (data is the same)
        #No cpu

    
    def run_tx_dsp(self):  
        print('DSP mode is %s'%(self.dsp.model))
        self.dsp.run_tx()
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

    def run_rx_analog(self):  
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
            que1.append(multiprocessing.Queue())
            proc1.append(multiprocessing.Process(target=self.rx[k].run, args=(que1[k],)))
            proc1[k].start()
            k += 1 

        for i in range(self.Rxantennas):
            self.rx[i]._Z.Value=que1[i].get()
            proc1[i].join()

        for i in self.adc: 
            i.run()

    def run_rx_dsp(self):
        self.dsp.run_rx()


    #def run(self):
    #    if self.model=='py':
    #        if self.txrxmode=='tx':
    #            self.run_tx_dsp()
    #        elif sel.txrxmode=='rx':
    #            self.run_rx_dsp()
    #    elif self.model=='sv':
    #        # Verilog model does not make distinction between modes
    #        # Operation is taken care of by proper parameter settings.
    #        self.write_infile()
    #        self.run_verilog()
    #        sefl.read_outfile()


