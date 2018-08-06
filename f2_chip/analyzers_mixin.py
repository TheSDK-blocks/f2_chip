#This is a mixin class for signal analyzers to be used by f2_system class
#Todo: Analyzers should be a independent class
#Last modification by Marko Kosunen, marko.kosunen@aalto.fi, 30.07.2018 18:09
import numpy as np
import scipy.signal as sig
import matplotlib as mpl 
mpl.use('Agg') #To enble plotting without X
import matplotlib.pyplot as plt

class analyzers_mixin:
#Define signal analyzer methods    
    def oscilloscope(self,argdict):
        ymax=argdict['ymax']
        ymin=argdict['ymin']
        timex=argdict['timex']
        sigin=argdict['sigin']
        tstr=argdict['tstr']
        printstr=argdict['printstr']
        msg="Generating %s" %(printstr)
        self.print_log({'type':'I', 'msg': msg}) 

        figure=plt.figure()
        h=plt.subplot();
        hfont = {'fontname':'Sans'}
        plt.plot(timex, sigin, linewidth=2)
        plt.ylim((ymin, ymax));
        plt.xlim((np.amin(timex), np.amax(timex)));
        #plt.plot(self.x,self.a,label='Blowing in the wind',linewidth=2);
        #plt.plot(self.x,self.b,label='Blowing in the wind',linewidth=2);
        tstr=argdict['tstr']
        plt.suptitle(tstr,fontsize=20);
        plt.ylabel('Out', **hfont,fontsize=18);
        plt.xlabel('Sample (n)', **hfont,fontsize=18);
        h.tick_params(labelsize=14)
        plt.grid(True);
        printstr=argdict['printstr']
        figure.savefig(printstr, format='eps', dpi=300);
        plt.close("all")

    def constellation(self,argdict):
        ymax=argdict['ymax']
        ymin=argdict['ymin']
        I=argdict['I']
        Q=argdict['Q']
        tstr=argdict['tstr']
        printstr=argdict['printstr']
        msg="Generating %s" %(printstr)
        self.print_log({'type':'I', 'msg': msg}) 

        figure=plt.figure()
        h=plt.subplot();
        hfont = {'fontname':'Sans'}
        plt.plot(I, Q, linestyle='None', marker='x')
        plt.ylim((ymin, ymax));
        plt.ylim((1.1*np.amin(Q), 1.1*np.amax(Q)));
        plt.xlim((1.1*np.amin(I), 1.1*np.amax(I)));
        #plt.plot(self.x,self.a,label='Blowing in the wind',linewidth=2);
        #plt.plot(self.x,self.b,label='Blowing in the wind',linewidth=2);
        tstr=argdict['tstr']
        plt.suptitle(tstr,fontsize=20);
        plt.ylabel('Q', **hfont,fontsize=18);
        plt.xlabel('I', **hfont,fontsize=18);
        h.tick_params(labelsize=14)
        plt.grid(True);
        printstr=argdict['printstr']
        figure.savefig(printstr, format='eps', dpi=300);
        plt.close("all")


    def spectrum_analyzer(self, **kwargs):
        #Example argdict
        #argdict={'sig':self.signal_gen._Z.Value[i,:,0],'ymax':3, 'ymin':spectrumfloorideal,'nperseg':1024, 
        #       'tstr' : "Tx, User:%i" %(i),'printstr':"%s/F2_system_Tx_antennas_Spectrum_Rs_%i_k:%i.eps" %(self.picpath, self.Rs, i)} 
        ymax=kwargs.get('ymax',3)
        ymin=kwargs.get('ymin',-80)
        nperseg=kwargs.get('nperseg',1024) #Samples for the Welch periodogram seqment
        fs=kwargs.get('Rs',self.Rs)
        freqx=np.arange(nperseg)/nperseg*fs/1e6
        freqx.shape=(-1,1)
        sigin=kwargs['sigin']
        sigin.shape=(-1,1)
        tstr=kwargs['tstr']
        printstr=kwargs['printstr']
        msg="Generating %s" %(printstr)
        self.print_log({'type':'I', 'msg': msg}) 
        figure=plt.figure()
        h=plt.subplot();
        hfont = {'fontname':'Sans'}
        fs, spe=sig.welch(sigin,fs=self.Rs,nperseg=nperseg,return_onesided=False,scaling='spectrum',axis=0)
        spelog=10*np.log10(np.abs(spe)/np.amax(np.abs(spe)))
        plt.plot(freqx,spelog, linewidth=2 )
        #plt.setp(markerline,'markerfacecolor', 'b','linewidth',2)
        #plt.setp(stemlines, 'linestyle','solid','color','b', 'linewidth', 2)
        #plt.ylim((np.amin([self.a,self.b]), np.amax([self.a,self.b])));
        plt.ylim((ymin, ymax));
        plt.xlim((np.amin(freqx), np.amax(freqx)));
        #plt.plot(self.x,self.a,label='Blowing in the wind',linewidth=2);
        #plt.plot(self.x,self.b,label='Blowing in the wind',linewidth=2);
        plt.suptitle(tstr,fontsize=20);
        plt.ylabel('Normalized Spectrum', **hfont,fontsize=18);
        plt.xlabel('Frequency (MHz)', **hfont,fontsize=18);
        h.tick_params(labelsize=14)
        #for axis in ['top','bottom','left','right']:
        #h.spines[axis].set_linewidth(2)
        #lgd=plt.legend(loc='upper right', fontsize=14);
        ##lgd.set_fontsize(12);
        plt.grid(True);
        figure.savefig(printstr, format='eps', dpi=300);
        plt.close("all")

    def logic_analyzer(self,argdict):
        ymax=argdict['ymax']
        ymin=argdict['ymin']
        timex=argdict['timex']
        sigin=argdict['sigin']
        tstr = argdict['tstr']
        printstr=argdict['printstr']
        msg="Generating %s" %(printstr)
        self.print_log({'type':'I', 'msg': msg}) 
    
        figure=plt.figure()
        h=plt.subplot();
        hfont = {'fontname':'Sans'}
        markerline, stemlines, baseline = plt.stem(timex, sigin, '-.')
        plt.setp(markerline,'markerfacecolor', 'b','linewidth',2)
        plt.setp(stemlines, 'linestyle','solid','color','b', 'linewidth', 2)
        plt.ylim((ymin, ymax));
        plt.xlim((np.amin(timex), np.amax(timex)));
        plt.suptitle(tstr,fontsize=20);
        plt.ylabel('Out', **hfont,fontsize=18);
        plt.xlabel('Sample (n)', **hfont,fontsize=18);
        h.tick_params(labelsize=14)
        plt.grid(True);
        figure.savefig(printstr, format='eps', dpi=300);

    def evm_calculator(self,argdict):
        reference=argdict['ref']
        received=argdict['signal']
        
        #Shape the vectors: time is row observation is colum
        #if received.shape[0]<received.shape[1]:
        #    received=np.transpose(received)
        reference.shape=(-1,1)
        received.shape=(-1,1)

        #RMS for Scaling
        rmsref=np.std(reference)
        rmsreceived=np.std(received)
        EVM=10*np.log10(np.mean(np.mean(np.abs(received/rmsreceived*rmsref-reference)**2,axis=0)/np.mean(np.abs(reference)**2,axis=0)))
        self.print_log({'type':'I', 'msg':"Estimated EVM is %0.2f dB" %(EVM)})
        return EVM

    def ber_calculator(self,argdict):
        reference=argdict['ref']
        received=argdict['signal']
        
        #Shape the vectors: time is row observation is colum
        #if received.shape[0]<received.shape[1]:
        #    received=np.transpose(received)

        #reference.shape=received.shape
        reference.shape=(-1,1)
        received.shape=(-1,1)
        
        #Discard samples rounded away in transmission
        #if received.shape[1] < reference.shape[1]:
        #   reference=reference[:,0:received.shape[1]]

        errors=np.sum(np.sum(np.abs(received-reference),axis=0))/(received.shape[0]*received.shape[1])
        errors=np.sum(np.sum(np.abs(received-reference),axis=0))
        bits=(received.shape[0]*received.shape[1])
        self.print_log({'type':'I', 'msg': "Received %i errors in %i bits" %(int(errors), int(bits))})
        BER=errors/bits
        self.print_log({'type':'I', 'msg': "Resulting BER is %0.3g" %(BER)})
        return BER

#From Kosta. 
def plot_generic(x, y_list, title_str, legend_list, xlabel_str, ylabel_str, xscale, yscale, plot_style_str='o-', xlim=[], ylim=[]):
    if (xscale, yscale) == ('linear', 'linear'):
        plot_type_str = 'plot'
    elif (xscale, yscale) == ('log', 'linear'):
        plot_type_str = 'semilogx'
    elif (xscale, yscale) == ('linear', 'log'):
        plot_type_str = 'semilogy'
    elif (xscale, yscale) == ('log', 'log'):
        plot_type_str = 'loglog'
    else:
        raise Exception('xscale = %s, yscale = %s, both should be linear or log!!' % (xscale, yscale))

    fig, ax = plt.subplots() # default is 1,1,1
    if (isinstance(x[0], list)) and (len(x) == len(y_list)): # several plots with different x values
        for x, y in zip(x, y_list):
            exec('ax.' + plot_type_str + '(x, y, plot_style_str, linewidth=linewidth)')
    else:
        if (isinstance(y_list[0], list)): # several plots with the same x values
            for y in y_list:
                exec('ax.' + plot_type_str + '(x, y, plot_style_str, linewidth=linewidth)')
        else: # single plot only
            exec('ax.' + plot_type_str + '(x, y_list, plot_style_str, linewidth=linewidth)')
    if xlim != []:
        plt.xlim(xlim)
    if ylim != []:
        plt.ylim(ylim)
    ax.set_xlabel(xlabel_str, fontsize=fontsize)
    plt.ylabel(ylabel_str, fontsize=fontsize)
    if title_str == []:
        loc_y = 1.05
    else:
        plt.title(title_str, fontsize=fontsize)
        loc_y = 1
    if legend_list != []:
        plt.legend(legend_list, loc=(0, loc_y))
    plt.grid(True, which='both')
    ax.tick_params(axis='both', which='major', labelsize=fontsize)
    plt.show()


