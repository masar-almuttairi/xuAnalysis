import os,sys
basepath = os.path.abspath(__file__).rsplit('/xuAnalysis/',1)[0]+'/xuAnalysis/'
sys.path.append(basepath)

from framework.analysis import analysis
from framework.fileReader import GetHistoFromSetOfFiles
from framework.functions import *
from ROOT.TMath import Sqrt as sqrt
from ROOT import *

### Channel to ints
class ch():
  ElMu = 0
  MuMu = 1
  ElEl = 2
  Muon = 3
  Elec = 4
chan = {ch.ElMu:'ElMu', ch.MuMu:'MuMu', ch.ElEl:'ElEl'}

### Levels to ints
class lev():
  dilepton = 0
  ZVeto    = 1
  MET      = 2
  jets2    = 3
  btag1    = 4
level = {lev.dilepton:'dilepton', lev.ZVeto:'ZVeto', lev.MET:'MET', lev.jets2:'2jets', lev.btag1:'1btag'}

### Systematic uncertainties
class systematic():
  nom       = -1 # Nominal
  MuonEffUp = 0
  MuonEffDo = 1
  ElecEffUp = 2
  ElecEffDo = 3
  JESUp = 4
  JESDo = 5
  JERUp = 6
  JERDo = 7
  PUUp = 8
  PUDo = 9
systlabel = {systematic.nom:'', systematic.MuonEffUp:'MuonEffUp', systematic.MuonEffDo:'MuonEffDown', systematic.ElecEffUp:'ElecEffUp', systematic.ElecEffDo:'ElecEffDown', systematic.JESUp:'JESUp', systematic.JESDo:'JESDown', systematic.PUUp:'PUUp', systematic.PUDo:'PUDown'}

### Datasets to ints
class datasets():
  SingleMuon = 0
  SingleElec = 1
  DoubleMuon = 2
  DoubleElec = 3
  MuonEG     = 4
dataset = {datasets.SingleElec:'HighEGJet', datasets.SingleMuon:'SingleMuon', datasets.DoubleMuon:'DoubleMuon'}

################ Analysis
class ttanalysis(analysis):
  def init(self):
    # Load SF files
    if not self.isData:
      self.LoadHisto('MuonIsoSF', basepath+'./inputs/MuonISO.root', 'NUM_TightRelIso_DEN_TightIDandIPCut_pt_abseta') # pt, abseta
      self.LoadHisto('MuonIdSF',  basepath+'./inputs/MuonID.root',  'NUM_TightID_DEN_genTracks_pt_abseta') # pt, abseta
      self.LoadHisto('ElecSF',    basepath+'./inputs/ElecTightCBid94X.root',  'EGamma_SF2D') # eta, pt

    # Uncertainties
    self.doSyst = False if ('noSyst' in self.options or self.isData) else True

    # Objects for the analysis
    self.selLeptons = []
    self.selJets = []
    self.pmet = TLorentzVector()

    if not self.isData and self.doSyst:
      self.selJetsJESUp = []
      self.selJetsJESDo = []
      self.selJetsJERUp = []
      self.selJetsJERDo = []
      self.pmetJESUp = TLorentzVector()
      self.pmetJESDo = TLorentzVector()
      self.pmetJERUp = TLorentzVector()
      self.pmetJERDo = TLorentzVector()

    # Sample name
    name = self.sampleName
    self.isTT = True if name[0:2] == 'TT' else False
    self.isTTnom = True if self.sampleName == 'TT' else False
    self.doTTbarSemilep = False
    if self.isTT and ('semi' in self.options or 'Semi' in self.options): # ttbar semilep
      self.doTTbarSemilep = True
      self.SetOutName("TTsemilep")
      print 'Setting out name to TTsemilep...'
    self.isDY = True if 'DY' in self.sampleName else False

    # PDF and scale histos for TT sample
    if self.isTTnom and self.index <= 0:
      hSumPDF   = GetHistoFromSetOfFiles(self.GetFiles(), 'SumOfPDFweights')
      hSumScale = GetHistoFromSetOfFiles(self.GetFiles(), 'SumOfScaleWeights')
      self.AddToOutputs('SumOfPDFweights', hSumPDF)
      self.AddToOutputs('SumOfScaleWeights', hSumScale)
    
    # It it's data, store dataset index
    self.sampleDataset = -1
    for i, dataName in dataset.items(): 
      if dataName == name: self.sampleDataset = i

    # Jet and lep pT
    self.JetPtCut  = 20
    self.LepPtCut  = 12
    self.Lep0PtCut = 20

  def resetObjects(self):
    self.selLeptons = []
    self.selJets = []
    self.pmet = TLorentzVector()
    if not self.isData and self.doSyst:
      self.selJetsJESUp = []
      self.selJetsJESDo = []
      self.selJetsJERUp = []
      self.selJetsJERDo = []
      self.pmetJESUp = TLorentzVector()
      self.pmetJESDo = TLorentzVector()
      self.pmetJERUp = TLorentzVector()
      self.pmetJERDo = TLorentzVector()

  def GetName(self, var, ichan, ilevel = '', isyst = ''):
    ''' Crafts the name for a histo '''
    if isinstance(ichan,  int): ichan  = chan[ichan]
    if isinstance(ilevel, int): ilevel = level[ilevel]
    if isinstance(isyst,  int): isyst  = systlabel[isyst]
    name = var + ('_' + ichan if ichan != '' else '') + ('_' + ilevel if ilevel != '' else '') + ('_'+isyst if isyst != '' else '')
    return name

  def NewHisto(self, var, chan, level, syst, nbins, bin0, binN):
    ''' Used to create the histos following a structure '''
    self.CreateTH1F(self.GetName(var, chan, level, syst), "", nbins, bin0, binN)

  def GetHisto(self, var, chan, level = '', syst = ''):
    ''' Get a given histo using the tthisto structure '''
    return self.obj[self.GetName(var, chan, level, syst)]

  def createHistos(self):
    ''' Create all the histos for the analysis '''
    self.isTTnom = True if self.sampleName      == 'TT' else False
    self.isTT    = True if self.sampleName[0:2] == 'TT' else False
    self.isDY    = True if 'DY' in self.sampleName      else False

    ### Yields histos
    if self.isTT: self.NewHisto('FiduEvents', '', '', '', 5,0,5)
    for key_chan in chan:
      ichan = chan[key_chan]
      for key_syst in systlabel.keys():
        if not self.doSyst and key_syst != systematic.nom: continue
        isyst = systlabel[key_syst]
        self.NewHisto('Yields',   ichan, '', isyst, 5, 0, 5)
        self.NewHisto('YieldsSS', ichan, '', isyst, 5, 0, 5)

    ### Histos for DY
    if self.isData or self.isDY:
      for key_chan in chan:
        ichan = chan[key_chan]
        for key_level in level:
          ilevel = level[key_level]
          if key_level != lev.ZVeto:
            self.NewHisto('DYHisto', ichan, ilevel, '', 60, 0, 300)
            if key_level != lev.MET: 
              self.NewHisto('DYHistoElMu', ichan, ilevel, '', 60, 0, 300)
        self.NewHisto('DYHisto',     ichan, 'eq1jet', '', 60, 0, 300)
        self.NewHisto('DYHistoElMu', ichan, 'eq1jet', '', 60, 0, 300)
        self.NewHisto('DYHisto',     ichan, 'eq2jet', '', 60, 0, 300)
        self.NewHisto('DYHistoElMu', ichan, 'eq2jet', '', 60, 0, 300)
        self.NewHisto('DYHisto',     ichan, 'geq3jet', '', 60, 0, 300)
        self.NewHisto('DYHistoElMu', ichan, 'geq3jet', '', 60, 0, 300)
        self.NewHisto('DYHisto',     ichan, '2btag', '', 60, 0, 300)
        self.NewHisto('DYHistoElMu', ichan, '2btag', '', 60, 0, 300)

    ### Analysis histos
    for key_chan in chan:
      ichan = chan[key_chan]
      for key_level in level:
        ilevel = level[key_level]
        if ichan == 'ElMu' and (ilevel == 'ZVeto' or ilevel == 'MET'): continue
        # Create histos for PDF and scale systematics
        if self.isTTnom:
          self.NewHisto('PDFweights',ichan,ilevel,'',33,0.5,33.5)
          self.NewHisto('ScaleWeights',ichan,ilevel,'',9,0.5,9.5)
        for key_syst in systlabel.keys():
          if key_syst != systematic.nom and self.isData: continue
          if not self.doSyst and key_syst != systematic.nom: continue
            
          isyst = systlabel[key_syst]
          # Event
          self.NewHisto('HT',   ichan,ilevel,isyst, 80, 0, 400)
          self.NewHisto('MET',  ichan,ilevel,isyst, 30, 0, 150)
          self.NewHisto('NJets',ichan,ilevel,isyst, 8 ,-0.5, 7.5)
          self.NewHisto('Btags',ichan,ilevel,isyst, 4 ,-0.5, 3.5)
          self.NewHisto('Vtx',  ichan,ilevel,isyst, 10, -0.5, 9.5)
          self.NewHisto('NBtagNJets', ichan,ilevel,isyst, 7, -0.5, 6.5)

          # Leptons
          self.NewHisto('Lep0Pt', ichan,ilevel,isyst, 24, 0, 120)
          self.NewHisto('Lep1Pt', ichan,ilevel,isyst, 24, 0, 120)
          self.NewHisto('Lep0Eta', ichan,ilevel,isyst, 50, -2.5, 2.5)
          self.NewHisto('Lep1Eta', ichan,ilevel,isyst, 50, -2.5, 2.5)
          self.NewHisto('Lep0Phi', ichan,ilevel,isyst, 20, -1, 1)
          self.NewHisto('Lep1Phi', ichan,ilevel,isyst, 20, -1, 1)
          self.NewHisto('DilepPt', ichan,ilevel,isyst, 40, 0, 200)
          self.NewHisto('InvMass', ichan,ilevel,isyst, 60, 0, 300)
          self.NewHisto('DYMass',  ichan,ilevel,isyst, 200, 70, 110)
          self.NewHisto('DYMassBB',  ichan,ilevel,isyst, 200, 70, 110)
          self.NewHisto('DYMassBE',  ichan,ilevel,isyst, 200, 70, 110)
          self.NewHisto('DYMassEB',  ichan,ilevel,isyst, 200, 70, 110)
          self.NewHisto('DYMassEE',  ichan,ilevel,isyst, 200, 70, 110)
          self.NewHisto('DeltaPhi',  ichan,ilevel,isyst, 20, 0, 1)
          if ichan == chan[ch.ElMu]:
            self.NewHisto('ElecEta', 'ElMu',ilevel,isyst, 50, -2.5, 2.5)
            self.NewHisto('MuonEta', 'ElMu',ilevel,isyst, 50, -2.5, 2.5)
            self.NewHisto('ElecPt', 'ElMu',ilevel,isyst, 24, 0, 120)
            self.NewHisto('MuonPt', 'ElMu',ilevel,isyst, 24, 0, 120)
            self.NewHisto('ElecPhi', 'ElMu',ilevel,isyst, 20, -1, 1)
            self.NewHisto('MuonPhi', 'ElMu',ilevel,isyst, 20, -1, 1)

          # Jets
          self.NewHisto('Jet0Pt',   ichan,ilevel,isyst, 60, 0, 300)
          self.NewHisto('Jet1Pt',   ichan,ilevel,isyst, 50, 0, 250)
          self.NewHisto('JetAllPt', ichan,ilevel,isyst, 60, 0, 300)
          self.NewHisto('Jet0Eta',   ichan,ilevel,isyst, 50, -2.5, 2.5)
          self.NewHisto('Jet1Eta',   ichan,ilevel,isyst, 50, -2.5, 2.5)
          self.NewHisto('JetAllEta', ichan,ilevel,isyst, 50, -2.5, 2.5)
          self.NewHisto('Jet0Csv',   ichan,ilevel,isyst, 40, 0, 1)
          self.NewHisto('Jet1Csv',   ichan,ilevel,isyst, 40, 0, 1)
          self.NewHisto('JetAllCsv', ichan,ilevel,isyst, 40, 0, 1)
          self.NewHisto('Jet0DCsv',   ichan,ilevel,isyst, 40, 0, 1)
          self.NewHisto('Jet1DCsv',   ichan,ilevel,isyst, 40, 0, 1)
          self.NewHisto('JetAllDCsv', ichan,ilevel,isyst, 40, 0, 1)

  def FillHistograms(self, leptons, jets, pmet, ich, ilev, isys):
    ''' Fill all the histograms. Take the inputs from lepton list, jet list, pmet '''
    if self.SS: return               # Do not fill histograms for same-sign events
    if not len(leptons) >= 2: return # Just in case
    self.SetWeight(isys)

    # Re-calculate the observables
    lep0  = leptons[0]; lep1 = leptons[1]
    l0pt  = lep0.Pt();  l1pt  = lep1.Pt()
    l0eta = lep0.Eta(); l1eta = lep1.Eta()
    l0phi = lep0.Phi(); l1phi = lep1.Phi()
    dphi  = DeltaPhi(lep0, lep1)
    mll   = InvMass(lep0, lep1)
    dipt  = DiPt(lep0, lep1)
    mupt  = 0; elpt  = 0
    mueta = 0; eleta = 0
    muphi = 0; elphi = 0
    if ich == ch.ElMu:
      if lep0.IsMuon():
         mu = lep0
         el = lep1
      else:
        mu = lep1
        el = lep0
      elpt  = el.Pt();  mupt  = mu.Pt()
      eleta = el.Eta(); mueta = mu.Eta()
      elphi = el.Phi(); muphi = mu.Phi()
                     
    met = pmet.Pt()
    ht = 0; 
    for j in jets: ht += j.Pt()
    njet = len(jets)
    nbtag = GetNBtags(jets)
    
    if njet > 0:
      jet0 = jets[0]
      j0pt = jet0.Pt(); j0eta = jet0.Eta(); j0phi = jet0.Phi()
      j0csv = jet0.GetCSVv2(); j0deepcsv = jet0.GetDeepCSV()
    if njet > 1:
      jet1 = jets[1]
      j1pt = jet1.Pt(); j1eta = jet1.Eta(); j1phi = jet1.Phi()
      j1csv = jet1.GetCSVv2(); j1deepcsv = jet1.GetDeepCSV()
    else:
      j0pt = -1; j0eta = -999; j0phi = -999;
      j0csv = -1; j0deepcsv = -1;
    
    ### Fill the histograms
    #if ich == ch.ElMu and ilev == lev.dilepton: print 'Syst = ', isys, ', weight = ', self.weight
    self.GetHisto('HT',   ich,ilev,isys).Fill(ht, self.weight)
    self.GetHisto('MET',  ich,ilev,isys).Fill(met, self.weight)
    self.GetHisto('NJets',ich,ilev,isys).Fill(njet, self.weight)
    self.GetHisto('Btags',ich,ilev,isys).Fill(nbtag, self.weight)
    self.GetHisto('Vtx',  ich,ilev,isys).Fill(self.nvtx, self.weight)
    self.GetHisto("InvMass", ich, ilev, isys).Fill(mll, self.weight)

    if   njet == 0: nbtagnjetsnum = nbtag
    elif njet == 1: nbtagnjetsnum = nbtag + 1
    elif njet == 2: nbtagnjetsnum = nbtag + 3
    else          : nbtagnjetsnum = 6
    self.GetHisto('NBtagNJets', ich, ilev,isys).Fill(nbtagnjetsnum, self.weight)

    # Leptons
    self.GetHisto('Lep0Pt', ich,ilev,isys).Fill(l0pt, self.weight)
    self.GetHisto('Lep1Pt', ich,ilev,isys).Fill(l1pt, self.weight)
    self.GetHisto('Lep0Eta', ich,ilev,isys).Fill(l0eta, self.weight)
    self.GetHisto('Lep1Eta', ich,ilev,isys).Fill(l1eta, self.weight)
    self.GetHisto('Lep0Phi', ich,ilev,isys).Fill(l0phi/3.141592, self.weight)
    self.GetHisto('Lep1Phi', ich,ilev,isys).Fill(l1phi/3.141592, self.weight)
    self.GetHisto('DilepPt', ich,ilev,isys).Fill(dipt, self.weight)
    self.GetHisto('DeltaPhi',  ich,ilev,isys).Fill(dphi/3.141592, self.weight)
    self.GetHisto('InvMass', ich,ilev,isys).Fill(mll, self.weight)
    if mll > 70 and mll < 110: 
      self.GetHisto('DYMass',  ich,ilev,isys).Fill(mll, self.weight)
      l0eta = abs(l0eta); l1eta = abs(l1eta)
      if ich == ch.ElEl:
        if   l0eta <= 1.479 and l1eta <= 1.479: self.GetHisto('DYMassBB',  ich,ilev,isys).Fill(mll, self.weight)
        elif l0eta <= 1.479 and l1eta  > 1.479: self.GetHisto('DYMassBE',  ich,ilev,isys).Fill(mll, self.weight)
        elif l0eta  > 1.479 and l1eta <= 1.479: self.GetHisto('DYMassEB',  ich,ilev,isys).Fill(mll, self.weight)
        elif l0eta  > 1.479 and l1eta  > 1.479: self.GetHisto('DYMassEE',  ich,ilev,isys).Fill(mll, self.weight)
    if ich == ch.ElMu:
      self.GetHisto('ElecEta', ich,ilev,isys).Fill(eleta, self.weight)
      self.GetHisto('ElecPt',  ich,ilev,isys).Fill(elpt, self.weight)
      self.GetHisto('ElecPhi', ich,ilev,isys).Fill(elphi, self.weight)
      self.GetHisto('MuonEta', ich,ilev,isys).Fill(mueta, self.weight)
      self.GetHisto('MuonPt',  ich,ilev,isys).Fill(mupt, self.weight)
      self.GetHisto('MuonPhi', ich,ilev,isys).Fill(muphi, self.weight)

    # Jets
    if njet >= 1:
      self.GetHisto('Jet0Pt',   ich,ilev,isys).Fill(j0pt, self.weight)
      self.GetHisto('Jet0Eta',   ich,ilev,isys).Fill(j0eta, self.weight)
      self.GetHisto('Jet0Csv',   ich,ilev,isys).Fill(j0csv, self.weight)
      self.GetHisto('Jet0DCsv',   ich,ilev,isys).Fill(j0deepcsv, self.weight)

    if njet >= 2:
      self.GetHisto('Jet1Pt',   ich,ilev,isys).Fill(j1pt, self.weight)
      self.GetHisto('Jet1Eta',   ich,ilev,isys).Fill(j1eta, self.weight)
      self.GetHisto('Jet1Csv',   ich,ilev,isys).Fill(j1csv, self.weight)
      self.GetHisto('Jet1DCsv',   ich,ilev,isys).Fill(j1deepcsv, self.weight)

    for ijet in jets:
      self.GetHisto('JetAllPt', ich,ilev,isys).Fill(ijet.Pt(), self.weight)
      self.GetHisto('JetAllEta', ich,ilev,isys).Fill(ijet.Eta(), self.weight)
      self.GetHisto('JetAllCsv', ich,ilev,isys).Fill(ijet.GetCSVv2(), self.weight)
      self.GetHisto('JetAllDCsv', ich,ilev,isys).Fill(ijet.GetDeepCSV(), self.weight)

  def FillYieldsHistos(self, ich, ilev, isyst):
    ''' Fill histograms for yields. Also for SS events for the nonprompt estimate '''
    self.SetWeight(isyst)
    if not self.SS: self.GetHisto('Yields',   ich, '', isyst).Fill(ilev, self.weight)
    else          : self.GetHisto('YieldsSS', ich, '', isyst).Fill(ilev, self.weight)

  def FillDYHistos(self, leptons, ich, ilev):
    ''' Fill DY histos used for the R_out/in method for DY estimate '''
    if self.SS: return # Do not fill the histograms with same-sign events
    if ilev == lev.ZVeto: return
    mll   = InvMass(leptons[0], leptons[1])
    self.GetHisto('DYHisto', ich, ilev).Fill(mll, self.weight)

  def FillDYHistosElMu(self, leptons, ich, ilev):
    ''' Fill DY histos used for the R_out/in method for the emu channel '''
    if self.SS: return # Do not fill the histograms with same-sign events
    if ilev == lev.ZVeto or ilev == lev.MET: return
    mll = InvMass(leptons[0], leptons[1])
    self.GetHisto('DYHistoElMu', ich, ilev).Fill(mll, self.weight)

  def FillAll(self, ich, ilev, isyst, leps, jets, pmet):
    ''' Fill histograms for a given variation, channel and level '''
    self.FillYieldsHistos(ich, ilev, isyst)
    self.FillHistograms(leps, jets, pmet, ich, ilev, isyst)

  def FillLHEweights(self, t, ich, ilev):
    weight = self.weight
    for i in range(t.nLHEPdfWeight):   self.GetHisto("PDFweights",   ich, ilev, -1).Fill(i+1, t.LHEPdfWeight[i]*weight)
    for i in range(t.nLHEScaleWeight): self.GetHisto("ScaleWeights", ich, ilev, -1).Fill(i+1, t.LHEScaleWeight[i]*weight)

  def SetWeight(self, syst):
    ''' Sets the event weight according to the systematic variation '''
    # elec, muon, pu, trigger...
    if not isinstance(syst, int): print '[WARNING] Label ', syst, ' is not an integer...'
    self.weight = self.EventWeight
    if   syst == systematic.nom:       self.weight *= self.SFmuon * self.SFelec * self.PUSF
    elif syst == systematic.ElecEffUp: self.weight *= self.SFmuon * (self.SFelec + self.SFelecErr) * self.PUSF
    elif syst == systematic.ElecEffDo: self.weight *= self.SFmuon * (self.SFelec - self.SFelecErr) * self.PUSF
    elif syst == systematic.MuonEffUp: self.weight *= (self.SFmuon + self.SFmuonErr) * self.SFelec * self.PUSF
    elif syst == systematic.MuonEffDo: self.weight *= (self.SFmuon - self.SFmuonErr) * self.SFelec * self.PUSF
    elif syst == systematic.PUUp:      self.weight *= self.SFmuon * self.SFelec * self.PUUpSF
    elif syst == systematic.PUDo:      self.weight *= self.SFmuon * self.SFelec * self.PUDoSF

  def SetVariables(self, isyst):
    leps = self.selLeptons
    jets = self.selJets
    pmet = self.pmet
    if   isyst == systematic.nom: return leps, jets, pmet
    elif isyst == systematic.JESUp:
      jets = self.selJetsJESUp
      pmet = self.pmetJESUp
    elif isyst == systematic.JESDo:
      jets = self.selJetsJESDo
      pmet = self.pmetJESDo
    elif isyst == systematic.JERUp:
      jets = self.selJetsJERUp
      pmet = self.pmetJERUp
    elif isyst == systematic.JERDo:
      jets = self.selJetsJERDo
      pmet = self.pmetJERDo
    return leps, jets, pmet

  def insideLoop(self, t):
    self.resetObjects()

    ### Lepton selection
    ###########################################
    if not self.isData: nGenLep = t.nGenDressedLepton 
    if self.isTT and not self.doTTbarSemilep and  nGenLep < 2: return
    if self.doTTbarSemilep and  nGenLep >= 2: return
    if self.isTT:
      genLep = []
      for i in range(nGenLep):
        p = TLorentzVector()
        p.SetPtEtaPhiM(t.GenDressedLepton_pt[i], t.GenDressedLepton_eta[i], t.GenDressedLepton_phi[i], t.GenDressedLepton_mass[i])
        pdgid = abs(t.GenDressedLepton_pdgId[i])
        if p.Pt() < 12 or abs(p.Eta()) > 2.4: continue
        genLep.append(lepton(p, 0, pdgid))
      pts    = [lep.Pt() for lep in genLep]
      genLep = [lep for _,lep in sorted(zip(pts,genLep))]

      if len(genLep) >= 2:
        genChan = 0
        l0 = genLep[0]; l1 = genLep[1]
        totId = l0.GetPDGid() + l1.GetPDGid()
        if   totId == 24: genChan = ch.ElMu
        elif totId == 22: genChan = ch.ElEl
        elif totId == 26: genChan = ch.MuMu
        genMll = InvMass(l0, l1)
   
        genMET = t.GenMET_pt
        genJets = []
        ngenJet = 0; ngenBJet = 0
        for i in range(t.nGenJet):
          p = TLorentzVector()
          p.SetPtEtaPhiM(t.GenJet_pt[i], t.GenJet_eta[i], t.GenJet_phi[i], t.GenJet_mass[i])
          if p.Pt() < 25 or abs(p.Eta()) > 2.4: continue
          pdgid = abs(t.GenJet_partonFlavour[i])
          j = jet(p)
          #if not j.IsClean(genLep, 0.4): continue
          genJets.append(j)
          ngenJet += 1
          if pdgid == 5: ngenBJet+=1
    
        # Fill fidu yields histo 
        if genMll >= 20 and genLep[0].Pt() >= 20:
          self.obj['FiduEvents'].Fill(lev.dilepton)
          if genChan == ch.ElEl or genChan == ch.MuMu:
            if abs(genMll - 90) > 15:
              self.obj['FiduEvents'].Fill(lev.ZVeto)
              if genMET > 35:
                self.obj['FiduEvents'].Fill(lev.MET)
                if ngenJet >= 2:
                  self.obj['FiduEvents'].Fill(lev.jets2)
                  if ngenBJet >= 1: self.obj['FiduEvents'].Fill(lev.btag1)
          else:
            self.obj['FiduEvents'].Fill(lev.ZVeto)
            self.obj['FiduEvents'].Fill(lev.MET)
            if ngenJet >= 2:
              self.obj['FiduEvents'].Fill(lev.jets2)
              if ngenBJet >= 1: self.obj['FiduEvents'].Fill(lev.btag1)
    
    ##### Muons
    for i in range(t.nMuon):
      p = TLorentzVector()
      p.SetPtEtaPhiM(t.Muon_pt[i], t.Muon_eta[i], t.Muon_phi[i], t.Muon_mass[i])
      charge = t.Muon_charge[i]
      # Tight ID
      if not t.Muon_tightId[i]: continue
      # Tight ISO, RelIso04 < 0.15
      if not t.Muon_pfRelIso04_all[i] < 0.15: continue
      # Tight IP
      dxy = abs(t.Muon_dxy[i])
      dz  = abs(t.Muon_dz[i] )
      if dxy > 0.05 or dz > 0.1: continue
      # pT < 12 GeV, |eta| < 2.4
      if p.Pt() < 12 or abs(p.Eta()) > 2.4: continue
      self.selLeptons.append(lepton(p, charge, 13))
       
    ##### Electrons
    for i in range(t.nElectron):
      p = TLorentzVector()
      p.SetPtEtaPhiM(t.Electron_pt[i], t.Electron_eta[i], t.Electron_phi[i], t.Electron_mass[i])
      charge = t.Electron_charge[i]
      etaSC    = abs(p.Eta());
      dEtaSC   = t.Electron_deltaEtaSC[i]
      convVeto = t.Electron_convVeto[i]
      R9       = t.Electron_r9[i]
      # Tight cut-based Id
      if not t.Electron_cutBased[i] >= 4: continue # Tightcut-based Id
      if not convVeto: continue
      # Isolation (RelIso03) tight
      relIso03 = t.Electron_pfRelIso03_all[i]
      if   etaSC <= 1.479 and relIso03 > 0.0361: continue
      elif etaSC >  1.479 and relIso03 > 0.094:  continue
      # Tight IP
      dxy = abs(t.Electron_dxy[i])
      dz  = abs(t.Electron_dz[i] )
      if dxy > 0.05 or dz > 0.1: continue
      # pT > 12 GeV, |eta| < 2.4
      if p.Pt() < 12 or abs(p.Eta()) > 2.4: continue
      self.selLeptons.append(lepton(p, charge, 11))
    leps = self.selLeptons
    pts  = [lep.Pt() for lep in leps]
    self.selLeptons = [lep for _,lep in sorted(zip(pts,leps))]

    # Lepton SF
    self.SFelec = 1; self.SFmuon = 1; self.SFelecErr = 0; self. SFmuonErr = 0
    if not self.isData:
      for lep in self.selLeptons:
        if lep.IsMuon():
          sf, err = self.GetSFandErr('MuonIsoSF, MuonIdSF', lep.Pt(), TMath.Abs(lep.Eta()))
          self.SFmuon*=sf
          self.SFmuonErr+=err*err
        else:
          sf, err = self.GetSFandErr('ElecSF', lep.Eta(), lep.Pt())
          self.SFelec*=sf
          self.SFelecErr+=err*err
      self.SFelecErr = sqrt(self.SFelecErr)
      self.SFmuonErr = sqrt(self.SFmuonErr)

    ### Jet selection
    ###########################################

    for i in range(t.nJet):
      p = TLorentzVector()
      p.SetPtEtaPhiM(t.Jet_pt[i], t.Jet_eta[i], t.Jet_phi[i], t.Jet_mass[i])
      csv = t.Jet_btagCSVV2[i]; deepcsv = t.Jet_btagDeepB[i]; 
      jid = t.Jet_jetId[i]
      flav = t.Jet_hadronFlavour[i] if not self.isData else -99;
      # Jet ID > 1, tight Id
      if not jid > 1: continue
      # |eta| < 2.4 
      if abs(p.Eta()) > 2.4: continue
      j      = jet(p,      csv, flav, jid, deepcsv)
      if csv >= 0.8484 : j.SetBtag() ### Misssing CSVv2 SFs !!!! 
      if not j.IsClean(self.selLeptons, 0.4): continue
      if p.Pt()      >= self.JetPtCut: self.selJets.append(j)
      if not self.isData and self.doSyst:
        pJESUp = TLorentzVector(); pJERUp = TLorentzVector()
        pJESDo = TLorentzVector(); pJERDo = TLorentzVector()
        pJESUp.SetPtEtaPhiM(t.Jet_pt_jesTotalUp[i],   t.Jet_eta[i], t.Jet_phi[i], t.Jet_mass_jesTotalUp[i])
        pJESDo.SetPtEtaPhiM(t.Jet_pt_jesTotalDown[i], t.Jet_eta[i], t.Jet_phi[i], t.Jet_mass_jesTotalDown[i])
        pJERUp.SetPtEtaPhiM(t.Jet_pt_jerUp[i],        t.Jet_eta[i], t.Jet_phi[i], t.Jet_mass_jerUp[i])
        pJERDo.SetPtEtaPhiM(t.Jet_pt_jerDown[i],      t.Jet_eta[i], t.Jet_phi[i], t.Jet_mass_jerDown[i])
        jJESUp = jet(pJESUp, csv, flav, jid, deepcsv)
        jJESDo = jet(pJESDo, csv, flav, jid, deepcsv)
        jJERUp = jet(pJERUp, csv, flav, jid, deepcsv)
        jJERDo = jet(pJERDo, csv, flav, jid, deepcsv)
        if csv >= 0.8484:
          jJESUp.SetBtag()
          jJESDo.SetBtag()
          jJERUp.SetBtag()
          jJERDo.SetBtag()
        if pJESUp.Pt() >= self.JetPtCut: self.selJetsJESUp.append(jJESUp)
        if pJESDo.Pt() >= self.JetPtCut: self.selJetsJESDo.append(jJESDo)
        if pJERUp.Pt() >= self.JetPtCut: self.selJetsJERUp.append(jJERUp)
        if pJERDo.Pt() >= self.JetPtCut: self.selJetsJERDo.append(jJERDo)
    self.selJets = SortByPt(self.selJets)
    if not self.isData and self.doSyst:
      self.selJetsJESUp = SortByPt(self.selJetsJESUp)
      self.selJetsJESDo = SortByPt(self.selJetsJESDo)
      self.selJetsJERUp = SortByPt(self.selJetsJERUp)
      self.selJetsJERDo = SortByPt(self.selJetsJERDo)

    ##### MET
    self.pmet.SetPtEtaPhiE(t.MET_pt, 0, t.MET_phi, 0)
    if not self.isData and self.doSyst:
      self.pmetJESUp.SetPtEtaPhiM(t.MET_pt_jesTotalUp,   0, t.MET_phi_jesTotalUp,   0) 
      self.pmetJESDo.SetPtEtaPhiM(t.MET_pt_jesTotalDown, 0, t.MET_phi_jesTotalDown, 0) 
      self.pmetJERUp.SetPtEtaPhiM(t.MET_pt_jerUp,        0, t.MET_phi_jerUp,        0) 
      self.pmetJERDo.SetPtEtaPhiM(t.MET_pt_jerDown,      0, t.MET_phi_jerDown,      0) 

    nJets = len(self.selJets)
    nBtag = GetNBtags(self.selJets)

    ### Set dilepton channel
    nLep = len(self.selLeptons)
    if nLep < 2: return
    l0 = self.selLeptons[0]
    l1 = self.selLeptons[1]
    totId = l0.GetPDGid() + l1.GetPDGid()
    ich = -1
    if   totId == 24: ich = ch.ElMu
    elif totId == 22: ich = ch.ElEl
    elif totId == 26: ich = ch.MuMu
    
    ### Trigger
    ###########################################
    trigger = {
     ch.Elec:t.HLT_HIEle20_WPLoose_Gsf,
     ch.Muon:t.HLT_HIL3Mu20,
     ch.ElMu:t.HLT_HIL3Mu20 or t.HLT_HIEle20_WPLoose_Gsf,
     ch.ElEl:t.HLT_HIEle20_WPLoose_Gsf,
     ch.MuMu:t.HLT_HIL3DoubleMu0
    }
    passTrig = trigger[ich]

    ### Remove overlap events in datasets
    # In tt @ 5.02 TeV, 
    if self.isData:
      if   self.sampleDataset == datasets.SingleElec:
        if   ich == ch.ElEl: passTrig = trigger[ich]
        elif ich == ch.ElMu: passTrig = trigger[ch.Elec] and not trigger[ch.Muon]
        else:                passTrig = False
      elif self.sampleDataset == datasets.SingleMuon:
        if   ich == ch.ElMu: passTrig = trigger[ch.Muon]
        else:                passTrig = False
      elif self.sampleDataset == datasets.DoubleMuon:
        if   ich == ch.MuMu: passTrig = trigger[ich]
        else:                passTrig = False

    ### Event weight and othe global variables
    ###########################################
    self.nvtx   = t.PV_npvs
    #'''
    if not self.isData:
      self.PUSF   = t.puWeight
      self.PUUpSF = t.puWeightUp
      self.PUDoSF = t.puWeightDown
    else:
      self.PUSF   = 1; self.PUUpSF = 1; self.PUDoSF = 1
    #'''
    #self.PUSF   = 1; self.PUUpSF = 1; self.PUDoSF = 1
    ''' Check that the PU weights are in the trees!!! '''

 
    ### Event selection
    ###########################################
    self.SetWeight(systematic.nom)
    weight = self.weight
    
    if not passTrig: return
    self.SS = l0.charge*l1.charge > 0
    for isyst in systlabel.keys():
      if not self.doSyst and isyst != systematic.nom: continue
      if self.isData and isyst != systematic.nom: continue
      leps, jets, pmet = self.SetVariables(isyst)
      nJets = len(jets)
      nBtag = GetNBtags(jets)
      if not len(leps) >= 2: continue
      l0 = leps[0]; l1 = leps[1]

      ### Dilepton pair
      if l0.Pt() < 20: continue
      if InvMass(l0,l1) < 20: continue
      self.FillAll(ich, lev.dilepton, isyst, leps, jets, pmet)
      if self.isTTnom and isyst == systematic.nom: self.FillLHEweights(t, ich, lev.dilepton)

      # >> Fill the DY histograms
      if (self.isData or self.isDY) and isyst == systematic.nom:
        self.FillDYHistos(self.selLeptons, ich, lev.dilepton)
        if self.pmet.Pt() > 35:
          self.FillDYHistos(self.selLeptons, ich, lev.MET)
          if   nJets == 1: self.FillDYHistos(self.selLeptons, ich, 'eq1jet')
          elif nJets == 2: self.FillDYHistos(self.selLeptons, ich, 'eq2jet')
          elif nJets >= 3: self.FillDYHistos(self.selLeptons, ich, 'geq3jet')
          if nJets >= 2:
            self.FillDYHistos(self.selLeptons, ich, lev.jets2)
            if nBtag >= 1:
              self.FillDYHistos(self.selLeptons, ich, lev.btag1)
              if nBtag >= 2:
                self.FillDYHistos(self.selLeptons, ich, '2btag')
        if   nJets == 1: self.FillDYHistosElMu(self.selLeptons, ich, 'eq1jet')
        elif nJets == 2: self.FillDYHistosElMu(self.selLeptons, ich, 'eq2jet')
        elif nJets >= 3: self.FillDYHistosElMu(self.selLeptons, ich, 'geq3jet')
        if nJets >= 2:
          self.FillDYHistosElMu(self.selLeptons, ich, lev.jets2)
          if nBtag >= 1:
            self.FillDYHistosElMu(self.selLeptons, ich, lev.btag1)
            if nBtag >= 2:
              self.FillDYHistosElMu(self.selLeptons, ich, '2btag')
  
      ### Z Veto + MET cut
      if ich == ch.MuMu or ich == ch.ElEl:
        if abs(InvMass(l0,l1) - 91) < 15: continue
        self.FillAll(ich, lev.ZVeto, isyst, leps, jets, pmet)
        if self.isTTnom and isyst == systematic.nom: self.FillLHEweights(t, ich, lev.ZVeto)
        if pmet.Pt() < 35: continue
        self.FillAll(ich,lev.MET,isyst,leps,jets,pmet)
        if self.isTTnom and isyst == systematic.nom: self.FillLHEweights(t, ich, lev.MET)

      ### 2 jets
      if nJets < 2: continue
      self.FillAll(ich, lev.jets2, isyst, leps, jets, pmet)
      if self.isTTnom and isyst == systematic.nom: self.FillLHEweights(t, ich, lev.jets2)

      ### 1 b-tag, CSVv2 Medium
      if nBtag < 1: continue 
      self.FillAll(ich, lev.btag1, isyst, leps, jets, pmet)
      if self.isTTnom and isyst == systematic.nom: self.FillLHEweights(t, ich, lev.btag1)
