#This is a mixin class for system definitions to be used by f2_system class
#Last modification by Marko Kosunen, marko.kosunen@aalto.fi, 06.08.2018 18:22
from f2_signal_gen import *
from f2_channel import *
from f2_rx import *
from f2_adc import *
from f2_dac import *
from f2_dsp import *
from f2_rx_dsp import *
from f2_tx_dsp import *
from f2_serdes import *
from f2_digital_postproc import *
from f2_central_processor import *

class system_definitions_mixin:
    def define_simple_rx(self):
        #This actually has the model for beamforming
        #There can be several run configurations
        #Signal generator model here
        self.signal_gen=f2_signal_gen(self)

        #The mached filters for the symbol synchronization
        #These are considered reconfigurable
        self.Hstf=np.conj(self.signal_gen.sg802_11n._PLPCseq_short[0:64])
        self.Hstf=self.Hstf[::-1]
        self.Hltf=np.conj(self.signal_gen.sg802_11n._PLPCseq_long[0:16])
        self.Hltf=self.Hltf[::-1]

        self.signal_gen.set_transmit_power() #default 30dBm
        self.channel=f2_channel(self)
        #_Z of the channel can not be null if range assignment is done

        #Make this as an array of pointers
        self.channel.iptr_A=self.signal_gen._Z

        #rx_block
        self.rx= [f2_rx(self) for i in range(self.Rxantennas)]
        #Set the Rx models
        for i in range(self.Rxantennas):
            self.rx[i].model=self.rxmodels[i]
        self.adc=[f2_adc(self) for i in range(self.Rxantennas)]
        self.dsp=[f2_dsp(self,i) for i in range(self.Rxantennas)]

        self.serdes=f2_serdes(self)
        self.postproc=f2_digital_postproc(self)
        self.cpu=f2_central_processor(self)
        
        #[antennas,users]
        self.cpu.iptr_R_c_mat.Value=[[self.dsp[k]._channel_corr.Value[i] 
            for i in range(self.Users)] for k in range(self.Rxantennas)]
        self.cpu.iptr_channel_mat.Value=[[self.dsp[k]._channel_est.Value[i] 
            for i in range(self.Users)] for k in range(self.Rxantennas)]

        for i in range(self.Rxantennas):
            #connect rxs to channel 
            self.rx[i].iptr_A=self.channel._Z.Value[i]
            #connect adc rx 
            self.adc[i].iptr_A=self.rx[i]._Z
            self.dsp[i].iptr_A=self.adc[i]._Z

            for k in range(0,self.Users):
                #connect dsp to adcs. K dsps per antenna
                self.dsp[i].iptr_reception_vect.Value[k]=self.cpu._R_reception_mat.Value[i][k]
                
        self.postproc.iptr_A.Value=[[self.dsp[k]._symbols.Value[i] for i in range(self.Users)] for k in range(self.Rxantennas)]
        self.serdes.iptr_A=self.postproc._wordstream
    
    def define_fader2(self):
    #This is the definition for the Transceiver system
    # Aim is to make it resemple the actual circuit as closely as possible

        # One RX_path takes in multiple users and either
        # Sums the user signals or just transmits one of them
        self.tx_dsp=f2_tx_dsp(self)

        self.tx_dacs=[ f2_dac(self) for i in range(self.Txantennas) ]
        for i in range(self.Txantennas):
            self.tx_dacs[i].iptr_real_t=self.tx_dsp._Z_real_t[i]
            self.tx_dacs[i].iptr_real_b=self.tx_dsp._Z_real_b[i]
            self.tx_dacs[i].iptr_imag_t=self.tx_dsp._Z_imag_t[i]
            self.tx_dacs[i].iptr_imag_b=self.tx_dsp._Z_imag_b[i]
        #Not connected anywhere, just check if you can run the sim


        #Rx_block
        self.rx= [f2_rx(self) for i in range(self.Rxantennas)]
        #Set the Rx models
        for i in range(self.Rxantennas):
            self.rx[i].model=self.rxmodels[i]
        self.adc=[f2_adc(self) for i in range(self.Rxantennas)]
        #Since tapein6, the DSP is a single entity with Rxantennas inputs
        self.rx_dsp=f2_rx_dsp(self)

        self.serdes=f2_serdes(self)
        self.serdes.Users=1 #We use only 1 user coming out of the dsp (data is the same)
        #No cpu

        for i in range(self.Rxantennas):
            #connect adc rx 
            self.adc[i].iptr_A=self.rx[i]._Z
            self.rx_dsp.iptr_A.Value[i]=self.adc[i]._Z

        #Do not need postprocessing any more
        self.serdes.iptr_A=self.rx_dsp._decimated

