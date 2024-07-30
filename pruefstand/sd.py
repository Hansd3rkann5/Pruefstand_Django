import time
import random
import json
import sys, os
import tkinter as tk
import threading
import pythoncom
from django.http import JsonResponse
from threading import Thread
from channels.generic.websocket import WebsocketConsumer
from win32com.client import Dispatch
from win32com.client.connect import *

#Klasse für Kommunikation zwischen Server und Client
class ChatConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False 
        self.hallcount_ist = 0
        self.hallcount_max = 0
        self.pos = 0
        self.Value = 0

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        self.running = False

    #Alle Funktionen für die Kommunikation zwischen Client und Server
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        task = text_data_json["task"]
        if task == "start":
            message = text_data_json["message"]
            controldesk().get_derivat()
            if message == "tf_ohne":
                self.show_hkl()
            if message == "tf_mit":
                self.show_tg()
        
        #Alle Funktionen, die für die Heckklappe ausgeführt werden
        if task == "hkl":
            message = text_data_json["message"]
            if message == "switch_block":
                status = controldesk().get_block_manu_stat("hkl", "block")
                if status == 1:
                    time.sleep(0.1)
                    self.send(text_data=json.dumps({"check": "on_hkl_block"}))
                if status == 0:
                    time.sleep(0.1)
                    self.send(text_data=json.dumps({"check": "off_hkl_block"}))
            if message == "switch_manu":
                status = controldesk().get_block_manu_stat("hkl", "manuell")
                if status == 1:
                    time.sleep(0.1)
                    self.send(text_data=json.dumps({"check": "on_hkl_manu"}))
                if status == 0:
                    time.sleep(0.1)
                    self.send(text_data=json.dumps({"check": "off_hkl_manu"}))
            message = text_data_json["message"]
            if message == "on_block":
                try:
                    Value = controldesk().block_manu_ON("hkl", "block")
                    if Value == 1:
                        self.send(text_data=json.dumps({"check": "on_hkl_block"}))
                except Exception as e:
                    self.show_error(e)
            if message == "off_block":
                try:
                    Value = controldesk().block_manu_OFF("hkl", "block")
                    if Value == 0:
                        self.send(text_data=json.dumps({"check": "off_hkl_block"}))
                except Exception as e:
                    self.show_error(e)
            if message == "on_manu":
                try:
                    Value = controldesk().block_manu_ON("hkl", "manuell")
                    if Value == 1:
                        self.send(text_data=json.dumps({"check": "on_hkl_manu"}))
                except Exception as e:
                    self.show_error(e)
            if message == "off_manu":
                try:
                    Value = controldesk().block_manu_OFF("hkl", "manuell")
                    if Value == 0:
                        self.send(text_data=json.dumps({"check": "off_hkl_manu"}))
                except Exception as e:
                    self.show_error(e)
        
        #Alle Funktionen, die für das Tailgate ausgeführt werden
        if task == "tg":
            message = text_data_json["message"]
            if message == "switch_block":
                status = controldesk().get_block_manu_stat("tg", "block")
                if status == 1:
                    time.sleep(0.1)
                    self.send(text_data=json.dumps({"check": "on_tg_block"}))
                if status == 0:
                    time.sleep(0.1)
                    self.send(text_data=json.dumps({"check": "off_tg_block"}))
            if message == "switch_manu":
                status = controldesk().get_block_manu_stat("tg", "manuell")
                if status == 1:
                    time.sleep(0.1)
                    self.send(text_data=json.dumps({"check": "on_tg_manu"}))
                if status == 0:
                    time.sleep(0.1)
                    self.send(text_data=json.dumps({"check": "off_tg_manu"}))
            message = text_data_json["message"]
            if message == "on_block":
                try:
                    Value = controldesk().block_manu_ON("tg", "block")
                    if Value == 1:
                        self.send(text_data=json.dumps({"check": "on_tg_block"}))
                except Exception as e:
                    self.show_error(e)
            if message == "off_block":
                try:
                    Value = controldesk().block_manu_OFF("tg", "block")
                    if Value == 0:
                        self.send(text_data=json.dumps({"check": "off_tg_block"}))
                except Exception as e:
                    self.show_error(e)
            if message == "on_manu":
                try:
                    Value = controldesk().block_manu_ON("tg", "manuell")
                    if Value == 1:
                        self.send(text_data=json.dumps({"check": "on_tg_manu"}))
                except Exception as e:
                    self.show_error()
            if message == "off_manu":
                try:
                    Value = controldesk().block_manu_OFF("tg", "manuell")
                    if Value == 0:
                        self.send(text_data=json.dumps({"check": "off_tg_manu"}))
                except Exception as e:
                    self.show_error(e)
        
        #Alle Funktionen im Zusammenhang mit Umstellung zwischen BLOCK und MANUELL in Controldesk
        if task == "hkl_hall_manu":
            message = text_data_json["message"]
            controldesk().hkl_set_hallcount(message, "manuell")
        if task == "tg_hall_manu":
            message = text_data_json["message"]
            controldesk().tg_set_hallcount(message, "manuell")
        if task == "hkl_hall_block":
            message = text_data_json["message"]
            controldesk().hkl_set_hallcount(message, "block")
        if task == "tg_hall_block":
            message = text_data_json["message"]
            controldesk().tg_set_hallcount(message, "block")
        
        #Übergabe der Anwenderauswahl für Derivat und ECU
        if task == "set_der_tg":
            message = text_data_json["message"]
            controldesk().set_derivat(int(message))
            controldesk().set_ecu("tg", 1)
        if task == "set_der_hkl":
            message = text_data_json["message"]
            controldesk().set_derivat(int(message))
        if task == "set_ecu":
            message = text_data_json["message"]
            controldesk().set_ecu("hkl", int(message))
        
        #Stopt die Übertragung der Öffnungsdaten von Server zu Client
        elif task == "stop":
            self.stop()

    #Abfrage des Öffnungswinkels der Heckklappe
    def get_hkl(self):
        while self.running:
            pos_hkl = round(controldesk().hkl_get_hall())
            buzz = controldesk().show_buzzer()
            self.send(text_data=json.dumps({"hkl": pos_hkl}))
            if buzz == "buzz":
                self.send(text_data=json.dumps({"buzz": "on"}))
            time.sleep(0.01)
    
    #Start für Periodische Abfrage des Öffnungswinkels der Heckklappe
    def show_hkl(self):
        self.running = True
        self.runner = Thread(target=self.get_hkl, name="runlocalscript")
        self.runner.start()
        self.send(text_data=json.dumps({"message": "starting"}))

    #Abfrage des Öffnungswinkels für Testfall mit Tailgate
    def get_tg(self):
        while self.running:
            pos_hkl = round(controldesk().hkl_get_hall())
            pos_tg = round(controldesk().tg_get_hall())
            buzz = controldesk().show_buzzer()
            if buzz == "buzz":
                self.send(text_data=json.dumps({"buzz": "on"}))
            self.send(text_data=json.dumps({"hkl": pos_hkl, "tg": pos_tg}))
            time.sleep(0.01)

    #Start für periodische Abfrage des Öffnungswinkels für Tailgate und Heckklappe
    def show_tg(self):
        self.running = True
        self.runner = Thread(target=self.get_tg, name="runlocalscript")
        self.runner.start()
        self.send(text_data=json.dumps({"message": "starting"}))

    #Stopt die periodische Abfrage
    def stop(self):
        self.running = False

    #Zeigt eventuelle Fehler mit Zeilenangabe an
    def show_error(self, exception):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno, exception)


#Klasse, in der die Kommunikation mit Controldesk stattfindet
class controldesk():
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.AppCD = Dispatch("ControlDeskNG.Application", pythoncom.CoInitialize())
        self.hkl_hallCounts_ist = self.AppCD.LayoutManagement.Layouts["Basis_User"].Instruments["Display_3816_4717"]                        
        self.tg_hallCounts_ist = self.AppCD.LayoutManagement.Layouts["Basis_User"].Instruments["Display_3816_4145"]
        self.hkl_hallCounts_max = 1
        self.tg_hallCounts_max = 1
        self.block_choose = 0
        self.buzzer = self.AppCD.LayoutManagement.Layouts["Basis_User"].Instruments["Display_4187"]
        self.manu_Tailgate = self.AppCD.LayoutManagement.Layouts["Blockieren"].Instruments["ManuellTailgate"]
        self.block_Tailgate = self.AppCD.LayoutManagement.Layouts["Blockieren"].Instruments["BlockTailgate"]
        self.manu_HKL = self.AppCD.LayoutManagement.Layouts["Blockieren"].Instruments["ManuellHKL"]
        self.block_HKL = self.AppCD.LayoutManagement.Layouts["Blockieren"].Instruments["BlockHKL_4582"]
        self.Derivat = self.AppCD.LayoutManagement.Layouts["Basis_User"].Instruments["MultiState Display_3688_3694_3695_3699_4067_7885"]
        self.hkl_set_manu = self.AppCD.LayoutManagement.Layouts["Blockieren"].Instruments["Numeric Input_4583_4585"]
        self.hkl_set_block = self.AppCD.LayoutManagement.Layouts["Blockieren"].Instruments["Numeric Input_4583"]
        self.tg_set_manu = self.AppCD.LayoutManagement.Layouts["Blockieren"].Instruments["Numeric Input_4583_4584_4586"]
        self.tg_set_block = self.AppCD.LayoutManagement.Layouts["Blockieren"].Instruments["Numeric Input_4583_4584"]
        self.derivat = self.AppCD.LayoutManagement.Layouts["Basis_User"].Instruments["Push Button_4066_7884"]
        self.ecu = self.AppCD.LayoutManagement.Layouts["Basis_User"].Instruments["Push Button_4066_4069_4642"]

    #Setzen der Derivatsauswahl des Anwenders in Controldesk
    def set_derivat(self, derivat):
        try:
            val_derivat = self.derivat.Value
            self.derivat.ValueAdjustment.Add(-val_derivat+derivat)
        except Exception as e:
            print(f"Fehler: {e}")

    #Setzen der ECU-auswahl des Anwenders in Controldesk
    def set_ecu(self, job, ecu):
        try:
            if job == 'hkl':
                val_ecu = self.ecu.Value
                self.ecu.ValueAdjustment.Add(-val_ecu+ecu)
            else:
                val_ecu = self.ecu.Value
                self.ecu.ValueAdjustment.Add(-val_ecu+1)
        except Exception as e:
            print(f"Fehler: {e}")    

    #Abfrage der Derivatsauswahl in Controldesk und setzen der individuellen Hallcounts für HKL und Tailgate
    def get_derivat(self):
        derivat = self.Derivat.Value
        if derivat == 1:
            #G60
            self.hkl_hallCounts_max = 1487
            self.tg_hallCounts_max = 750
        if derivat == 2:
            #RR25
            self.hkl_hallCounts_max = 1300
        if derivat == 3:
            #G07
            self.hkl_hallCounts_max = 1099
            self.tg_hallCounts_max = 750
        if derivat == 4:
            #I20
            pass
        if derivat == 5:
            #U06
            pass
        if derivat == 6:
            #U11
            pass
        if derivat == 7:
            #G70
            self.hkl_hallCounts_max = 1280
        if derivat == 8:
            #G09
            self.hkl_hallCounts_max = 1513
            self.tg_hallCounts_max = 750
        if derivat == 9:
            #G05
            self.hkl_hallCounts_max = 969
            self.tg_hallCounts_max = 750
        if derivat == 10:
            #G06
            self.hkl_hallCounts_max = 1525
            self.tg_hallCounts_max = 750
        if derivat == 11:
            #F70
            self.hkl_hallCounts_max = 1471
        if derivat == 12:
            #U25
            pass
        if derivat == 13:
            #U10
            pass
        if derivat == 14:
            #G45
            self.hkl_hallCounts_max = 1824
        if derivat == 15:
            #G61
            self.hkl_hallCounts_max = 1350

    #Überprüfung des BuzzerDutyCalls bei Betätigung der Heckklappe mit Fußkick
    def show_buzzer(self):
        buzzer = self.buzzer.Value
        if buzzer != 0:
            return "buzz"
        return "no buzz"

    #
    def hkl_block(self):
        self.block_choose = 1

    #Abfrage des Status für BLOCK und MANUELL (ON oder OFF) für HKL und Tailgate
    def get_block_manu_stat(self, choice, function):
        if choice == "hkl":
            if function == "manuell":
                status = self.manu_HKL.Value
            if function == "block":
                status = self.block_HKL.Value
        else:
            if function == "manuell":
                status = self.manu_Tailgate.Value
            if function == "block":
                status = self.block_Tailgate.Value
        return status

    #BLOCK oder MANUELL auf ON für HKL und Tailgate
    def block_manu_ON(self, choice, function):
        if choice == "hkl":
            if function == "manuell":
                self.manu_HKL.ValueAdjustment.Add(1)
                Value = self.manu_HKL.Value
            else:
                self.block_HKL.ValueAdjustment.Add(1)
                Value = self.block_HKL.Value
        else: #choice == "tg"
            if function == "manuell":
                self.manu_Tailgate.ValueAdjustment.Add(1)
                Value = self.manu_Tailgate.Value
            else:
                self.block_Tailgate.ValueAdjustment.Add(1)
                Value = self.block_Tailgate.Value
        time.sleep(0.1)
        return Value

    #BLOCK oder MANUELL auf OFF für HKL und Tailgate
    def block_manu_OFF(self, choice, function):
        if choice == "hkl":
            if function == "manuell":
                self.manu_HKL.ValueAdjustment.Add(-1)
                Value = self.manu_HKL.Value
            else:
                self.block_HKL.ValueAdjustment.Add(-1)
                Value = self.block_HKL.Value
        else: #choice == "tg"
            if function == "manuell":
                self.manu_Tailgate.ValueAdjustment.Add(-1)
                Value = self.manu_Tailgate.Value
            else:
                self.block_Tailgate.ValueAdjustment.Add(-1)
                Value = self.manu_Tailgate.Value
        time.sleep(0.1)
        return Value
    
    #Abfrage der Position des HKL in Hallcounts
    def hkl_get_hall(self):
        self.get_derivat()
        hkl_pos = 0
        try:
            hkl_pos = (100 / self.hkl_hallCounts_max)*self.hkl_hallCounts_ist.Value
        except Exception as e:
            print(f"Fehler: {e}")
        return hkl_pos
    
    #Abfrage der Position des Tailgate in Hallcounts
    def tg_get_hall(self):
        self.get_derivat()
        tg_pos = 0
        try:
            tg_pos = (100 / self.tg_hallCounts_max)*self.tg_hallCounts_ist.Value
        except Exception as e:
            print(f"Fehler: {e}")
        return tg_pos

    #Setzen der Hallcounts für HKL für BLOCK oder MANUELL
    def hkl_set_hallcount(self, hc, function):
        self.get_derivat()
        if function == "manuell":
            val = self.hkl_set_manu.Value
            try:
                pos = self.hkl_hallCounts_max*(int(hc)/100)-val
                self.hkl_set_manu.ValueAdjustment.Add(pos)
            except Exception as e:
                print(f"Fehler: {e}")
        else:
            val = self.hkl_set_block.Value
            try:
                pos = self.hkl_hallCounts_max*(int(hc)/100)-val
                self.hkl_set_block.ValueAdjustment.Add(pos)
            except Exception as e:
                print(f"Fehler: {e}")

    #Setzen der Hallcounts für Tailgate für BLOCK oder MANUELL
    def tg_set_hallcount(self, hc, function):
        self.get_derivat()
        if function == "manuell":
            val = self.tg_set_manu.Value
            try:
                pos = self.tg_hallCounts_max*(int(hc)/100)-val
                self.tg_set_manu.ValueAdjustment.Add(pos)
            except Exception as e:
                print(f"Fehler: {e}")
        else:
            val = self.tg_set_block.Value
            try:
                pos = self.tg_hallCounts_max*(int(hc)/100)-val
                self.tg_set_block.ValueAdjustment.Add(pos)
            except Exception as e:
                print(f"Fehler: {e}")


test = controldesk()


