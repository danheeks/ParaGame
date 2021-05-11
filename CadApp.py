import os
import sys
cad_dir = os.path.dirname(os.path.realpath(__file__))
pycad_dir = os.path.realpath(cad_dir + '/../PyCAD')
sys.path.append(pycad_dir)
import wx
import cad
import geom

from SolidApp import SolidApp # from CAD
from Ribbon import RB
from Ribbon import Ribbon
from Ribbon import GrayedButton

from points import Points
from points import type as points_type


class PointEditing(cad.InputMode):
    def __init__(self, front):
        cad.InputMode.__init__(self)
        # front is True or False ( for rear )
        self.front = front
        self.points = None
        
    def GetTitle(self):
        return 'Point Editing ' + ('Front' if self.front else 'Rear')
        
    def GetHelpText(self):
        return 'Drag on ' + ('Blue' if self.front else 'Red' ) + ' curve to modify it'
        
    def OnMouse(self, event):
        if event.Moving():
            if event.leftDown:
                v = wx.GetApp().GetViewport()
                p = cad.Digitize(cad.IPoint(event.x, event.y))
                self.points.ModifyAtPoint(p, self.front)

                v.need_update = True
                v.need_refresh = True
                wx.GetApp().frame.graphics_canvas.Refresh() 
                       
        if event.GetWheelRotation() != 0:
            wx.GetApp().GetViewport().OnWheelRotation(event.wheelRotation, event.x, event.y)

front_editing = PointEditing(True)
rear_editing = PointEditing(False)
    
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
        self.RegisterExportFileTypes(['points'], 'Points Files', ExportPointsFile)

    def AddExtraRibbonPages(self, ribbon):
        SolidApp.AddExtraRibbonPages(self, ribbon)
        
        save_bitmap_path = self.bitmap_path
        self.bitmap_path = cad_dir

        panel = RB.RibbonPanel(ribbon.main_page, wx.ID_ANY, 'Point', ribbon.Image('points'))
        toolbar = RB.RibbonButtonBar(panel)
        Ribbon.AddToolBarTool(toolbar,'Front', 'front', 'Edit Front Points', self.OnFrontEditButton)
        Ribbon.AddToolBarTool(toolbar,'Rear', 'rear', 'Edit Rear Points', self.OnRearEditButton)
        Ribbon.AddToolBarTool(toolbar,'Game', 'game', 'Run Game', self.OnGameButton)
        
        ribbon.main_page.Realize()

        self.bitmap_path = save_bitmap_path
        
    def OnEdit(self, front):
        editing = front_editing if front else rear_editing
        editing.points = None
        doc = cad.GetApp()
        object = doc.GetFirstChild()
        while object:
            if object.GetType() == points_type:
                editing.points = object
                break
        cad.SetInputMode(editing)
        
    def OnFrontEditButton(self, event):
        self.OnEdit(True)
        
    def OnRearEditButton(self, event):
        self.OnEdit(False)
        
    def OnGameButton(self, event):
        ExportPointFilePath('line_lengths.points')
        os.system('"C:\\Users\\Dan Heeks\\AppData\\Local\\Programs\\Python\\Python36-32\\python" game.py /i')

def ImportPointsFile():
    points = Points()
    points.points = eval( open(cad.GetFilePathForImportExport(), "r").read() )
    cad.AddUndoably(points)
    
def ExportPointFilePath(path):
    f = open(path, 'w')

    doc = cad.GetApp()
    object = doc.GetFirstChild()
    while object:
        if object.GetType() == points_type:
            f.write(str(object.points) + '\n')
        object = doc.GetNextChild()
    f.close()

def ExportPointsFile():
    ExportPointFilePath(cad.GetFilePathForImportExport())
