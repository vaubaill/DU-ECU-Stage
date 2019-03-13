"""Simple GUI for DU-ECU students (educational purpose).

The goals are for the students to get familliarized with astronomical images
as well as astrometric reduction. Since most of them do not use Linux, 
experience shows they are reluctant to write command lines in Terminal.
This simple GUI is intended to run all necessary utilities (in particular SCAMP,
E. Bertin, IAP, www.astromatic.net) to perform the astrometric reduction.

Author
------
    Jeremie Vaubaillon, IMCCE, Observatoire de Paris

"""

import re
import os
import ftplib
from distutils.spawn import find_executable
import Tkinter as tk
import tkMessageBox
import tkFileDialog
from astropy.io import fits
from astropy.io.votable import parse
import logging

path=os.environ['HOME']
# link to data zip: to be updated each year
link='http://ftp.obspm.fr/outgoing/vaubaill/data4students.zip'

# setup logger
#logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
log_fmt = '%(levelname)s %(filename)s %(lineno)d (%(funcName)s) : %(message)s '
sdlr = logging.StreamHandler()
sdlr.setLevel(logging.INFO)
sdlr.setFormatter(logging.Formatter(fmt=log_fmt))
log.addHandler(sdlr)

class T120_GUI (object): 
     
    def __init__(self,path,img_file,link,datapath='data4students'):
        log.info('Start...')
        # find executable
        self.aladin=find_executable('Aladin')
        self.gedit=find_executable('gedit')
        self.scamp=find_executable('scamp')
        self.missfits=find_executable('missfits')
        allexe={'Aladin':self.aladin,
                'gedit':self.gedit,
                'scamp':self.scamp,
                'missfits':self.missfits}
        # test existence of executables
        for exe in allexe:
            if not exe:
                msg = '*** FATAL ERROR: program '+exe+' cannot be found'
                log.error(msg)
                raise IOError(msg)
        
        # set up variables
        self.link = link
        self.datapath = datapath
        self.path=os.environ['HOME']+'/'+self.datapath+'/'
        self.img_file=img_file
        self.ahead_file = ''
        
        
        # create main window
        self.root = tk.Tk()
        self.root.title("DU-ECU TP Meudon")
        # Button to open file
        self.B_open=tk.Button(text="Download data",command=lambda: self.get_file(initialdir=self.path,initialfile=self.img_file))
        # comments window
        self.FIL_S=tk.StringVar()
        self.FIL_S.set('Click to download data')
        self.FIL_L=tk.Label(self.root,text=self.FIL_S.get())
        # interface to put header information into gui:
        self.CRPIX1_L=tk.Label(self.root,text='CRPIX1=0 pixel ')
        self.CRPIX2_L=tk.Label(self.root,text='CRPIX2=0 pixel ')
        self.CRVAL1_L=tk.Label(self.root,text='CRVAL1=0 deg ')
        self.CRVAL2_L=tk.Label(self.root,text='CRVAL2=0 deg ')
        self.CRPIX1_E=tk.Entry(self.root,width=10, relief='sunken', bd=2)#, textvariable=self.CRPIX1_S.get())
        self.CRPIX2_E=tk.Entry(self.root,width=10, relief='sunken', bd=2)#, textvariable=self.CRPIX2_S.get())
        self.CRVAL1_E=tk.Entry(self.root,width=10, relief='sunken', bd=2)#, textvariable=self.CRVAL1_S.get())
        self.CRVAL2_E=tk.Entry(self.root,width=10, relief='sunken', bd=2)#, textvariable=self.CRVAL2_S.get())
        # Contrast result
        self.contrast=0.0
        self.CTR_S=tk.StringVar()
        self.CTR_S.set(str(self.contrast))
        self.CTR_L=tk.Label(self.root,text='Score='+self.CTR_S.get())
        # Button to open image with Aladin
        self.B_Aladin=tk.Button(text='Visualize Image',command=lambda: self.Aladin(),state=tk.DISABLED)
        # Button to edit scamp configuration file
        self.B_scamp_conf=tk.Button(text="Open SCAMP config",command=lambda: self.open_scamp_conf(),state=tk.DISABLED)
        # Button to run scamp
        self.B_scamp=tk.Button(text="Run astrometry",command=lambda: self.run(),state=tk.DISABLED)
        # Open header button
        self.B_header=tk.Button(text="Open Header",command=lambda: self.gedit_header(),state=tk.DISABLED)
        # Button to save header provided by scamp
        self.B_save_header=tk.Button(text="Save solution",command=lambda: self.save_header(),state=tk.DISABLED)
        # messages label
        self.MSG_S=tk.StringVar()
        self.MSG_S.set('Avant tout, ouvrez le fichier image')
        self.MSG_L=tk.Label(self.root,text=self.MSG_S.get())
        # quit button
        B_quit=tk.Button(text="Quit",command=lambda: self.Quit('Bye!'))
        # place windows and buttons
        self.B_open.grid(row=0, column=0)
        self.FIL_L.grid(row=0, column=1)
        self.CRPIX1_L.grid(row=1, column=0)
        self.CRPIX1_E.grid(row=1, column=1)
        self.CRPIX2_L.grid(row=2, column=0)
        self.CRPIX2_E.grid(row=2, column=1)
        self.CRVAL1_L.grid(row=3, column=0)
        self.CRVAL1_E.grid(row=3, column=1)
        self.CRVAL2_L.grid(row=4, column=0)
        self.CRVAL2_E.grid(row=4, column=1)
        self.CTR_L.grid(   row=4, column=4)
        self.B_Aladin.grid(     row=2, column=3)
        self.B_scamp_conf.grid( row=3, column=3)
        self.B_scamp.grid(      row=4, column=3)
        self.B_header.grid(     row=5, column=3)
        self.B_save_header.grid(row=6, column=3)
        self.MSG_L.grid(   row=0, column=2,rowspan=3,columnspan=2)
        B_quit.grid(       row=7, column=4)
        # builds window
        self.root.bind_all("<Control-c>",self.Quit)
        self.root.mainloop()
        return
    
    def change_path(self,path):
        """Change the current path.
        
        Parameters
        ----------
        Path: string
            Path name
        
        Return
        ------
        None.
        
        """
        os.chdir(path)
        log.info('now relocating to '+path)
        log.info('done')
        return
    
    def set_files(self):
        self.ldac_file          =self.path+'/'+os.path.basename(self.img_file).replace('fits','ldac')
        self.header_file        =self.path+'/'+os.path.basename(self.img_file).replace('fits','head')
        self.ahead_file         =self.path+'/scamp.ahead'
        self.scamp_config_file  =self.path+'/config.scamp.try'
        log.info('path='+self.path)
        log.info('self.img_file='+self.img_file)
        log.info('self.header_file='+self.header_file)
        log.info('self.ahead_file='+self.ahead_file)
        log.info('self.scamp_config_file='+self.scamp_config_file)
        for need_file in [self.ldac_file,self.header_file,self.ahead_file,self.scamp_config_file]:
            try:
                os.system('chmod u+rw '+need_file)
                #os.system('touch '+need_file)
                open(need_file, 'a').close()
            except:
                msg = '*** FATAL ERROR: impossible to touch file ' +need_file
                log.error(msg)
                self.Quit(msg)
                raise IOError(msg)
        
        log.info('done')
        return
    
    def Quit(self,msg):
        if self.ahead_file:
            if os.path.exists(self.ahead_file):
                log.info('Now removing ahead file: '+self.ahead_file)
                os.remove(self.ahead_file)
        log.info(msg)
        self.root.destroy()
        return
    
    def set_msg(self,msg):
        self.MSG_S.set(msg)
        self.MSG_L.configure(text=self.MSG_S.get())
        return
    
    def get_file(self,initialdir='./',initialfile='1984QY1-002-c.fits'):
        # go to HOME directory
        self.change_path(os.environ['HOME'])
        self.path = os.environ['HOME'] +'/' + self.datapath+'/'
        # upload data if they do not exist
        log.info('path: '+self.path)
        if not os.path.exists(self.path):
            log.warning(self.path+' does not exists: launching the download process')
            self.set_msg('Downloading data: WAIT!!! (or you will screw everything up...)')
        if not os.path.exists(self.path):
            #Open ftp connection
            try:
                ftp = ftplib.FTP('ftp.obspm.fr', 'anonymous','vaubaill@imcce.fr')
                ftp.cwd("outgoing/vaubaill/")
                filename='data4students.zip'
                gFile = open(filename, "wb")
                log.info('Downloading the data PLEASE WAIT...')
                ftp.retrbinary('RETR '+filename, gFile.write)
                gFile.close()
                ftp.quit()
                cmd = 'unzip '+filename
                log.info('cmd file='+cmd)
                os.system(cmd)
            except:
                msg = '*** FATAL ERROR: impossible to download data'
                log.error(msg)
                self.Quit(msg)
                #raise IOError(msg)
        else:
            log.info(self.path+'alredy exists: no need to download the data')
        # go to data directory
        self.change_path(self.path)
        
        self.img_file=tkFileDialog.askopenfilename(initialdir=self.path,initialfile=initialfile)
        self.set_files()
        self.FIL_S.set(os.path.basename(self.img_file))
        self.FIL_L.configure(text=self.FIL_S.get())
        hdulist = fits.open(self.img_file)
        hdr=hdulist[0].header
        self.CRPIX1_S=tk.StringVar()
        self.CRPIX2_S=tk.StringVar()
        self.CRVAL1_S=tk.StringVar()
        self.CRVAL2_S=tk.StringVar()
        self.CRPIX1_S.set(str(hdr['CRPIX1']))
        self.CRPIX2_S.set(str(hdr['CRPIX2']))
        self.CRVAL1_S.set(str(hdr['CRVAL1']))
        self.CRVAL2_S.set(str(hdr['CRVAL2']))
        self.set_labels()
        self.set_msg('File '+os.path.basename(self.img_file)+' successfully opened.')
        # set buttons to NORMAL
        self.B_Aladin.config(state="normal")
        self.B_scamp_conf.config(state="normal")
        self.B_scamp.config(state="normal")
        self.B_header.config(state="normal")
        self.B_save_header.config(state="normal")
        self.B_open.config(state=tk.DISABLED)
        log.info('done')
        return
        
    def set_labels(self):
        self.CRPIX1_L.configure(text='CRPIX1='+str(self.CRPIX1_S.get())+' pixel ')
        self.CRPIX2_L.configure(text='CRPIX2='+str(self.CRPIX2_S.get())+' pixel ')
        self.CRVAL1_L.configure(text='CRVAL1='+str(self.CRVAL1_S.get())+' deg ')
        self.CRVAL2_L.configure(text='CRVAL2='+str(self.CRVAL2_S.get())+' deg ')
        log.info('done')
        return
        
    def print_labels(self):
        log.info('self.CRPIX1_S='+self.CRPIX1_S.get())
        log.info('self.CRPIX2_S='+self.CRPIX2_S.get())
        log.info('self.CRVAL1_S='+self.CRVAL1_S.get())
        log.info('self.CRVAL2_S='+self.CRVAL2_S.get())
        log.info('done')
        return
        
    def retrieve(self):
        if not (self.CRPIX1_E.get()==''): self.CRPIX1_S.set(self.CRPIX1_E.get())
        if not (self.CRPIX2_E.get()==''): self.CRPIX2_S.set(self.CRPIX2_E.get())
        if not (self.CRVAL1_E.get()==''): self.CRVAL1_S.set(self.CRVAL1_E.get())
        if not (self.CRVAL2_E.get()==''): self.CRVAL2_S.set(self.CRVAL2_E.get())
        self.set_labels()
        self.print_labels()
        self.set_msg('All data were correctly retrieved.')
        log.info('done')
        return
        
    def update_scamp_ahead(self,ahead_file=''):
        # update SCAMP ahead file with data from GUI
        if (ahead_file==''):
            ahead_file=self.ahead_file
        if not os.path.exists(ahead_file):
            log.info('*** FATAL ERROR: file '+ahead_file+'does not exist')
            return
        # save the CRPIX and CRVAL in ahead file
        outahead=open(ahead_file,'w')
        outahead.write('CRPIX1  = '+self.CRPIX1_S.get()+'\n')
        outahead.write('CRPIX2  = '+self.CRPIX2_S.get()+'\n')
        outahead.write('CRVAL1  = '+self.CRVAL1_S.get()+'\n')
        outahead.write('CRVAL2  = '+self.CRVAL2_S.get()+'\n')
        outahead.close()
        self.set_msg(ahead_file+' successfully updated')
        log.info('done')
        return
    
    def open_scamp_conf(self,scamp_config_file=''):
        if not (scamp_config_file):
            scamp_config_file=self.scamp_config_file
        log.info('scamp_config_file= '+scamp_config_file)
        cmd=self.gedit+' '+scamp_config_file+ ' &'
        log.info('cmd : '+cmd)
        os.system(cmd)
        log.info('done')
        return
    
    def run_scamp(self,ldac_file='',scamp_config_file=''):
        if (ldac_file==''):
            ldac_file=self.ldac_file
        if (scamp_config_file==''):
            scamp_config_file=self.scamp_config_file
        if not os.path.exists(ldac_file):
            log.info('*** FATAL ERROR: file ',ldac_file,'does not exist')
            return
        if not os.path.exists(scamp_config_file):
            log.info('*** FATAL ERROR: file ',scamp_config_file,'does not exist')
            return
        cmd='scamp '+ldac_file+' -c '+scamp_config_file
        log.info('now running cmd='+cmd)
        os.system(cmd)
        log.info('done')
        return
    
    def retrieve_scamp(self,xml_file_name='scamp.xml',head='default.head'):
        xml_file=self.path+xml_file_name
        log.info('now reading file '+xml_file)
        votable = parse(xml_file)
        table = votable.get_first_table()
        contrastring = table.array['XY_Contrast']
        if (len(contrastring)==0): contrastring='0.0'
        self.CTR_S.set(str(contrastring))
        self.CTR_L.configure(text="Score="+self.CTR_S.get())
        self.contrast=float(contrastring)
        self.choose_msg()
        log.info('done')
        return
        
    def Aladin(self):
        # open image with Aladin
        if not os.path.exists(self.img_file):
            log.info('*** FATAL ERROR: file ',self.img_file,' does not exist')
            return
        cmd=self.aladin+' '+self.img_file+' &'
        log.info('Now opening image '+self.img_file)
        log.info('launching the command: '+cmd)
        os.system(cmd)
        log.info('done')
        return
        
    def gedit_header(self):
        # launches gedit to visualize the header file
        log.info('Now opening file '+self.header_file)
        cmd=self.gedit+' '+self.header_file+' &'
        os.system(cmd)
        log.info('done')
        return
    
    def retrieve_header(self):
        param_obj=(self.CRPIX1_S,self.CRPIX2_S,self.CRVAL1_S,self.CRVAL2_S)
        param_name=('CRPIX1','CRPIX2','CRVAL1','CRVAL2')
        cparam=[]
        for p in param_name:
            cparam.append(re.compile(p))
        log.info('now opening header file: '+self.header_file)
        hdf=open(self.header_file)
        for line in hdf:
            for (param,obj) in zip(cparam,param_obj):
                if (param.match(line)):
                    obj.set(line.split()[2])
        self.set_labels()
        log.info('done')
        return
    
    def choose_msg(self):
        all_msg=['Try again...','Better but still...','Getting there...','YEAH! See if you can do even better']
        if (self.contrast<2.0):
            self.set_msg(all_msg[0])
        elif (self.contrast<4.0):
            self.set_msg(all_msg[1])
        elif (self.contrast<6.0):
            self.set_msg(all_msg[2])
        else:
            self.set_msg(all_msg[3])
        return
    
    def save_header(self):
        saveheader=tkMessageBox.askyesno(title='Save header',
                    message='Votre Score est: '+str(self.contrast)+' Voulez-vous mettre a jour le header de l image ?')
        if saveheader:
            self.run_missfits()
            self.set_msg('Nouvelle solution ajoutee dans le header de l image')
        else:
            self.set_msg('Header unchanged, please keep trying')
        log.info('done')
        return
    
    def run_missfits(self):
        cmd='missfits -OUTFILE_TYPE SAME '+self.img_file+' &'
        if not os.path.exists(self.header_file):
            msg='*** WARNING: '+self.header_file+' does not exist'
            log.warning(cmd)
            self.set_msg(msg)
        else:
            log.info('now running cmd='+cmd)
            os.system(cmd)
        self.set_msg('done')
        log.info('done')
        return
    
    def run(self):
        self.retrieve()
        self.update_scamp_ahead()
        self.run_scamp()
        self.retrieve_scamp()
        self.retrieve_header()
        log.info('done')
        return

# Launch the GUI
img_file='1984QY1-002-c.fits'
gui=T120_GUI(path,img_file,link)
