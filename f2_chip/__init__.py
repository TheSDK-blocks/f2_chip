#from joblib import Parallel, delayed
import numpy as np
from thesdk import *
import multiprocessing
from functools import reduce
from f2_signal_gen import *
from f2_chip.system_definitions_mixin import system_definitions_mixin
from f2_chip.analyzers_mixin import analyzers_mixin

class f2_chip(thesdk,system_definitions_mixin,analyzers_mixin):
    Rs=160e6      #Baseband sampling frequency
    Rs_dsp=20e6      #Baseband sampling frequency
    frequency=1e9 #Rf center frequency 

    #Baseband signal dictionaries are used to control the signal generator
    #-----Sinusoidal test signals
    # Check if working. Receiver is now fiexed to OFDM
    bbsigdict_sinusoid={ 'mode':'sinusoid', 'freqs':[1.0e6 ], 'length':2**14, 'BBRs':40e6 };
    bbsigdict_sinusoid3= { 'mode':'sinusoid', 'freqs':[1.0e6 , 3e6, 7e6 ], 'length':2**14, 'BBRs':20e6 };
    bbsigdict_ofdm_sinusoid3={ 'mode':'ofdm_sinusoid', 'freqs':[-7.0e6 , 2e6, 5e6 ], 'length':2**14, 'BBRs':20e6 };
    
    #-----Data signals
    bbsigdict_randombitstream_QAM4_OFDM={ 'mode':'ofdm_random_qam', 'QAM':4, 'length':2**14, 'BBRs': 20e6 };

    bbsigdict_802_11n_random_QAM16_OFDM={ 'mode':'ofdm_random_802_11n', 'QAM':16, 'length':2**14, 'BBRs': 20e6 };

    #Channel dictionaries are used to16control the channel model
    channeldict_buffer= { 'model': 'lossless' , 'frequency': 1e9 }
    channeldict_buffer_1km= { 'model': 'lossless', 'frequency': 1e9, 'distance': 1000}
    #channeldict_lossless_awgn= { 'model': 'awgn', 'frequency': 1e9, 'bandwidth': 100e6, 'distance': 0 }

    channeldict_802_11n_A= { 'model': 'A',  'distance': 1000}
    channeldict_802_11n_B= { 'model': 'B',  'distance': 1000}
    channeldict_802_11n_C= { 'model': 'C',  'distance': 1000}
    channeldict_802_11n_D= { 'model': 'D',  'distance': 1000}
    channeldict_802_11n_E= { 'model': 'E',  'distance': 1000}
    channeldict_802_11n_F= { 'model': 'F',  'distance': 1000}


    def __init__(self,*arg):
        self.picpath=[]
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
        self.Rs=f2_chip.Rs
        self.Rs_dsp=f2_chip.Rs_dsp
                           #Synchronization filter
        self.Hstf=1                             #Synchronization filter
        self.ofdmdict=ofdm64dict_withguardband  #Guard-banded frames as default
        self.bbsigdict=bbsigdict_802_11n_random_QAM16_OFDM
        self.channeldict=f2_chip.channeldict_802_11n_C
        self.signal_gen=[]
        self.channel=[]
        self.rx=[]
        self.adc=[]
        self.dsp=[]
        self.tx=[]
        self.serdes=[]
        selflDEBUG= False
        if len(arg)>=1:
            parent=arg[0]
            self.logfile=arg[1]['logfile']
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
        self.signal_gen_tx.init()
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

        self.rx_dsp.init()
        self.rx_dsp.run()

        self.serdes.init()
        self.serdes.run()


    def analyze_simple(self):
        timex = np.array(range(0,10000))
        spectrumfloor=-40
        spectrumfloorideal=-75
        #Plot signal generator outputs
        ymax=np.amax(np.amax(np.amax(np.absolute(np.real(self.signal_gen._Z.Value)))))
        for k in range(self.Users):
            argdict={'I'       :np.real(self.signal_gen._qam_reference[k,:]), 
                     'Q'       :np.imag(self.signal_gen._qam_reference[k,:]),
                     'ymax'    :1.1*np.max(np.abs(np.real(self.signal_gen._qam_reference[k,:]))),
                     'ymin'    :-1.1*np.max(np.abs(np.imag(self.signal_gen._qam_reference[k,:]))), 
                     'tstr'    : "QAM data, Usr=%i" %(k),
                     'printstr':"%s/F2_system_QAM_reference_Rs_%i_k=%i.eps" %(self.picpath, self.Rs,k)}
            self.constellation(argdict)

            argdict={'timex'   :timex,
                     'sigin'   :np.real(self.signal_gen._Z.Value[k,timex,0]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr'    :"Tx, User=%i" %(k),
                     'printstr':"%s/F2_system_Tx_antennas_Rs_%i_k=%i.eps" %(self.picpath, self.Rs, k)}
            self.oscilloscope(argdict)

            #Spectrum
        for i in range(self.Users):
            argdict={'sigin':self.signal_gen._Z.Value[i,:,0],
                     'ymax':3, 
                     'ymin':spectrumfloorideal,
                     'nperseg':1024, 
                     'tstr' : "Tx, User:%i" %(i),
                     'printstr':"%s/F2_system_Tx_antennas_Spectrum_Rs_%i_k=%i.eps" %(self.picpath, self.Rs, i)} 
            self.spectrum_analyzer(**argdict)

        #Plot Rx inputs
        ymax=0
        for i in range(self.Rxantennas):
            ymax=np.amax([ymax, np.amax(np.amax(np.absolute(np.real(self.rx[i].iptr_A.Value))))])

        for i in range(len(self.rx)):
            argdict={'timex'   :timex, 
                     'sigin'   :np.real(self.rx[i].iptr_A.Value[timex]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr' : "Rx, Ant=%i" %(i), 
                     'printstr':"%s/F2_system_Antenna_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.oscilloscope(argdict)


            #Spectrum
        for i in range(self.Rxantennas):
            argdict={'sigin':self.rx[i].iptr_A.Value,
                     'ymax':3, 
                     'ymin':spectrumfloorideal,
                     'nperseg':1024, 
                     'tstr' : "Rx, Ant=%i" %(i), 
                     'printstr':"%s/F2_system_Antenna_Spectrum_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.spectrum_analyzer(**argdict)

        #Plot the rx output signals
        ymax=0
        for i in range(self.Rxantennas):
            ymax=np.amax([ymax, np.amax(np.amax(np.absolute(np.real(self.rx[i]._Z.Value))))])
        for i in range(len(self.rx)):
            argdict={'timex'   :timex, 
                     'sigin'   :np.real(self.rx[i]._Z.Value[timex]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr'    :"Rx, rxm=%s, Ant=%i" %(self.rx[i].model,i),
                     'printstr':"%s/F2_system_Rx_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i) }
            self.oscilloscope(argdict)


            #Spectrum
        for i in range(self.Rxantennas):
            argdict={'sigin':self.rx[i]._Z.Value,
                     'ymax':3, 
                     'ymin':spectrumfloorideal,
                     'nperseg':1024, 
                     'tstr' : "Rx, Rx=%i" %(i), 
                     'printstr':"%s/F2_system_Rx_Spectrum_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.spectrum_analyzer(**argdict)

        #Plot the Adc output signals
        ymax=0
        for i in range(self.Rxantennas):
            ymax=np.amax([ymax, np.amax(np.amax(np.absolute(np.real(self.adc[i]._Z.Value))))])

        for i in range(len(self.adc)):
            argdict={'timex'   :timex, 
                     'sigin'   :np.real(self.adc[i]._Z.Value[timex]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr'    :"ADC, adcm=%s, Ant=%i" %(self.adc[i].model,i),
                     'printstr': "%s/F2_system_ADC_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)} 
            self.oscilloscope(argdict)

            argdict={'sigin':self.adc[i]._Z.Value,
                     'ymax':3, 
                     'ymin':spectrumfloorideal,
                     'nperseg':1024, 
                     'tstr' : "ADC, Rx=%i" %(i), 
                     'printstr':"%s/F2_system_ADC_Spectrum_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.spectrum_analyzer(**argdict)

        #Plot dsp and serdes
        ymax=0
        ymaxfsyncl=0
        ymaxfsyncs=0
        syncrange=np.array(range(0,700))
        for i in range(self.Rxantennas):
            for k in range(self.Users):
                ymax=np.amax([ymax,np.amax(np.absolute(np.real(self.serdes._Z.Value[timex,k])))])

        for i in range(self.Rxantennas):
            ymaxfsyncs=np.amax([ymaxfsyncs,np.amax(np.absolute(self.dsp[i]._Frame_sync_short.Value[syncrange]))])
            ymaxfsyncl=np.amax([ymaxfsyncl,np.amax(np.absolute(self.dsp[i]._Frame_sync_long.Value[syncrange]))])

        for i in range(self.Rxantennas):
            argdict={'timex'   :syncrange,
                     'sigin'   :np.real(self.dsp[i]._Frame_sync_short.Value[syncrange]),
                     'ymax'    :1.1*ymaxfsyncs,
                     'ymin'    :0, 
                     'tstr'    : "DSP Framesync short, Ant=%i, model %s" %(i, self.dsp[i].model),
                     'printstr':"%s/F2_system_DSP_Fsync_short_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.oscilloscope(argdict)

            argdict={'timex'   :syncrange,
                     'sigin'   :self.dsp[i]._Frame_sync_long.Value[syncrange],
                     'ymax'    :1.1*ymaxfsyncl,
                     'ymin'    :0, 
                     'tstr'    : "DSP Framesync long, Ant=%i, model %s" %(i, self.dsp[i].model),
                     'printstr':"%s/F2_system_DSP_Fsync_long_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.oscilloscope(argdict)

        for i in range(self.Rxantennas):
            for k in range(self.Users):
                l=np.amin([self.signal_gen._qam_reference.shape[1], self.dsp[i]._symbols.Value[k].Value.shape[0]])
                EVM=self.evm_calculator({'ref':self.signal_gen._qam_reference[k,0:l],'signal':self.dsp[i]._symbols.Value[k].Value[0:l]})
                l=np.amin([self.signal_gen._bitstream_reference.shape[1], self.dsp[i]._bitstream.Value[k].Value.shape[0]])
                BER=self.ber_calculator({'ref':self.signal_gen._bitstream_reference[k,0:l],'signal':self.dsp[i]._bitstream.Value[k].Value[0:l]})
                argdict={'I'       :np.real(self.dsp[i]._symbols.Value[k].Value), 
                         'Q'       :np.imag(self.dsp[i]._symbols.Value[k].Value),
                         'ymax'    :1.1*ymax,
                         'ymin'    :-1.1*ymax, 
                         'tstr'    : "DSP, Ant=%i, Usr=%i, %s, EVM=%0.2f dB, BER= %0.3g" %(i, k, self.dsp[i].model, EVM,BER),
                         'printstr':"%s/F2_system_DSP_Rs_%i_m=%i_k=%i.eps" %(self.picpath, self.Rs, i,k)}
                self.constellation(argdict)


        for k in range(self.Users):
            l=np.amin([self.signal_gen._qam_reference.shape[1], self.postproc._symbols.Value.shape[0]])
            EVM=self.evm_calculator({'ref':self.signal_gen._qam_reference[k,0:l],'signal':self.postproc._symbols.Value[0:l,k]})
            l=np.amin([self.signal_gen._bitstream_reference.shape[1], self.postproc._bitstream.Value.shape[0]])
            BER=self.ber_calculator({'ref':self.signal_gen._bitstream_reference[k,0:l],'signal':self.postproc._bitstream.Value[0:l,k]})
            argdict={'I'       :np.real(self.postproc._symbols.Value[:,k]), 
                    'Q'       :np.imag(self.postproc._symbols.Value[:,k]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr'    : "Postproc, Usr=%i, %s, EVM=%0.2f dB, BER= %0.3g" %(k, self.postproc.model, EVM,BER),
                     'printstr':"%s/F2_system_Postproc_Rs_%i_k=%i.eps" %(self.picpath, self.Rs,k)}
            self.constellation(argdict)


            argdict={'timex'   :timex, 
                     'sigin'   :self.serdes._Z.Value[timex,k],
                     'ymax'    :1.1*ymax,
                     'ymin'    :0, 
                     'tstr'    : "Serdes, %s, Usr=%i" %(self.serdes.model,k),
                     'printstr':"%s/F2_system_serdes_Rs_%i_k=%i.eps" %(self.picpath, self.Rs,k)} 
            self.oscilloscope(argdict)

    def analyze_rx_dsp(self):
        timex = np.array(range(0,10000))
        
        spectrumfloor=-40
        spectrumfloorideal=-75

        #Plot signal generator outputs
        ymax=np.amax(np.amax(np.amax(np.absolute(np.real(self.signal_gen_rx._Z.Value)))))
        for k in range(self.Users):
            argdict={'timex'   :timex,
                     'sigin'   :np.real(self.signal_gen_rx._Z.Value[k,timex,0]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr'    :"Tx, User=%i" %(k),
                     'printstr':"%s/F2_system_Tx_antennas_Rs_%i_k=%i.eps" %(self.picpath, self.Rs, k)}
            self.oscilloscope(argdict)

            #Spectrum
        for i in range(self.Users):
            argdict={'sigin':self.signal_gen_rx._Z.Value[i,:,0],
                     'ymax':3, 
                     'ymin':spectrumfloorideal,
                     'nperseg':1024, 
                     'tstr' : "Tx, User:%i" %(i),
                     'printstr':"%s/F2_system_Tx_antennas_Spectrum_Rs_%i_k=%i.eps" %(self.picpath, self.Rs, i)} 
            self.spectrum_analyzer(**argdict)

        #Plot Rx inputs
        ymax=0
        for i in range(self.Rxantennas):
            ymax=np.amax([ymax, np.amax(np.amax(np.absolute(np.real(self.rx[i].iptr_A.Value))))])

        for i in range(len(self.rx)):
            argdict={'timex'   :timex, 
                     'sigin'   :np.real(self.rx[i].iptr_A.Value[timex]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr' : "Rx, Ant=%i" %(i), 
                     'printstr':"%s/F2_system_Antenna_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.oscilloscope(argdict)


            #Spectrum
        for i in range(self.Rxantennas):
            argdict={'sigin':self.rx[i].iptr_A.Value,
                     'ymax':3, 
                     'ymin':spectrumfloorideal,
                     'nperseg':1024, 
                     'tstr' : "Rx, Ant=%i" %(i), 
                     'printstr':"%s/F2_system_Antenna_Spectrum_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.spectrum_analyzer(**argdict)

        #Plot the rx output signals
        ymax=0
        for i in range(self.Rxantennas):
            ymax=np.amax([ymax, np.amax(np.amax(np.absolute(np.real(self.rx[i]._Z.Value))))])
        for i in range(len(self.rx)):
            argdict={'timex'   :timex, 
                     'sigin'   :np.real(self.rx[i]._Z.Value[timex]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr'    :"Rx, rxm=%s, Ant=%i" %(self.rx[i].model,i),
                     'printstr':"%s/F2_system_Rx_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i) }
            self.oscilloscope(argdict)


            #Spectrum
        for i in range(self.Rxantennas):
            argdict={'sigin':self.rx[i]._Z.Value,
                     'ymax':3, 
                     'ymin':spectrumfloorideal,
                     'nperseg':1024, 
                     'tstr' : "Rx, Rx=%i" %(i), 
                     'printstr':"%s/F2_system_Rx_Spectrum_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.spectrum_analyzer(**argdict)

        #Plot the Adc output signals
        ymax=0
        for i in range(self.Rxantennas):
            ymax=np.amax([ymax, np.amax(np.amax(np.absolute(np.real(self.adc[i]._Z.Value))))])

        for i in range(len(self.adc)):
            argdict={'timex'   :timex, 
                     'sigin'   :np.real(self.adc[i]._Z.Value[timex]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr'    :"ADC, adcm=%s, Ant=%i" %(self.adc[i].model,i),
                     'printstr': "%s/F2_system_ADC_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)} 
            self.oscilloscope(argdict)

            argdict={'sigin':self.adc[i]._Z.Value,
                     'ymax':3, 
                     'ymin':spectrumfloorideal,
                     'nperseg':1024, 
                     'tstr' : "ADC, Rx=%i" %(i), 
                     'printstr':"%s/F2_system_ADC_Spectrum_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.spectrum_analyzer(**argdict)


        ##Plot dsp and serdes outputs
        ymax=0
        k=0
        for i in range(self.Rxantennas):
                ymax=np.amax([ymax,np.amax(np.absolute(np.real(self.serdes._Z.Value[i].Value)))])

        ##Plot the DSP output signals
        for i in range(4):
            argdict={'timex'   :timex, 
                     'sigin'   :np.real(self.rx_dsp._decimated.Value[i].Value[timex]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr'    :"DSP, dspmodel=%s, Ant=%i" %(self.rx_dsp.model,i),
                     'printstr': "%s/F2_system_DSP_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)} 
            self.oscilloscope(argdict)

            argdict={'sigin':self.rx_dsp._decimated.Value[i].Value  ,
                     'ymax'    :3, 
                     'ymin'    :spectrumfloorideal,
                     'Rs'      :self.Rs_dsp,
                     'nperseg' :1024, 
                     'tstr'    : "DSP, Rx=%i" %(i), 
                     'printstr':"%s/F2_system_DSP_Spectrum_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.spectrum_analyzer(**argdict)

            argdict={'timex'   :timex, 
                     'sigin'   :np.real(self.serdes._Z.Value[i].Value[timex]),
                     'ymax'    :1.1*ymax,
                     'ymin'    :-1.1*ymax, 
                     'tstr'    : "Serdes, %s, Ant=%i" %(self.serdes.model,i),
                     'printstr':"%s/F2_system_serdes_Rs_%i_m=%i.eps" %(self.picpath, self.Rs,i)} 
            self.oscilloscope(argdict)

            argdict={'sigin'   :self.serdes._Z.Value[i].Value,
                     'ymax'    :3, 
                     'ymin'    :spectrumfloorideal,
                     'Rs'      :self.Rs_dsp,
                     'nperseg' :1024, 
                     'tstr'    : "Serdes, Rx=%i" %(i), 
                     'printstr':"%s/F2_system_serdes_Spectrum_Rs_%i_m=%i.eps" %(self.picpath, self.Rs, i)}
            self.spectrum_analyzer(**argdict)
        
 
#Define simple dac here
    #def dac(self,argdict)
        #thermo=argdict['thermo']
        #bin=argdict['bin']
        #sigin=argdict['sigin']
        ##Format of one user
        ##thermo_real bin_real thermo_imag bin_imag
        ##this is pseudocode needto ch3eck the output data format
        #dac_out=np.sum(thermo_real)+bin_real+1j*(np.sum(thermo_imag)+bin_imag)
        pass

