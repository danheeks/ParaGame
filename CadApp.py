import os
import sys
cad_dir = os.path.dirname(os.path.realpath(__file__))
pycad_dir = os.path.realpath(cad_dir + '/../PyCAD')
sys.path.append(pycad_dir)
import wx
import cad

from SolidApp import SolidApp # from CAD
from Ribbon import RB
from Ribbon import Ribbon

class CadApp(SolidApp):
    def __init__(self):
        self.cad_dir = cad_dir
        SolidApp.__init__(self)
        
    def GetAppTitle(self):
        return 'ParaGame Point List Editing Software'
       
    def GetAppConfigName(self):
        return 'ParaGameCAD'
 
    def RegisterObjectTypes(self):
        SolidApp.RegisterObjectTypes(self)
        self.RegisterImportFileTypes(['points'], 'Points Files', ImportPointsFile)

def ImportPointsFile():
    wx.MessageBox('points')