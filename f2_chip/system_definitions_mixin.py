#This is a mixin class for system definitions to be used by f2_system class
#Last modification by Marko Kosunen, marko.kosunen@aalto.fi, 15.08.2018 10:51
from f2_util_classes import *
from f2_signal_gen import *
from f2_channel import *
from f2_rx import *
from f2_adc import *
from segmented_dac import *
from f2_dsp import *
#from f2_rx_dsp import *
#from f2_tx_dsp import *
from f2_dsp_2019 import *
from f2_serdes import *
from f2_digital_postproc import *
from f2_central_processor import *


class system_definitions_mixin:
   pass 

        #Do not need postprocessing any more
        #self.serdes.iptr_A=self.rx_dsp._decimated
#    def define_simple_rx(self):
#        #This actually has the model for beamforming
#        #There can be several run configurations
#        #Signal generator model here
#        self.signal_gen=f2_signal_gen(self)
#
#        #The mached filters for the symbol synchronization
#        #These are considered reconfigurable
#        self.Hstf=np.conj(self.signal_gen.sg802_11n._PLPCseq_short[0:64])
#        self.Hstf=self.Hstf[::-1]
#        self.Hltf=np.conj(self.signal_gen.sg802_11n._PLPCseq_long[0:16])
#        self.Hltf=self.Hltf[::-1]
#
#        self.signal_gen.set_transmit_power() #default 30dBm
#        self.channel=f2_channel(self)
#        #_Z of the channel can not be null if range assignment is done
#
#        #Make this as an array of pointers
#        self.channel.iptr_A=self.signal_gen._Z
#
#        #rx_block
#        self.rx= [f2_rx(self) for i in range(self.Rxantennas)]
#        #Set the Rx models
#        for i in range(self.Rxantennas):
#            self.rx[i].model=self.rxmodels[i]
#        self.adc=[f2_adc(self) for i in range(self.Rxantennas)]
#        self.dsp=[f2_dsp(self,i) for i in range(self.Rxantennas)]
#
#        self.serdes=f2_serdes(self)
#        self.postproc=f2_digital_postproc(self)
#        self.cpu=f2_central_processor(self)
#        
#        #[antennas,users]
#        self.cpu.iptr_R_c_mat.Data=[[self.dsp[k]._channel_corr.Data[i] 
#            for i in range(self.Users)] for k in range(self.Rxantennas)]
#        self.cpu.iptr_channel_mat.Data=[[self.dsp[k]._channel_est.Data[i] 
#            for i in range(self.Users)] for k in range(self.Rxantennas)]
#
#        for i in range(self.Rxantennas):
#            #connect rxs to channel 
#            self.rx[i].iptr_A=self.channel._Z.Data[i]
#            #connect adc rx 
#            self.adc[i].iptr_A=self.rx[i]._Z
#            self.dsp[i].iptr_A=self.adc[i]._Z
#
#            for k in range(0,self.Users):
#                #connect dsp to adcs. K dsps per antenna
#                self.dsp[i].iptr_reception_vect.Data[k]=self.cpu._R_reception_mat.Data[i][k]
#                
#        self.postproc.iptr_A.Data=[[self.dsp[k]._symbols.Data[i] for i in range(self.Users)] for k in range(self.Rxantennas)]
#        self.serdes.iptr_A=self.postproc._wordstream

